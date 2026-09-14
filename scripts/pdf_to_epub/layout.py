"""Conservative layout defaults and verified print-artifact recognition."""
from collections import Counter, defaultdict
import re
import statistics

from .extract import contains, overlaps
from .model import normalized, ConversionError


def signature(line):
    return re.sub(r'\d+', '#', line.text.casefold())


def infer(pages, config, metadata):
    lines = [l for p in pages for l in p.lines if len(l.text) > 35 and .12 * p.height < l.top < .8 * p.height]
    if not lines:
        raise ConversionError('No usable text layer; scanned PDFs are unsupported.')
    font, size = Counter((l.font, l.size) for l in lines).most_common(1)[0][0]
    # The central sample identifies the font, not the content boundaries.
    body = [l for p in pages for l in p.lines
            if (l.font, l.size) == (font, size) and len(l.text) > 35]
    lay = config['layout']
    defaults = {'body_font': font, 'body_size': size,
                'left': statistics.median(l.x0 for l in body), 'right': statistics.median(l.x1 for l in body),
                'indent': statistics.median(l.x0 for l in body) + size * 1.3, 'line_height': size * 1.35,
                'top': min(l.top for l in body) - size, 'bottom': max(l.bottom for l in body) + size}
    for key, value in defaults.items():
        if lay[key] is None:
            lay[key] = round(value, 2) if isinstance(value, float) else value
    for key, pdfkey in [('title', 'Title'), ('author', 'Author'), ('publisher', 'Publisher')]:
        if config['metadata'][key] is None:
            config['metadata'][key] = str(metadata.get(pdfkey) or '')
    heading_fonts = Counter(l.font for p in pages for l in p.lines if l.size >= size * 1.2 and len(l.text) > 5)
    h = config['headings']
    if h['font'] is None and heading_fonts:
        h['font'] = heading_fonts.most_common(1)[0][0]
    if h['h1_size'] is None:
        h['h1_size'] = size * 1.8
    if h['h2_size'] is None:
        h['h2_size'] = size * 1.2
    candidates = Counter((l.font, l.size) for p in pages for l in p.lines
                         if l.size < lay['body_size'] * .95 and re.match(r'^\d+\.\s', l.text))
    if config['notes']['size'] is None and candidates:
        note_font, note_size = candidates.most_common(1)[0][0]
        config['notes']['font'] = config['notes']['font'] or note_font
        config['notes']['size'] = note_size
    return config


def preflight(pages, config, ledger):
    count = len(pages)
    if config['layout']['left'] >= config['layout']['right']:
        raise ConversionError('layout.left must be less than layout.right.')
    for p in pages:
        for panel in config['pages'].get(p.number, {}).get('panels', []):
            if panel['box'][2] > p.width or panel['box'][3] > p.height:
                raise ConversionError(f'Panel exceeds page {p.number} bounds.')
    for number in config['pages']:
        if number > count:
            raise ConversionError(f'Unknown page: {number}')
    for key in config['line_overrides']:
        if key not in ledger.source:
            raise ConversionError(f'Unknown line override: {key}')
    for section, chapter in config['notes']['sections'].items():
        if section not in ledger.source or chapter not in ledger.source:
            raise ConversionError(f'Unknown endnote section or chapter: {section} -> {chapter}')
        if config['pages'].get(ledger.source[section].page, {}).get('role') != 'endnotes':
            raise ConversionError(f'Endnote section {section} requires the endnotes page role.')
    for item in config['duplicates'] + config['artifacts']:
        for key in [item['line']] + item.get('of', []):
            if key not in ledger.source:
                raise ConversionError(f'Unknown line: {key}')
    for region in config['illustrations'] + ([config['cover']] if config['cover'] else []):
        if region['page'] > count:
            raise ConversionError(f'Unknown crop page: {region["page"]}')
        page = pages[region['page'] - 1]
        b = region['box']
        if b[0] < 0 or b[1] < 0 or b[2] > page.width or b[3] > page.height:
            raise ConversionError(f'Crop exceeds page {page.number} bounds.')
        if region is not config['cover'] and (b[2] - b[0]) * (b[3] - b[1]) > .8 * page.width * page.height:
            raise ConversionError('Full-page illustration fallback is forbidden.')
        for key in region.get('retain_text', []):
            if key not in ledger.source or ledger.source[key].page != page.number or not contains(b, ledger.source[key]):
                raise ConversionError(f'retain_text line is not inside its crop: {key}')
    for i, a in enumerate(config['illustrations']):
        for b in config['illustrations'][i + 1:]:
            if a['page'] == b['page'] and overlaps(a['box'], b['box']):
                raise ConversionError(f'Overlapping illustrations on page {a["page"]}.')
    # Only repeated text in the margins can be removed automatically.
    repeats = defaultdict(set)
    for p in pages:
        for l in p.lines:
            if l.top < config['layout']['top'] or l.top >= config['layout']['bottom']:
                repeats[signature(l)].add(p.number)
    heading_texts = [normalized(''.join(r.text for r in l.runs if not r.superscript)) for p in pages for l in p.lines
                     if config['layout']['top'] <= l.top < config['layout']['bottom'] and l.font == config['headings']['font'] and l.size >= config['headings']['h2_size']]
    for p in pages:
        heads = [l for l in p.lines if config['layout']['top'] <= l.top < config['layout']['bottom'] and l.font == config['headings']['font'] and l.size >= config['headings']['h2_size']]
        for i, first in enumerate(heads):
            text = ''.join(r.text for r in first.runs if not r.superscript)
            for previous, following in zip(heads[i:], heads[i + 1:]):
                if following.top - previous.top > 34:
                    break
                text += ''.join(r.text for r in following.runs if not r.superscript)
                heading_texts.append(normalized(text))
    excluded = {}
    for p in pages:
        rule = config['pages'].get(p.number, {})
        top = rule.get('top', config['layout']['top'])
        bottom = rule.get('bottom', config['layout']['bottom'])
        if top >= bottom or bottom > p.height:
            raise ConversionError(f'Invalid content bounds on page {p.number}.')
        for l in p.lines:
            outside = l.top < top or l.top >= bottom
            if outside and l.top < top and normalized(l.text) in heading_texts:
                excluded[l.id] = 'Running header matches retained heading'
            elif outside and len(repeats[signature(l)]) >= 3:
                excluded[l.id] = 'Repeated running header/footer outside content bounds'
            elif outside and re.fullmatch(r'(?:\d{1,4}|[ivxlcdm]+)', l.text.replace(' ', '')) and (l.top > .7 * p.height or l.top < .12 * p.height):
                excluded[l.id] = 'Margin page number'
        crops = [r['box'] for r in config['illustrations'] if r['page'] == p.number]
        if config['cover'] and config['cover']['page'] == p.number:
            crops.append(config['cover']['box'])
        graphics = p.raster_images or p.marks
        preserved = graphics and all(any(
            crop[0] <= max(0, b[0]) + 1 and crop[1] <= max(0, b[1]) + 1
            and crop[2] >= min(p.width, b[2]) - 1 and crop[3] >= min(p.height, b[3]) - 1
            for crop in crops) for b in graphics)
        if not p.lines and graphics and not preserved:
            ledger.fail('scan', 'Page has graphics but no extractable text; no OCR fallback.', page=p.number)
    for item in config['artifacts']:
        line = ledger.source[item['line']]
        valid = re.fullmatch(r'\d{1,4}', line.text.strip()) if item['kind'] == 'page_number' else re.search(r'\.indd\s+\d+|^\d{2}/\d{2}/\d{4}\s+\d{2}[.:]\d{2}$', line.text)
        if 'reviewed_text' in item:
            height = pages[line.page - 1].height
            margin = line.bottom < height * .05 if item['kind'] == 'running_header' else line.top > height * .9
            valid = margin and line.text == item['reviewed_text']
        if not valid:
            ledger.fail('unverified-exclusion', 'Artifact rule does not match a recognized print artifact.', line)
        else:
            excluded[line.id] = item['kind']
    for item in config['duplicates']:
        line = ledger.source[item['line']]
        targets = [ledger.source[key] for key in item['of']]
        if not targets or any(t.id == line.id or t.id in excluded for t in targets) or normalized(line.text) not in normalized(''.join(t.text for t in targets)):
            ledger.fail('unverified-duplicate', 'Duplicate must exactly match retained source text.', line)
        else:
            excluded[line.id] = 'Verified duplicate of ' + ', '.join(item['of'])
    for p in pages:
        rule = config['pages'].get(p.number, {})
        if rule.get('role') == 'duplicate':
            target = rule['duplicate_of']
            if target > count or config['pages'].get(target, {}).get('role') == 'duplicate':
                raise ConversionError('Duplicate page must reference a retained page.')
            destination = normalized(''.join(l.text for l in pages[target - 1].lines))
            source = normalized(''.join(l.text for l in p.lines if l.id not in excluded))
            if source and source in destination:
                for l in p.lines:
                    excluded[l.id] = f'Verified duplicate of page {target}'
            else:
                ledger.fail('unverified-duplicate', 'Page text is not a contiguous duplicate of its target.', page=p.number)
    for item in config['duplicates']:
        if item['line'] in excluded and any(key in excluded for key in item['of']):
            ledger.fail('excluded-duplicate-target', 'Duplicate points to excluded text; name a retained source.', ledger.source[item['line']])
    return excluded
