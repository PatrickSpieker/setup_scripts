#!/usr/bin/env python3
"""Durable UI exploration checkpoints and a portable HTML report. Python 3.10+."""
import argparse
import base64
import copy
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile
import time
from urllib.parse import urlsplit, urlunsplit

REASONS = ('production restriction', 'outside requested workflow', 'unreachable', 'exploration limit')
ASSETS = Path(__file__).resolve().parent.parent / 'assets'
ID = re.compile(r'^[a-zA-Z0-9_-]{1,80}$')


def atomic(path, data):
    path = Path(path)
    fd, temporary = tempfile.mkstemp(dir=path.parent, prefix='.' + path.name)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def require(condition, message):
    if not condition:
        raise ValueError(message)


def fields(record, allowed, required):
    require(isinstance(record, dict), 'Expected a JSON object')
    require(not record.keys() - set(allowed.split()), 'Unknown fields: ' + ', '.join(record.keys() - set(allowed.split())))
    for key in required.split():
        require(isinstance(record.get(key), str) and bool(record[key].strip()), f'{key} must be nonempty text')
    for key, value in record.items():
        require(isinstance(value, str), f'{key} must be text')
    if 'id' in record:
        require(bool(ID.fullmatch(record['id'])), 'IDs use letters, digits, underscores and hyphens (max 80)')


def find(graph, collection, identifier):
    matches = [item for item in graph[collection] if item['id'] == identifier]
    require(bool(matches), f'Unknown {collection} ID: {identifier}')
    return matches[0]


def clean_url(value):
    parts = urlsplit(value)
    require(parts.scheme in ('http', 'https'), 'URL must use http or https')
    return urlunsplit((parts.scheme, parts.netloc.rsplit('@', 1)[-1], parts.path, '', ''))


def image_data(path):
    data = path.read_bytes()
    if data.startswith(b'\x89PNG\r\n\x1a\n'):
        mime, suffix = 'image/png', '.png'
    elif data.startswith(b'\xff\xd8\xff'):
        mime, suffix = 'image/jpeg', '.jpg'
    elif data[:4] == b'RIFF' and data[8:12] == b'WEBP':
        mime, suffix = 'image/webp', '.webp'
    else:
        raise ValueError('Screenshot must be PNG, JPEG, or WebP; SVG/HTML is not accepted')
    return data, mime, suffix


def initialize(args):
    require(args.max_states is None or args.max_states > 0, 'max-states must be positive')
    require(args.max_seconds is None or args.max_seconds > 0, 'max-seconds must be positive')
    return {'version': 1, 'title': args.title, 'scope': {
        'app': args.app, 'platform': args.platform, 'mode': args.mode,
        'role': args.role, 'device': args.device, 'theme': args.theme,
        'workflow': args.workflow, 'build': args.build},
        'limits': {'states': args.max_states, 'seconds': args.max_seconds},
        'started_at': time.time(), 'status': 'active',
        'remaining_unknown': True, 'summary': 'Exploration in progress',
        'states': [], 'actions': [], 'changes': []}


def limit_reason(graph):
    limits = graph['limits']
    if limits['states'] is not None and len(graph['states']) >= limits['states']:
        return f"State limit reached ({limits['states']})"
    if limits['seconds'] is not None and time.time() - graph['started_at'] >= limits['seconds']:
        return f"Elapsed time limit reached ({limits['seconds']} seconds, including interruption time)"
    return None


def transition(graph, args, run):
    command = args.command
    record = json.loads(Path(args.input).read_text()) if getattr(args, 'input', None) else None
    if command in ('state', 'action'):
        require(graph['status'] == 'active', 'Run is not active; resume it first')
    if command == 'state':
        fields(record, 'id title key screenshot evidence url prerequisites observations', 'id title key screenshot evidence')
        require(not any(s['id'] == record['id'] for s in graph['states']), 'State ID already exists')
        require(not any(s['key'] == record['key'] for s in graph['states']), 'Equivalent state exists: resolve to its existing ID')
        # Capturing an already in-flight outcome is allowed even after a limit expires.
        reason = limit_reason(graph)
        require(not reason or any(a['status'] == 'in_flight' for a in graph['actions']), reason or '')
        data, _, suffix = image_data(Path(record['screenshot']))
        image_name = hashlib.sha256(data).hexdigest() + suffix
        target = run / 'screenshots' / image_name
        target.parent.mkdir(exist_ok=True)
        if not target.exists():
            target.write_bytes(data)
        record['screenshot'] = 'screenshots/' + image_name
        if record.get('url'):
            record['url'] = clean_url(record['url'])
        graph['states'].append(record)
    elif command == 'action':
        fields(record, 'id from label effect provenance prerequisites', 'id from label effect provenance')
        find(graph, 'states', record['from'])
        require(record['effect'] in ('read-only', 'test-account', 'external'), 'Unknown effect classification')
        require(not any(a['id'] == record['id'] for a in graph['actions']), 'Action ID already exists')
        record['status'] = 'pending'
        graph['actions'].append(record)
    elif command == 'begin':
        require(graph['status'] == 'active', 'Run is not active; resume it first')
        action = find(graph, 'actions', args.id)
        require(action['status'] == 'pending', 'Only pending actions may begin; reconcile in-flight actions instead')
        require(not any(a['status'] == 'in_flight' for a in graph['actions']), 'Reconcile the current in-flight action first')
        reason = limit_reason(graph)
        if graph['scope']['mode'] == 'production' and action['effect'] == 'external':
            action.update(status='blocked', reason='production restriction', explanation='Effect extends outside the test account')
            return 'BLOCKED: production restriction; do not execute'
        if reason:
            graph.update(status='stopped', summary=reason)
            return 'STOPPED: ' + reason + '; do not execute'
        action['status'] = 'in_flight'
        return 'READY: action checkpointed; execute once through the UI'
    elif command == 'resolve':
        action = find(graph, 'actions', args.id)
        require(action['status'] == 'in_flight', 'Resolve requires an in-flight action')
        find(graph, 'states', args.to)
        require(bool(args.evidence.strip()), 'Resolution requires observed evidence')
        action.update(status='observed', to=args.to, evidence=args.evidence)
    elif command == 'block':
        action = find(graph, 'actions', args.id)
        require(action['status'] in ('pending', 'in_flight'), 'Only pending/in-flight actions may be blocked')
        require(bool(args.explanation.strip()), 'Explain why the branch was not explored')
        action.update(status='blocked', reason=args.reason, explanation=args.explanation)
    elif command == 'change':
        fields(record, 'id description original expected status explanation', 'id description status explanation')
        require(record['status'] in ('pending', 'restored', 'left-behind'), 'Unknown restoration status')
        old = next((c for c in graph['changes'] if c['id'] == record['id']), None)
        if old:
            old.update(record)
        else:
            graph['changes'].append(record)
    elif command == 'finish':
        require(bool(args.explanation.strip()), 'Finish requires a coverage explanation')
        if args.status == 'exhausted':
            require(not any(a['status'] in ('pending', 'in_flight') for a in graph['actions']), 'Cannot finish: pending or uncertain actions remain')
            require(bool(graph['states']), 'Cannot claim exhaustion without captures')
        graph.update(status=args.status, summary=args.explanation, remaining_unknown=args.status != 'exhausted')
    elif command == 'resume':
        # Deliberately leave in-flight actions untouched; caller must reconcile.
        graph.update(status='active', remaining_unknown=True, summary='Resumed; reconcile any uncertain actions before continuing')
    else:
        raise ValueError('Unknown mutation: ' + command)
    return 'Saved'


def render(graph, run, output):
    public = copy.deepcopy(graph)
    for state in public['states']:
        path = (run / state['screenshot']).resolve()
        require(path.is_relative_to((run / 'screenshots').resolve()), 'Screenshot escapes run directory')
        data, mime, _ = image_data(path)
        state['image'] = f'data:{mime};base64,' + base64.b64encode(data).decode()
        state.pop('screenshot')
    # Restoration originals are local-only; never embed them in shared HTML.
    public['changes'] = [{k: c[k] for k in ('id', 'description', 'status', 'explanation')} for c in public['changes']]
    payload = json.dumps(public, ensure_ascii=True).replace('<', '\\u003c').replace('>', '\\u003e').replace('&', '\\u0026')
    html = (ASSETS / 'report.html').read_text()
    html = html.replace('/* REPORT_STYLE */', (ASSETS / 'report.css').read_text())
    html = html.replace('/* REPORT_SCRIPT */', (ASSETS / 'report.js').read_text())
    html = html.replace('/* REPORT_DATA */', payload)
    atomic(output, html)


def parser():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--run', type=Path, required=True)
    sub = p.add_subparsers(dest='command', required=True)
    init = sub.add_parser('init')
    for name in ('title', 'app', 'platform', 'role', 'device', 'theme', 'build'):
        init.add_argument('--' + name, required=True)
    init.add_argument('--mode', choices=('production', 'staging'), default='production')
    init.add_argument('--workflow', default='')
    init.add_argument('--max-states', type=int)
    init.add_argument('--max-seconds', type=int)
    for name in ('state', 'action', 'change'):
        sub.add_parser(name).add_argument('--input', required=True)
    sub.add_parser('begin').add_argument('id')
    resolve = sub.add_parser('resolve')
    resolve.add_argument('id')
    resolve.add_argument('--to', required=True)
    resolve.add_argument('--evidence', required=True)
    block = sub.add_parser('block')
    block.add_argument('id')
    block.add_argument('--reason', choices=REASONS, required=True)
    block.add_argument('--explanation', required=True)
    finish = sub.add_parser('finish')
    finish.add_argument('--status', choices=('exhausted', 'stopped'), required=True)
    finish.add_argument('--explanation', required=True)
    sub.add_parser('resume')
    sub.add_parser('inspect')
    sub.add_parser('render').add_argument('--output', type=Path)
    return p


def main():
    args = parser().parse_args()
    run = args.run.resolve()
    run.mkdir(parents=True, exist_ok=True)
    try:
        with (run / '.lock').open('w') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            checkpoint = run / 'graph.json'
            if args.command == 'init':
                require(not checkpoint.exists(), 'Run already exists; use inspect/resume')
                graph = initialize(args)
                message = 'Initialized'
            else:
                graph = json.loads(checkpoint.read_text())
                require(graph.get('version') == 1, 'Unsupported checkpoint version')
                if args.command == 'inspect':
                    print(json.dumps(graph, indent=2))
                    return
                message = 'Rendered' if args.command == 'render' else transition(graph, args, run)
            if args.command != 'render':
                atomic(checkpoint, json.dumps(graph, indent=2) + '\n')
            output = getattr(args, 'output', None) or run / 'report.html'
            render(graph, run, output)
            print(message + ': ' + str(output))
    except (ValueError, OSError, KeyError) as error:
        raise SystemExit(str(error)) from error


if __name__ == '__main__':
    main()
