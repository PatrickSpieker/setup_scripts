"""Self-contained, offline HTML inspection and conversion reports."""
import base64
import html
import io
import json
import os
from pathlib import Path
import tempfile

import pdfplumber

from .config import dump


def atomic_write(path, data):
    path = Path(path)
    with tempfile.NamedTemporaryFile(dir=path.parent, prefix='.' + path.name, delete=False) as stream:
        temporary = Path(stream.name)
        try:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        except BaseException:
            temporary.unlink(missing_ok=True)
            raise
    try:
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def write_report(path, pdf_path, pages, config, ledger, versions, status, joins):
    esc = html.escape
    parts = ['<!doctype html><meta charset="utf-8"><title>PDF to EPUB report</title>',
             '<style>body{font:16px system-ui;margin:2rem;max-width:1200px}img{max-width:500px;width:100%}table{border-collapse:collapse;width:100%}td,th{padding:.3rem;border:1px solid #ccc;text-align:left}pre{white-space:pre-wrap}summary{cursor:pointer}a{color:#146}</style>',
             f'<h1>{esc(status)}</h1><p>Automatic checks do not certify visual quality. Review prose, notes, figures, and reading order.</p>',
             '<p>Line IDs use one-based PDF pages and extracted line order. Bounds use PDF points from the top left.</p>',
             '<h2>Issues</h2><ul>']
    for issue in ledger.issues:
        target = f'line-{issue.line}' if issue.line else f'page-{issue.page}'
        parts.append(f'<li><a href="#{target}">{esc(issue.code)}</a>: {esc(issue.message)} {esc(issue.suggestion)}</li>')
    parts.append('</ul><details><summary>Effective configuration</summary><pre>' + esc(dump(config)) + '</pre></details>')
    parts.append('<details><summary>Versions and normalization</summary><pre>' + esc(json.dumps(versions, indent=2)) + '</pre><p>NFKC Unicode normalization; layout whitespace joined; configured discretionary hyphens removed. Original spelling is otherwise retained.</p><pre>' + esc(json.dumps(joins, ensure_ascii=False, indent=2)) + '</pre></details>')
    if pages:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pages:
                preview = pdf.pages[page.number - 1].to_image(resolution=55).original
                preview.thumbnail((700, 900))
                image = io.BytesIO()
                preview.convert('RGB').save(image, 'JPEG', quality=65)
                data = base64.b64encode(image.getvalue()).decode()
                parts.append(f'<details id="page-{page.number}"><summary>Page {page.number} — {len(page.lines)} lines</summary><img alt="Page {page.number}" src="data:image/jpeg;base64,{data}"/><table><tr><th>Line</th><th>Bounds / font</th><th>Text</th><th>Destination</th></tr>')
                for line in page.lines:
                    entry = ledger.entries.get(line.id, {'kind': 'unaccounted', 'detail': ''})
                    parts.append(f'<tr id="line-{line.id}"><td>{line.id}</td><td>{esc(str([round(n,1) for n in line.box]))}<br>{esc(line.font)} {line.size}</td><td>{esc(line.text)}</td><td>{esc(entry["kind"])}: {esc(entry["detail"])}</td></tr>')
                parts.append('</table></details>')
                pdf.pages[page.number - 1].close()
    atomic_write(path, ''.join(parts).encode())
