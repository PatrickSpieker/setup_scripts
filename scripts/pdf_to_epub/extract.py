"""Positioned text extraction, without guessing whitespace from glyph gaps."""
from collections import Counter
from difflib import SequenceMatcher
import unicodedata

import pdfplumber

from .model import Line, Page, Run, ConversionError, normalized


def extract(path, config=None):
    pages = []
    with pdfplumber.open(path) as pdf:
        metadata = dict(pdf.metadata or {})
        for n, page in enumerate(pdf.pages, 1):
            lines = []
            raw_lines = []
            rule = (config or {}).get('pages', {}).get(n, {})
            regions = rule.get('reading_regions')
            text_options = {'y_tolerance': rule['text_y_tolerance']} if 'text_y_tolerance' in rule else {}
            if regions:
                crops = [page.within_bbox(tuple(box)) for box in regions]
                source_chars = Counter((c['text'], c['x0'], c['top']) for c in page.chars)
                selected_chars = Counter((c['text'], c['x0'], c['top']) for crop in crops for c in crop.chars)
                if source_chars != selected_chars:
                    raise ConversionError(f'Reading regions must contain every glyph exactly once on page {n}.')
                original_lines = [line for crop in crops for line in crop.extract_text_lines(**text_options)]
            else:
                original_lines = page.extract_text_lines(**text_options)
            for raw in original_lines:
                # A wide gutter is a column boundary, never a prose space.
                groups = [[]]
                ordered = sorted(raw['chars'], key=lambda c: c['x0'])
                for char in ordered:
                    if groups[-1] and char.get('upright', True) and char['x0'] - max(c['x1'] for c in groups[-1]) > max(char['size'] * 4, 30):
                        groups.append([])
                    groups[-1].append(char)
                if len(groups) == 1:
                    raw_lines.append(raw)
                else:
                    glyph_groups = [(t, index) for index, group in enumerate(groups) for c in group
                                    for t in unicodedata.normalize('NFKC', c['text']) if not t.isspace()]
                    target = unicodedata.normalize('NFKC', raw['text'])
                    compact = ''.join(target.split())
                    owners = {}
                    for match in SequenceMatcher(None, ''.join(t for t, _ in glyph_groups), compact, autojunk=False).get_matching_blocks():
                        for off in range(match.size):
                            owners[match.b + off] = glyph_groups[match.a + off][1]
                    texts = ['' for _ in groups]
                    position = 0
                    owner = owners.get(0, 0)
                    for char in target:
                        if not char.isspace():
                            owner = owners.get(position, owner)
                            position += 1
                        texts[owner] += char
                    for index, group in enumerate(groups):
                        raw_lines.append({'chars': group, 'text': texts[index].strip(),
                                          'x0': min(c['x0'] for c in group), 'x1': max(c['x1'] for c in group),
                                          'top': min(c['top'] for c in group), 'bottom': max(c['bottom'] for c in group)})
            before = Counter(normalized(''.join(l['text'] for l in original_lines)))
            after = Counter(normalized(''.join(l['text'] for l in raw_lines)))
            if before != after:
                raise ConversionError(f'Column separation changed source characters on page {n}.')
            ordered_lines = raw_lines if regions else sorted(raw_lines, key=lambda l: (l['top'], l['x0']))
            for i, raw in enumerate(ordered_lines, 1):
                chars = [c for c in raw['chars'] if c['text'].strip()]
                if not chars:
                    continue
                font, size = Counter((c['fontname'].split('+')[-1], round(c['size'], 1)) for c in chars).most_common(1)[0][0]
                baseline = max(c['bottom'] for c in chars if round(c['size'], 1) == size)
                glyphs = [(t, 'Bold' in c['fontname'], 'Italic' in c['fontname'],
                           round(c['size'], 1) <= round(size * .8, 1)
                           and c['bottom'] < baseline - size * .15 and t.isdigit())
                          for c in sorted(chars, key=lambda c: c['x0'])
                          for t in unicodedata.normalize('NFKC', c['text']) if not t.isspace()]
                target = unicodedata.normalize('NFKC', raw['text']).strip()
                source = ''.join(c[0] for c in glyphs)
                wanted = ''.join(target.split())
                styles = {}
                for match in SequenceMatcher(None, source, wanted, autojunk=False).get_matching_blocks():
                    for off in range(match.size):
                        styles[match.b + off] = glyphs[match.a + off][1:]
                runs = []
                pos = 0
                for char in target:
                    style = (False, False, False) if char.isspace() else styles.get(pos, (False, False, False))
                    if not char.isspace():
                        pos += 1
                    if runs and (runs[-1].bold, runs[-1].italic, runs[-1].superscript) == style:
                        runs[-1].text += char
                    else:
                        runs.append(Run(char, *style))
                lines.append(Line(f'p{n:04}-l{i:04}', n, tuple(raw[k] for k in ('x0', 'top', 'x1', 'bottom')),
                                  target, font, size, runs, all(c.get('upright', True) for c in chars)))
            marks = [tuple(obj[k] for k in ('x0', 'top', 'x1', 'bottom')) for obj in page.lines + page.rects + page.curves]
            images = [tuple(obj[k] for k in ('x0', 'top', 'x1', 'bottom')) for obj in page.images]
            pages.append(Page(n, float(page.width), float(page.height), lines, marks, images))
            page.close()
    return pages, metadata


def contains(box, line, tolerance=1):
    return (line.x0 >= box[0] - tolerance and line.top >= box[1] - tolerance
            and line.x1 <= box[2] + tolerance and line.bottom <= box[3] + tolerance)


def overlaps(a, b):
    return a[0] < b[2] and a[2] > b[0] and a[1] < b[3] and a[3] > b[1]
