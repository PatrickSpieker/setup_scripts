#!/usr/bin/env python3
"""Local recording, edit timeline, and verified-upload lifecycle for product demos."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import queue
import re
import shutil
import signal
import subprocess
import sys
import threading
import time
from datetime import datetime
from zoneinfo import ZoneInfo

FOLDER_ID = '115PfFulm_kVSzZ3MZ00w42rQAR04sIBz'
FOLDER_NAME = 'Antaeus Health Demos'


def require(condition, message):
    if not condition:
        raise ValueError(message)


def binary(name):
    path = shutil.which(name)
    require(path, f'{name} is missing; install FFmpeg before recording')
    return path


def load(run):
    return json.loads((Path(run) / 'manifest.json').read_text())


def save(run, data):
    p = Path(run) / 'manifest.json'
    tmp = p.with_suffix('.tmp')
    tmp.write_text(json.dumps(data, indent=2) + '\n')
    tmp.replace(p)


def digest(path, algorithm='sha256'):
    h = hashlib.new(algorithm)
    with open(path, 'rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def basename(name, when=None):
    when = when or datetime.now(ZoneInfo('America/New_York'))
    require(when.tzinfo is not None, 'Timestamp must be timezone-aware')
    slug = re.sub(r'[^a-z0-9]+', '_', name.lower()).strip('_')[:80].rstrip('_')
    require(slug, 'Demo name must contain letters or numbers')
    return when.astimezone(ZoneInfo('America/New_York')).strftime('%Y-%m-%d_%H_%M_%S_') + slug


def new_run(root, name, target):
    root = Path(root).expanduser().resolve()
    root.mkdir(parents=True, exist_ok=True)
    base = basename(name)
    for n in range(1000):
        stem = base if n == 0 else f'{base}_{n + 1}'
        run = root / stem
        try:
            run.mkdir()
            break
        except FileExistsError:
            continue
    else:
        raise ValueError('Too many filename collisions')
    (run / 'work').mkdir()
    save(run, dict(version=1, name=name, target=target, final=f'{stem}.mp4',
                   status='prepared', actions=[], complete=False, owned=[],
                   created_at=datetime.now(ZoneInfo('America/New_York')).isoformat()))
    return run


def own(run, relative):
    p = Path(relative)
    require(p.parts and p.parts[0] == 'work' and '..' not in p.parts and not p.is_absolute(),
            'Temporary artifacts must be inside work/')
    full = Path(run) / p
    require(not any(parent.is_symlink() for parent in [full, *full.parents]),
            'Artifact path contains a symlink')
    data = load(run)
    if relative not in data['owned']:
        data['owned'].append(relative)
        save(run, data)
    return full


def probe(path):
    result = subprocess.run([binary('ffprobe'), '-v', 'error', '-show_format', '-show_streams',
                             '-of', 'json', str(path)], capture_output=True, text=True, check=True)
    info = json.loads(result.stdout)
    videos = [s for s in info['streams'] if s['codec_type'] == 'video']
    require(len(videos) == 1, 'Expected exactly one video stream')
    s = videos[0]
    duration = float(info['format']['duration'])
    require(math.isfinite(duration) and duration > 0, 'Video is empty')
    return dict(width=s['width'], height=s['height'], duration=duration,
                frame_rate=s.get('avg_frame_rate'), streams=info['streams'])


def decode(path):
    subprocess.run([binary('ffmpeg'), '-v', 'error', '-xerror', '-i', str(path),
                    '-map', '0:v:0', '-f', 'null', '-'], check=True, capture_output=True)


def pixel_bounds(bounds, origin, scale):
    require(all(math.isfinite(v) for v in [*bounds, *origin, *scale]), 'Nonfinite bounds')
    require(min(scale) > 0 and bounds[2] > 0 and bounds[3] > 0, 'Invalid dimensions')
    x, y, w, h = bounds
    sx, sy = scale
    result = [round((x-origin[0])*sx), round((y-origin[1])*sy),
              int(w*sx)//2*2, int(h*sy)//2*2]
    require(min(result[:2]) >= 0 and min(result[2:]) >= 2, 'Region outside display')
    return result


def record(run, device, crop, duration=None, startup_timeout=15):
    data = load(run)
    require(data['status'] == 'prepared', 'Create a new run for each capture attempt')
    require(len(crop) == 4 and min(crop[:2]) >= 0 and min(crop[2:]) >= 2,
            'Supply measured content-only pixel bounds x y width height')
    require(crop[2] % 2 == 0 and crop[3] % 2 == 0, 'Crop dimensions must be even')
    if duration is not None:
        require(math.isfinite(duration) and duration > 0, 'Duration must be positive')
    raw = own(run, 'work/raw.mp4')
    log = own(run, 'work/capture.log')
    stop = own(run, 'work/stop')
    x, y, w, h = crop
    cmd = [binary('ffmpeg'), '-hide_banner', '-loglevel', 'warning', '-n',
           '-f', 'avfoundation', '-framerate', '30', '-pixel_format', 'nv12',
           '-i', f'{device}:none', '-vf', f'crop={w}:{h}:{x}:{y}', '-r', '30', '-an',
           '-c:v', 'libx264', '-preset', 'ultrafast', '-crf', '18',
           '-progress', 'pipe:1', '-stats_period', '0.1']
    if duration:
        cmd += ['-t', str(duration)]
    cmd.append(str(raw))
    events = queue.Queue()
    interrupted = threading.Event()
    previous = {s: signal.signal(s, lambda *_: interrupted.set())
                for s in (signal.SIGINT, signal.SIGTERM)}
    started = time.monotonic()
    failure = None
    proc = None
    try:
        with log.open('w') as log_file:
            proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                    stderr=log_file, text=True)
            def progress():
                for line in proc.stdout:
                    events.put(line.strip())
            threading.Thread(target=progress, daemon=True).start()
            data = load(run)
            data.update(status='starting', capture=dict(device=device, crop=crop))
            save(run, data)
            ready = False
            while proc.poll() is None:
                while not events.empty():
                    line = events.get_nowait()
                    if line.startswith('out_time_us=') and not ready:
                        value = line.split('=', 1)[1]
                        if value.lstrip('-').isdigit() and int(value) > 0:
                            data = load(run)
                            data.update(status='recording', clock=time.monotonic()-int(value)/1e6)
                            save(run, data)
                            ready = True
                            print('Recording ready; begin the flow.', flush=True)
                if stop.exists() or interrupted.is_set():
                    break
                if not ready and time.monotonic() - started > startup_timeout:
                    failure = 'No frames received; check Screen Recording permission for the launching app'
                    break
                time.sleep(0.1)
            if proc.poll() is None:
                try:
                    proc.stdin.write('q\n')
                    proc.stdin.flush()
                    proc.wait(timeout=10)
                except (BrokenPipeError, subprocess.TimeoutExpired):
                    proc.terminate()
                    try:
                        proc.wait(timeout=3)
                    except subprocess.TimeoutExpired:
                        proc.kill()
                        proc.wait()
            require(not failure, failure)
            require(proc.returncode == 0, f'Capture failed; inspect {log}')
            info = probe(raw)
            data = load(run)
            data.update(status='captured', source=info)
            save(run, data)
    except BaseException as exc:
        data = load(run)
        data.update(status='blocked', blocker=str(exc), complete=False)
        save(run, data)
        raise
    finally:
        if proc and proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=3)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait()
        if proc:
            for pipe in (proc.stdin, proc.stdout):
                if pipe:
                    pipe.close()
        for s, handler in previous.items():
            signal.signal(s, handler)


def import_video(run, source, offset=0, move=False):
    data = load(run)
    require(data['status'] in ('prepared', 'external'), 'Cannot replace an existing capture')
    require(math.isfinite(offset), 'Invalid offset')
    info = probe(source)
    raw = own(run, 'work/raw.mp4')
    require(not raw.exists(), 'Raw recording already exists')
    if move:
        shutil.move(str(source), raw)
    else:
        shutil.copyfile(source, raw)
    data = load(run)
    for action in data['actions']:
        action['start'] += offset
        if 'end' in action:
            action['end'] += offset
    data.update(status='captured', source=info, external_offset=offset)
    save(run, data)


def mark(run, label=None, focus=None, at=None, end=False):
    data = load(run)
    require(data['status'] in ('recording', 'external', 'captured'), 'Capture is not ready')
    if at is None:
        require(data['status'] in ('recording', 'external') and 'clock' in data,
                'Use --at for post-capture source timestamps')
        at = time.monotonic() - data['clock']
    require(math.isfinite(at) and at >= 0, 'Timestamp must be finite and nonnegative')
    if end:
        require(data['actions'] and 'end' not in data['actions'][-1], 'No open action')
        require(at > data['actions'][-1]['start'], 'Action end must follow start')
        data['actions'][-1]['end'] = at
    else:
        require(label and (not data['actions'] or 'end' in data['actions'][-1]),
                'Finish the prior action and supply --label')
        if focus:
            require(len(focus) == 4 and all(math.isfinite(v) for v in focus)
                    and min(focus[:2]) >= 0 and min(focus[2:]) > 0, 'Invalid focus rectangle')
        data['actions'].append(dict(label=label, start=at, focus=focus))
    save(run, data)


def intervals(actions, duration):
    require(actions, 'Mark meaningful actions before rendering')
    spans = []
    previous = -1
    for action in actions:
        a, b = action['start'], action.get('end', -1)
        require(all(math.isfinite(v) for v in (a, b)) and 0 <= a < b <= duration + 0.1,
                'Action timestamps must fit the source video; inspect and correct the timeline')
        require(a >= previous, 'Action intervals must be chronological and nonoverlapping')
        previous = b
        lo, hi = max(0, a - 0.4), min(duration, b + 0.8)
        if spans and lo <= spans[-1][1]:
            spans[-1][1] = max(hi, spans[-1][1])
        else:
            spans.append([lo, hi])
    return spans


def map_time(t, spans):
    elapsed = 0
    for a, b in spans:
        if t <= b:
            return elapsed + max(0, t-a)
        elapsed += b-a
    return elapsed


def framing(focus, width, height):
    if not focus:
        return (1.0, 0.5, 0.5)
    x, y, w, h = focus
    require(x >= 0 and y >= 0 and w > 0 and h > 0 and x+w <= width and y+h <= height,
            'Focus rectangle is outside content pixels')
    z = max(1, min(2.2, width/(w*1.5), height/(h*1.5)))
    return z, (x+w/2)/width, (y+h/2)/height


def curve(keys, component):
    expression = f'{keys[-1][1][component]:.8f}'
    for (a, av), (b, bv) in reversed(list(zip(keys, keys[1:]))):
        u = f'clip((on/30-{a:.8f})/{b-a:.8f},0,1)'
        smooth = f'({u}*{u}*(3-2*{u}))'
        value = f'{av[component]:.8f}+({bv[component]-av[component]:.8f})*{smooth}'
        expression = f'if(lt(on/30,{b:.8f}),{value},{expression})'
    return expression


def edit_plan(data):
    info = data['source']
    spans = intervals(data['actions'], info['duration'])
    duration = sum(b-a for a, b in spans)
    full = (1.0, 0.5, 0.5)
    keys = [(0.0, full)]
    for action in data['actions']:
        t = max(keys[-1][0] + 0.6, map_time(action['start'], spans) + 0.6)
        if t < duration - 1.2:
            keys.append((t, framing(action.get('focus'), info['width'], info['height'])))
    if duration > keys[-1][0] + 1.2:
        keys.append((duration - 0.8, keys[-1][1]))
    keys.append((max(duration - 1/30, keys[-1][0]+1/30), full))
    return spans, duration, keys


def render(run):
    data = load(run)
    require(data['status'] in ('captured', 'rendered', 'previewed', 'declined', 'approved', 'upload_uncertain'), 'Capture is not ready to edit')
    require(data['complete'] and data.get('completion_evidence'), 'Verify flow completion before rendering')
    raw = Path(run) / 'work/raw.mp4'
    data['source'] = probe(raw)
    spans, duration, keys = edit_plan(data)
    w, h = data['source']['width'], data['source']['height']
    require(w % 2 == 0 and h % 2 == 0, 'Source dimensions must be even for H.264')
    # Native Device Hub exports are variable-rate and omit unchanged frames.
    # Normalize before trimming so a cut inside a static hold keeps its duration.
    filters = [f'[0:v]setpts=PTS-STARTPTS,fps=30,tpad=stop_mode=clone:stop_duration=1,'
               f'trim=duration={data["source"]["duration"]:.8f},split={len(spans)}' +
               ''.join(f'[in{i}]' for i in range(len(spans)))]
    for i, (a, b) in enumerate(spans):
        filters.append(f'[in{i}]trim=start={a:.8f}:end={b:.8f},setpts=PTS-STARTPTS[s{i}]')
    filters.append(''.join(f'[s{i}]' for i in range(len(spans))) +
                   f'concat=n={len(spans)}:v=1:a=0,fps=30[cut]')
    z, cx, cy = [curve(keys, i) for i in range(3)]
    filters.append(f"[cut]zoompan=z='{z}':x='max(0,min(iw-iw/zoom,iw*({cx})-iw/zoom/2))':"
                   f"y='max(0,min(ih-ih/zoom,ih*({cy})-ih/zoom/2))':d=1:s={w}x{h}:fps=30,"
                   'setsar=1,format=yuv420p[out]')
    script = own(run, 'work/filter.txt')
    script.write_text(';\n'.join(filters))
    timeline = own(run, 'work/timeline.json')
    timeline.write_text(json.dumps(dict(spans=spans, duration=duration, keys=keys), indent=2))
    pending = own(run, 'work/render.mp4')
    subprocess.run([binary('ffmpeg'), '-hide_banner', '-loglevel', 'error', '-nostdin', '-y',
                    '-i', str(raw), '-filter_complex', script.read_text(), '-map', '[out]',
                    '-an', '-c:v', 'libx264', '-preset', 'medium', '-crf', '18',
                    '-t', str(duration), '-movflags', '+faststart', str(pending)], check=True)
    info = probe(pending)
    require(abs(info['duration'] - duration) < 0.15 and info['frame_rate'] == '30/1',
            'Rendered duration/frame rate is incorrect')
    decode(pending)
    final = Path(run) / data['final']
    pending.replace(final)
    data = load(run)
    if data.get('upload_request'):
        data.setdefault('previous_uploads', []).append(dict(
            status=data['status'], request=data['upload_request'], sha256=data['final_sha256'],
            metadata=data.get('upload')))
    for field in ('approval', 'preview', 'upload', 'upload_request'):
        data.pop(field, None)
    data.update(status='rendered', output=info, final_sha256=digest(final))
    save(run, data)
    return final


def current_final(run, data):
    require(Path(data['final']).name == data['final'] and data['final'].endswith('.mp4'),
            'Final file must be a local MP4 basename')
    final = Path(run) / data['final']
    require(not final.is_symlink(), 'Final video cannot be a symlink')
    require(final.is_file() and digest(final) == data.get('final_sha256'), 'Final video changed; render and preview again')
    return final


def previewed(run):
    data = load(run)
    require(data['status'] == 'rendered', 'Render and inspect the video first')
    current_final(run, data)
    data.update(status='previewed', preview=data['final_sha256'])
    save(run, data)


def decision(run, approved):
    data = load(run)
    require(data['status'] in ('previewed', 'declined'), 'Show the current local preview before asking')
    current_final(run, data)
    data['status'] = 'approved' if approved else 'declined'
    data['approval'] = data['final_sha256'] if approved else None
    save(run, data)


def upload_request(run, profile, folder):
    data = load(run)
    require(data['status'] == 'approved' and data.get('approval') == data['final_sha256'],
            'Explicit approval for this preview is required')
    final = current_final(run, data)
    email = profile.get('email', profile.get('emailAddress', ''))
    require(email.lower().endswith('@antaeus.health'), 'Connected account is not Antaeus')
    require(folder.get('id') == FOLDER_ID and folder.get('name', folder.get('title')) == FOLDER_NAME
            and folder.get('mimeType', folder.get('mime_type')) == 'application/vnd.google-apps.folder'
            and not folder.get('trashed', False), 'Destination folder metadata does not match')
    require(folder.get('capabilities', {}).get('canAddChildren') is not False, 'Cannot write to demos folder')
    request = dict(file_uri=str(final.resolve()), file_name=final.name,
                   mime_type='video/mp4', parent_folder_id=FOLDER_ID)
    data.update(status='uploading', upload_request=request)
    save(run, data)
    return request


def verify_upload(run, metadata, downloaded=None):
    data = load(run)
    require(data['status'] in ('uploading', 'upload_uncertain'), 'No approved upload to verify')
    final = current_final(run, data)
    require(data.get('approval') == data['final_sha256'], 'Upload approval is stale')
    link = metadata.get('webViewLink', metadata.get('url', '')) or ''
    if downloaded is not None:
        downloaded = Path(downloaded)
        require(downloaded.resolve() != final.resolve(), 'Read back remote bytes, not the local final')
        matches = downloaded.is_file() and digest(downloaded) == digest(final)
    else:
        matches = metadata.get('md5Checksum') == digest(final, 'md5')
    require(metadata.get('id') and metadata.get('name', metadata.get('title')) == final.name
            and metadata.get('mimeType', metadata.get('mime_type')) == 'video/mp4'
            and not metadata.get('trashed', False)
            and FOLDER_ID in (metadata.get('parents', metadata.get('parent_ids')) or [])
            and int(metadata.get('size') or -1) == final.stat().st_size
            and matches and link.startswith('https://drive.google.com/'),
            'Upload is not verified: compare id, name, parent, MIME, size, bytes and link')
    data.update(status='uploaded', upload=metadata)
    save(run, data)


def cleanup(run):
    data = load(run)
    require(data['status'] in ('uploaded', 'cleaned') and data.get('upload'), 'Verified upload required for cleanup')
    current_final(run, data)
    paths = []
    for relative in data['owned']:
        paths.append(own(run, relative))
    for path in paths:
        if path.exists():
            require(path.is_file(), 'Refusing to remove a directory')
    for path in paths:
        path.unlink(missing_ok=True)
    data = load(run)
    data['status'] = 'cleaned'
    save(run, data)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    p = sub.add_parser('new')
    p.add_argument('--name', required=True)
    p.add_argument('--target', choices=['web', 'ios'], required=True)
    p.add_argument('--root', default=str(Path.home() / 'Movies' / 'Antaeus Demos'))
    sub.add_parser('devices')
    p = sub.add_parser('bounds')
    p.add_argument('--rect', nargs=4, type=float, required=True)
    p.add_argument('--origin', nargs=2, type=float, default=[0, 0])
    p.add_argument('--scale', nargs=2, type=float, required=True)
    for name in ['record', 'stop', 'clock', 'import', 'mark', 'finish', 'render', 'previewed',
                 'decision', 'upload-request', 'upload-uncertain', 'verify-upload', 'cleanup']:
        p = sub.add_parser(name)
        p.add_argument('run', type=Path)
        if name == 'record':
            p.add_argument('--device', type=int, required=True)
            p.add_argument('--crop', type=int, nargs=4, required=True)
            p.add_argument('--duration', type=float)
        elif name == 'import':
            p.add_argument('source', type=Path)
            p.add_argument('--offset', type=float, default=0)
            p.add_argument('--move', action='store_true', help='Adopt a newly created export into this run')
        elif name == 'mark':
            p.add_argument('--label')
            p.add_argument('--focus', type=float, nargs=4)
            p.add_argument('--at', type=float)
            p.add_argument('--end', action='store_true')
        elif name == 'finish':
            p.add_argument('--evidence', required=True)
        elif name == 'decision':
            p.add_argument('answer', choices=['approve', 'decline'])
        elif name == 'upload-request':
            p.add_argument('--profile', type=Path, required=True)
            p.add_argument('--folder', type=Path, required=True)
        elif name == 'verify-upload':
            p.add_argument('metadata', type=Path)
            p.add_argument('--downloaded', type=Path)
    args = parser.parse_args()
    c = args.command
    if c == 'new':
        print(new_run(args.root, args.name, args.target))
    elif c == 'devices':
        result = subprocess.run([binary('ffmpeg'), '-hide_banner', '-f', 'avfoundation',
                                 '-list_devices', 'true', '-i', ''], capture_output=True, text=True)
        print(result.stderr)  # Listing deliberately exits nonzero without an input.
    elif c == 'bounds':
        print(*pixel_bounds(args.rect, args.origin, args.scale))
    elif c == 'record':
        record(args.run, args.device, args.crop, args.duration)
    elif c == 'stop':
        require(load(args.run)['status'] in ('starting', 'recording'), 'No active recorder')
        own(args.run, 'work/stop').touch()
    elif c == 'clock':
        data = load(args.run)
        require(data['status'] == 'prepared', 'Clock already started')
        data.update(status='external', clock=time.monotonic())
        save(args.run, data)
    elif c == 'import':
        import_video(args.run, args.source, args.offset, args.move)
    elif c == 'mark':
        mark(args.run, args.label, args.focus, args.at, args.end)
    elif c == 'finish':
        data = load(args.run)
        require(data['status'] == 'captured' and args.evidence.strip(), 'Finalize capture and verify the result first')
        intervals(data['actions'], data['source']['duration'])
        data.update(complete=True, completion_evidence=args.evidence)
        save(args.run, data)
    elif c == 'render':
        print(render(args.run))
    elif c == 'previewed':
        previewed(args.run)
    elif c == 'decision':
        decision(args.run, args.answer == 'approve')
    elif c == 'upload-request':
        print(json.dumps(upload_request(args.run, json.loads(args.profile.read_text()),
                                        json.loads(args.folder.read_text())), indent=2))
    elif c == 'upload-uncertain':
        data = load(args.run)
        require(data['status'] == 'uploading', 'No upload in progress')
        data['status'] = 'upload_uncertain'
        save(args.run, data)
    elif c == 'verify-upload':
        verify_upload(args.run, json.loads(args.metadata.read_text()), args.downloaded)
    elif c == 'cleanup':
        cleanup(args.run)


if __name__ == '__main__':
    try:
        main()
    except (ValueError, OSError, subprocess.CalledProcessError) as error:
        print(f'Blocked: {error}', file=sys.stderr)
        sys.exit(1)
