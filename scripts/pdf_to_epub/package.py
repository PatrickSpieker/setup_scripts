"""Isolated Calibre packaging, structural checks, and reproducible ZIP output."""
from collections import Counter
import hashlib
import html
import io
import json
import os
from pathlib import Path
import subprocess
import zipfile

from lxml import etree
import pdfplumber

from .model import ConversionError, normalized

CALIBRE = Path('/Applications/calibre.app/Contents/MacOS')
CSS = '''body{font-family:serif;line-height:1.4;margin:0 5%}p{margin:0 0 .65em}
h1,h2{font-family:sans-serif;line-height:1.2;page-break-after:avoid}h1{font-size:1.65em}h2{font-size:1.2em}
figure{margin:1em 0;text-align:center;page-break-inside:avoid}img{max-width:100%;height:auto}
.boxed{font-family:sans-serif;font-size:.92em;margin-left:.65em;padding-left:.75em;border-left:2px solid #79988d}.footnote{font-size:.85em}.reference{padding-left:1em;text-indent:-1em}sup{font-size:.7em;line-height:0}
a{text-decoration:none}'''


def environment(root):
    config = root / 'calibre-config'
    config.mkdir(exist_ok=True)
    return {**os.environ, 'CALIBRE_CONFIG_DIRECTORY': str(config), 'CALIBRE_NO_DEFAULT_PROGRAMS': '1',
            'CALIBRE_OVERRIDE_LANG': 'en', 'TZ': 'UTC', 'QT_QPA_PLATFORM': 'offscreen',
            'PYTHONHASHSEED': '0', 'SOURCE_DATE_EPOCH': '946684800'}


def command(args, root):
    result = subprocess.run([str(arg) for arg in args], env=environment(root), cwd=root,
                            text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    with (root / 'calibre.log').open('a') as log:
        log.write(result.stdout)
    if result.returncode:
        raise ConversionError(f'{Path(args[0]).name} failed ({result.returncode}): {result.stdout[-6000:]}')
    return result.stdout


def version(root):
    for tool in ('ebook-convert', 'ebook-polish', 'calibre-debug'):
        if not (CALIBRE / tool).is_file():
            raise ConversionError(f'Missing Calibre tool: {CALIBRE / tool}. Install Calibre first.')
    return command([CALIBRE / 'ebook-convert', '--version'], root).strip()


def rasterize(pdf_path, config, blocks, root):
    (root / 'images').mkdir()
    with pdfplumber.open(pdf_path) as pdf:
        for block in blocks:
            if block.kind != 'image':
                continue
            if block.id == 'source-cover':
                rule = config['cover']
            else:
                page = int(Path(block.image).stem.split('-')[0][1:])
                index = int(Path(block.image).stem.split('-')[-1])
                rule = [r for r in config['illustrations'] if r['page'] == page][index]
            image = pdf.pages[rule['page'] - 1].crop(tuple(rule['box'])).to_image(resolution=config['render_dpi']).original
            if rule.get('rotate'):
                image = image.rotate(-rule['rotate'], expand=True)
            image.convert('RGB').save(root / block.image, format='PNG', optimize=False)


def source_html(blocks, config):
    refs = Counter()
    def link(chapter, no):
        refs[(chapter, no)] += 1
        return f'<a id="ref-{chapter}-{no}-{refs[(chapter, no)]}" href="#note-{chapter}-{no}">{html.escape(no)}</a>'
    def markup(block):
        parts = []
        for run in block.runs:
            text = html.escape(run.text)
            if run.superscript:
                if config['notes']['mode'] == 'linked' and block.kind != 'note' and run.text.strip().isdigit():
                    text = link(block.chapter, run.text.strip())
                text = '<sup>' + text + '</sup>'
            if run.italic:
                text = '<em>' + text + '</em>'
            if run.bold:
                text = '<strong>' + text + '</strong>'
            parts.append(text)
        return ''.join(parts)
    body = []
    for block in blocks:
        if block.id == 'source-cover':
            continue  # Calibre emits this same image as the cover page.
        if block.kind == 'image':
            body.append(f'<figure id="{block.id}"><img src="{block.image}" alt="{html.escape(block.caption, quote=True)}"/>')
            for no in block.image_notes:
                body.append('<p>Note ' + link(block.chapter, no) + '</p>')
            body.append('</figure>')
        else:
            tag = 'p' if block.kind == 'note' else block.kind
            css = 'footnote' if block.kind == 'note' else block.css
            body.append(f'<{tag} id="{block.id}" class="{css}">{markup(block)}')
            if block.kind == 'note':
                body.append(f' <a href="#ref-{block.chapter}-{block.note}-1">↩</a>')
            body.append(f'</{tag}>')
    title = html.escape(config['metadata']['title'])
    return f'<html xmlns="http://www.w3.org/1999/xhtml"><head><title>{title}</title><link rel="stylesheet" href="style.css"/></head><body>{"".join(body)}</body></html>'


def normalize_epub(path, identity):
    parser = etree.XMLParser(resolve_entities=False, no_network=True)
    with zipfile.ZipFile(path) as archive:
        contents = {name: archive.read(name) for name in archive.namelist()}
    for name, data in list(contents.items()):
        if name.endswith(('.opf', '.ncx')):
            tree = etree.fromstring(data, parser)
            for elem in tree.iter():
                local = etree.QName(elem).localname
                if local == 'identifier':
                    elem.text = 'urn:sha256:' + identity
                elif local == 'date' or (local == 'meta' and elem.get('property') in ('dcterms:modified', 'calibre:timestamp')):
                    elem.text = '2000-01-01T00:00:00Z'
                if local == 'meta' and elem.get('name') == 'dtb:uid':
                    elem.set('content', 'urn:sha256:' + identity)
            contents[name] = etree.tostring(tree, encoding='utf-8', xml_declaration=True)
    output = io.BytesIO()
    # Stored entries avoid compression-library variation; PNGs are already compressed.
    with zipfile.ZipFile(output, 'w', compression=zipfile.ZIP_STORED) as archive:
        for name in ['mimetype'] + sorted(set(contents) - {'mimetype'}):
            info = zipfile.ZipInfo(name, (2000, 1, 1, 0, 0, 0))
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            archive.writestr(info, contents[name])
    path.write_bytes(output.getvalue())


def validate_epub(path, root):
    script = root / 'validate.py'
    script.write_text('''import sys
from calibre.gui2 import Application
app = Application([])
from calibre.ebooks.oeb.polish.container import get_container
from calibre.ebooks.oeb.polish.check.main import run_checks
errors = run_checks(get_container(sys.argv[1]))
for error in errors:
    print(str(error))
sys.exit(1 if errors else 0)
''')
    command([CALIBRE / 'calibre-debug', script, path], root)


def verify_packaged_text(path, blocks):
    parser = etree.XMLParser(resolve_entities=False, no_network=True)
    found = {}
    with zipfile.ZipFile(path) as archive:
        for name in archive.namelist():
            if name.endswith(('.html', '.xhtml')):
                tree = etree.fromstring(archive.read(name), parser)
                for element in tree.iter():
                    key = element.get('id')
                    if key:
                        found.setdefault(key, []).append(element)
    for block in blocks:
        if block.kind == 'image':
            continue
        matches = found.get(block.id, [])
        if len(matches) != 1:
            raise ConversionError(f'Packaged content missing or duplicated: {block.id}')
        actual = normalized(''.join(matches[0].itertext()))
        expected = normalized(''.join(run.text for run in block.runs))
        if actual != expected:
            raise ConversionError(f'Calibre changed text in {block.id}.')


def package(pdf_path, blocks, config, toolchain, root):
    rasterize(pdf_path, config, blocks, root)
    source = source_html(blocks, config)
    (root / 'index.html').write_text(source, encoding='utf-8')
    (root / 'style.css').write_text(CSS)
    args = [CALIBRE / 'ebook-convert', root / 'index.html', root / 'raw.epub',
            '--title', config['metadata']['title'], '--authors', config['metadata']['author'],
            '--author-sort', config['metadata']['author'],
            '--language', 'en', '--publisher', config['metadata']['publisher'],
            '--epub-version', '3', '--output-profile', 'tablet', '--disable-font-rescaling',
            '--chapter', '//h:h1', '--chapter-mark', 'pagebreak', '--page-breaks-before', '/',
            '--level1-toc', '//h:h1', '--level2-toc', '//h:h2', '--no-default-epub-cover']
    if config['cover']:
        args.extend(['--cover', root / 'images/cover.png'])
    command(args, root)
    command([CALIBRE / 'ebook-polish', '--remove-unused-css', root / 'raw.epub', root / 'final.epub'], root)
    identity = hashlib.sha256(json.dumps({'config': config, 'tools': toolchain}, sort_keys=True).encode()).hexdigest()
    final = root / 'final.epub'
    normalize_epub(final, identity)
    validate_epub(final, root)
    verify_packaged_text(final, blocks)
    return final
