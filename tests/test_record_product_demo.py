"""Exercise video transforms and the preview/upload/cleanup boundary without cloud writes."""
import importlib.util
import json
from datetime import datetime, timezone
from pathlib import Path
import shutil
import subprocess

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / 'skills/record-product-demo/scripts/demo.py'
spec = importlib.util.spec_from_file_location('product_demo', SCRIPT)
demo = importlib.util.module_from_spec(spec)
spec.loader.exec_module(demo)


@pytest.fixture
def run(tmp_path):
    return demo.new_run(tmp_path, 'Connect a Provider!', 'web')


def test_new_york_timestamp_and_collision(tmp_path):
    summer = datetime(2026, 7, 1, 12, tzinfo=timezone.utc)
    winter = datetime(2026, 1, 1, 12, tzinfo=timezone.utc)
    assert demo.basename('A / B', summer) == '2026-07-01_08_00_00_a_b'
    assert demo.basename('A / B', winter) == '2026-01-01_07_00_00_a_b'
    # Fall-back repeats a wall-clock hour; directory creation still prevents overwrite.
    assert demo.basename('x', datetime(2026, 11, 1, 5, 30, tzinfo=timezone.utc)) == demo.basename(
        'x', datetime(2026, 11, 1, 6, 30, tzinfo=timezone.utc))
    a = demo.new_run(tmp_path, 'demo', 'web')
    b = demo.new_run(tmp_path, 'demo', 'web')
    assert a != b and a.exists() and b.exists()
    with pytest.raises(ValueError):
        demo.basename('!!!')


def test_retina_and_secondary_display():
    assert demo.pixel_bounds([1540, 100, 801, 503], [1440, 0], [2, 2]) == [200, 200, 1602, 1006]
    assert demo.pixel_bounds([-1000, 20, 601, 401], [-1440, 0], [1, 1]) == [440, 20, 600, 400]
    with pytest.raises(ValueError):
        demo.pixel_bounds([0, 0, 100, 100], [100, 0], [2, 2])
    with pytest.raises(ValueError):
        demo.pixel_bounds([0, 0, float('nan'), 100], [0, 0], [2, 2])


def test_trim_and_map_time():
    actions = [dict(start=1, end=2), dict(start=6, end=7), dict(start=7.2, end=8)]
    spans = demo.intervals(actions, 10)
    assert spans == [[0.6, 2.8], [5.6, 8.8]]
    for bad in ([dict(start=1)], [dict(start=5, end=4)], [dict(start=1, end=11)],
                [dict(start=0, end=2), dict(start=1, end=3)]):
        with pytest.raises(ValueError):
            demo.intervals(bad, 10)


def test_edit_plan_ignores_legacy_focus():
    data = dict(source=dict(width=320, height=240, duration=10), actions=[
        dict(start=0, end=3, focus=[0, 0, 50, 50]),
        dict(start=6, end=9, focus=[250, 160, 50, 50])])
    spans, duration = demo.edit_plan(data)
    assert spans == [[0, 3.8], [5.6, 9.8]]
    assert duration == pytest.approx(8)


def prepared_video(run):
    data = demo.load(run)
    final = run / data['final']
    final.write_bytes(b'test-video-bytes')
    raw = demo.own(run, 'work/raw.mp4')
    raw.write_bytes(b'raw')
    demo.own(run, 'work/filter.txt').write_text('filter')
    data = demo.load(run)
    data.update(status='rendered', complete=True, final_sha256=demo.digest(final))
    demo.save(run, data)
    return final, raw


def destination():
    return {'email': 'patrick@antaeus.health'}, {
        'id': demo.FOLDER_ID, 'name': demo.FOLDER_NAME,
        'mimeType': 'application/vnd.google-apps.folder', 'capabilities': {'canAddChildren': True}}


def receipt(final):
    return dict(id='observed-file-id', name=final.name, mimeType='video/mp4',
                parents=[demo.FOLDER_ID], size=str(final.stat().st_size),
                md5Checksum=demo.digest(final, 'md5'), webViewLink='https://drive.google.com/file/d/observed-file-id/view')


def approve(run):
    demo.previewed(run)
    demo.decision(run, True)
    return demo.upload_request(run, *destination())


def test_no_upload_or_cleanup_before_preview_and_approval(run):
    _, raw = prepared_video(run)
    with pytest.raises(ValueError):
        demo.decision(run, True)
    with pytest.raises(ValueError):
        demo.upload_request(run, *destination())
    with pytest.raises(ValueError):
        demo.cleanup(run)
    demo.previewed(run)
    demo.decision(run, False)
    with pytest.raises(ValueError):
        demo.cleanup(run)
    assert raw.exists()


def test_modified_video_invalidates_approval(run):
    final, raw = prepared_video(run)
    demo.previewed(run)
    demo.decision(run, True)
    final.write_bytes(b'changed')
    with pytest.raises(ValueError, match='changed'):
        demo.upload_request(run, *destination())
    assert raw.exists()


def test_destination_identity_and_write_denial(run):
    prepared_video(run)
    demo.previewed(run)
    demo.decision(run, True)
    profile, folder = destination()
    with pytest.raises(ValueError, match='Antaeus'):
        demo.upload_request(run, {'email': 'someone@example.com'}, folder)
    with pytest.raises(ValueError, match='Destination'):
        demo.upload_request(run, profile, {**folder, 'id': 'other'})
    folder['capabilities']['canAddChildren'] = False
    with pytest.raises(ValueError, match='Cannot write'):
        demo.upload_request(run, profile, folder)


def test_verified_upload_and_scoped_cleanup(run):
    final, raw = prepared_video(run)
    unrelated = run / 'work/unrelated.txt'
    unrelated.write_text('keep')
    args = approve(run)
    assert args['file_uri'] == str(final) and args['parent_folder_id'] == demo.FOLDER_ID
    with pytest.raises(ValueError):
        demo.verify_upload(run, {**receipt(final), 'parents': ['wrong']})
    with pytest.raises(ValueError):
        demo.verify_upload(run, {**receipt(final), 'md5Checksum': 'bad'})
    assert raw.exists()
    # A timeout does not revoke consent, but does prevent deletion until readback succeeds.
    data = demo.load(run)
    data['status'] = 'upload_uncertain'
    demo.save(run, data)
    with pytest.raises(ValueError):
        demo.cleanup(run)
    demo.verify_upload(run, receipt(final))
    demo.cleanup(run)
    demo.cleanup(run)  # idempotent
    assert final.exists() and unrelated.exists() and not raw.exists()


def test_normalized_connector_metadata_requires_remote_bytes(run, tmp_path):
    final, raw = prepared_video(run)
    demo.previewed(run)
    demo.decision(run, True)
    demo.upload_request(run, {'email': 'patrick@antaeus.health'}, {
        'id': demo.FOLDER_ID, 'title': demo.FOLDER_NAME,
        'mime_type': 'application/vnd.google-apps.folder'})
    metadata = dict(id='remote', title=final.name, mime_type='video/mp4', parent_ids=[demo.FOLDER_ID],
                    size=final.stat().st_size, url='https://drive.google.com/file/d/remote/view')
    with pytest.raises(ValueError):
        demo.verify_upload(run, metadata)
    with pytest.raises(ValueError):
        demo.verify_upload(run, metadata, final)
    downloaded = tmp_path / 'downloaded.mp4'
    downloaded.write_bytes(b'wrong')
    with pytest.raises(ValueError):
        demo.verify_upload(run, metadata, downloaded)
    downloaded.write_bytes(final.read_bytes())
    demo.verify_upload(run, metadata, downloaded)
    assert raw.exists()  # verification alone does not delete


def test_cleanup_rejects_escape_and_symlink(run, tmp_path):
    final, raw = prepared_video(run)
    approve(run)
    demo.verify_upload(run, receipt(final))
    outside = tmp_path / 'unrelated'
    outside.write_text('retain')
    for entry in ['../unrelated', str(outside)]:
        data = demo.load(run)
        data['owned'].append(entry)
        demo.save(run, data)
        with pytest.raises(ValueError):
            demo.cleanup(run)
        data['owned'].pop()
        demo.save(run, data)
    link = run / 'work/link'
    link.symlink_to(outside)
    data = demo.load(run)
    data['owned'].append('work/link')
    demo.save(run, data)
    with pytest.raises(ValueError):
        demo.cleanup(run)
    assert raw.exists() and outside.read_text() == 'retain'


def test_source_alignment_and_incomplete_flow(run, monkeypatch, tmp_path):
    source = tmp_path / 'device.mov'
    source.write_bytes(b'video')
    monkeypatch.setattr(demo, 'probe', lambda _: dict(width=320, height=240, duration=10))
    data = demo.load(run)
    data.update(status='external', actions=[dict(start=1, end=2, focus=None)])
    demo.save(run, data)
    demo.import_video(run, source, 1.2)
    assert demo.load(run)['actions'][0]['start'] == 2.2
    with pytest.raises(ValueError, match='completion'):
        demo.render(run)
    assert source.exists()


def test_missing_ffmpeg(monkeypatch):
    monkeypatch.setattr(shutil, 'which', lambda _: None)
    with pytest.raises(ValueError, match='missing'):
        demo.binary('ffmpeg')


@pytest.mark.skipif(not shutil.which('ffmpeg'), reason='FFmpeg needed for video integration')
@pytest.mark.parametrize('sparse', [False, True])
def test_real_video_edit_and_decode(run, tmp_path, sparse):
    source = tmp_path / 'motion.mp4'
    subprocess.run(['ffmpeg', '-v', 'error', '-f', 'lavfi', '-i',
                    'testsrc2=size=320x240:rate=30:duration=8',
                    *(['-vf', "select='eq(mod(n,45),0)+eq(n,239)'", '-fps_mode', 'vfr'] if sparse else []),
                    '-c:v', 'libx264', str(source)], check=True)
    demo.import_video(run, source)
    demo.mark(run, 'First action', at=0)
    demo.mark(run, at=2, end=True)
    demo.mark(run, 'Second action', at=5)
    demo.mark(run, at=7.5, end=True)
    data = demo.load(run)
    data.update(complete=True, completion_evidence='Both fixture actions complete')
    demo.save(run, data)
    final = demo.render(run)
    info = demo.probe(final)
    assert info['width'] == 320 and info['height'] == 240 and info['frame_rate'] == '30/1'
    assert info['duration'] == pytest.approx(6.2, abs=.04)
    assert len(info['streams']) == 1
    if not sparse:
        def frame(path):
            return subprocess.check_output([
                'ffmpeg', '-v', 'error', '-i', str(path), '-vf', "fps=30,select='eq(n,30)'",
                '-frames:v', '1', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'])
        before, after = frame(source), frame(final)
        assert len(before) == len(after) == 320 * 240 * 3
        # Full-content framing survives encoding; a zoom/pan changes these pixels substantially.
        assert sum(abs(a-b) for a, b in zip(before, after)) / len(before) < 3
    demo.decode(final)
    demo.previewed(run)
    demo.decision(run, True)
    demo.upload_request(run, *destination())
    pending = demo.load(run)
    pending["status"] = "upload_uncertain"
    demo.save(run, pending)
    demo.render(run)
    assert len(demo.load(run)["previous_uploads"]) == 1
    assert demo.load(run)['status'] == 'rendered' and 'approval' not in demo.load(run)


def test_stalled_recorder_is_stopped_and_reported(run, tmp_path, monkeypatch):
    fake = tmp_path / 'fake-ffmpeg'
    fake.write_text('#!/usr/bin/env python3\nimport sys\nsys.stdin.readline()\n')
    fake.chmod(0o755)
    monkeypatch.setattr(demo, 'binary', lambda _: str(fake))
    with pytest.raises(ValueError, match='No frames'):
        demo.record(run, 3, [0, 0, 320, 240], startup_timeout=.05)
    data = demo.load(run)
    assert data['status'] == 'blocked' and not data['complete']
    assert 'permission' in data['blocker']
    assert (run / 'work/capture.log').exists()


def test_bad_capture_bounds_rejected_without_recording(run):
    with pytest.raises(ValueError, match='even'):
        demo.record(run, 3, [0, 0, 321, 240])
    with pytest.raises(ValueError, match='Duration'):
        demo.record(run, 3, [0, 0, 320, 240], duration=-1)
    assert demo.load(run)['status'] == 'prepared'


def test_adopt_native_export_retains_raw_until_upload(run, tmp_path, monkeypatch):
    source = tmp_path / 'new-device-export.mp4'
    source.write_bytes(b'original capture')
    monkeypatch.setattr(demo, 'probe', lambda _: dict(width=320, height=240, duration=10))
    demo.import_video(run, source, move=True)
    assert not source.exists()
    assert (run / 'work/raw.mp4').read_bytes() == b'original capture'
    with pytest.raises(ValueError):
        demo.cleanup(run)
