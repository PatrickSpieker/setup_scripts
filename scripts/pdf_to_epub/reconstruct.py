"""Reflow text with per-line provenance and explicit ambiguity failures."""
from collections import Counter
from copy import deepcopy
import re

import cmudict

from .extract import contains, overlaps
from .model import Block, Run, normalized


class Builder:
    def __init__(self, pages, config, ledger, excluded):
        self.pages, self.config, self.ledger, self.excluded = pages, config, ledger, excluded
        self.blocks = []
        self.current = None
        self.previous = None
        self.chapter = 'frontmatter'
        self.notes = {}
        self.words = Counter(re.findall(r'[\w]+(?:-[\w]+)*', ' '.join(l.text for p in pages for l in p.lines).casefold()))
        self.dictionary = set(cmudict.words())
        self.joins = []

    def join(self, runs, new, line):
        left, right = ''.join(r.text for r in runs), ''.join(r.text for r in new)
        a, b = re.search(r'(\w+)-$', left), re.match(r'(\w+)', right)
        separator = ' '
        if a and b:
            split = a[1] + '-' + b[1]
            compound, joined = split.casefold(), (a[1] + b[1]).casefold()
            decisions = self.config['hyphenation']
            if split in decisions['keep']:
                keep = True
            elif split in decisions['join']:
                keep = False
            elif self.words[compound] and not self.words[joined]:
                keep = True
            elif (self.words[joined] or joined in self.dictionary) and not self.words[compound]:
                keep = False
            else:
                self.ledger.fail('ambiguous-hyphen', f'Choose whether to keep the hyphen in {split!r}.', line,
                                 suggestion=f'Add {split!r} to hyphenation.keep or hyphenation.join.')
                keep = True
            if not keep:
                for run in reversed(runs):
                    if run.text:
                        run.text = run.text[:-1]
                        break
            separator = ''
            self.joins.append({'line': line.id, 'split': split, 'kept': keep})
        runs.append(Run(separator))
        runs.extend(deepcopy(new))

    def flush(self):
        if self.current:
            self.blocks.append(self.current)
        self.current = None
        self.previous = None

    def heading(self, line, level):
        self.flush()
        if re.match(self.config['headings']['chapter_pattern'], line.text):
            self.chapter = line.id
            level = 'h1'
        elif level == 'h1':
            self.chapter = line.id
        # Consecutive heading lines remain one semantic heading.
        if self.blocks and self.blocks[-1].kind == level and self.blocks[-1].lines[-1].page == line.page:
            previous = self.blocks[-1].lines[-1]
            if line.top - previous.top < 34:
                block = self.blocks[-1]
                self.chapter = block.chapter
                self.join(block.runs, line.runs, line)
                block.lines.append(line)
                self.ledger.claim(line, 'heading', block.id)
                return
        block = Block(level, self.chapter, [line], deepcopy(line.runs), id=line.id)
        self.blocks.append(block)
        self.ledger.claim(line, 'heading', block.id)

    def body(self, line, role, override):
        lay = self.config['layout']
        new = self.current is None
        if self.previous and self.current:
            prev = self.previous
            cross = prev.page != line.page
            full = prev.x1 > lay['right'] - lay['body_size'] * 1.8
            gap = line.top - prev.top
            indent = abs(line.x0 - lay['indent']) <= lay['body_size'] * .4
            text = ''.join(r.text for r in self.current.runs)
            if role == 'references':
                new = line.x0 < lay['left'] + lay['body_size'] * .55
            else:
                new = (not cross and gap > lay['line_height'] * 1.4) or not full
                if indent and (cross or prev.x0 < lay['left'] + lay['body_size'] * .7):
                    new = True
                if re.match(r'^(?:[•●–]|\d{1,2}[.)])\s', line.text):
                    new = True
                if cross and text.rstrip().endswith(('.', '?', '!')):
                    new = True
                if text.endswith('-') and line.text[:1].islower():
                    new = False
                if role == 'jacket':
                    panels = self.config['pages'][line.page].get('panels', [])
                    same_panel = any(contains(panel['box'], line) and contains(panel['box'], prev) for panel in panels)
                    new = not same_panel or gap > line.size * 1.8
                if role in ('frontmatter', 'contents'):
                    new = True
        if override == 'paragraph':
            new = True
        if override == 'continue':
            if not self.current:
                self.ledger.fail('orphan-continuation', 'No preceding paragraph for continue override.', line)
            new = self.current is None
        if new:
            self.flush()
            self.current = Block('p', self.chapter, [line], deepcopy(line.runs), id=line.id,
                                 css='reference' if role == 'references' else ('boxed' if line.font == self.config['headings']['font'] and role == 'body' else ''))
        else:
            self.join(self.current.runs, line.runs, line)
            self.current.lines.append(line)
        self.ledger.claim(line, 'prose', self.current.id)
        self.previous = line

    def note(self, line):
        match = re.match(r'^(\d+)\.\s', line.text)
        if match:
            key = (self.chapter, match[1])
            if key in self.notes:
                self.ledger.fail('duplicate-note', 'Duplicate footnote number in this chapter.', line)
                return
            self.notes[key] = Block('note', self.chapter, [line], deepcopy(line.runs), id=f'note-{self.chapter}-{match[1]}', note=match[1])
        else:
            candidates = [key for key in self.notes if key[0] == self.chapter]
            if not candidates:
                self.ledger.fail('orphan-note', 'Note continuation has no numbered start.', line)
                return
            key = candidates[-1]
            self.join(self.notes[key].runs, line.runs, line)
            self.notes[key].lines.append(line)
        self.ledger.claim(line, 'note', self.notes[key].id)

    def build(self):
        lay, heads = self.config['layout'], self.config['headings']
        for page in self.pages:
            rule = self.config['pages'].get(page.number, {})
            role = rule.get('role', 'body')
            if role in ('frontmatter', 'contents', 'jacket'):
                self.flush()
            regions = [r for r in self.config['illustrations'] if r['page'] == page.number]
            image_lines, images = {}, {}
            for index, region in enumerate(regions):
                selected = [l for l in page.lines if contains(region['box'], l) and l.id not in self.excluded and l.id not in region.get('retain_text', [])]
                if not selected:
                    if not any(overlaps(region['box'], box) for box in page.raster_images + page.marks):
                        self.ledger.fail('empty-illustration', 'Illustration crop has no visible source content.', page=page.number)
                        continue
                    self.flush()
                    self.blocks.append(Block('image', self.chapter, [], id=f'image-{page.number}-{index}',
                                             image=f'images/p{page.number:04}-{index:03}.png', caption=region.get('caption', 'Illustration')))
                    continue
                for line in selected:
                    if line.font == lay['body_font'] and line.size >= lay['body_size'] * .95 and len(line.text) > 40:
                        self.ledger.fail('prose-in-image', 'Crop contains ordinary body prose.', line,
                                         suggestion='Tighten the crop or add this overlapping line to retain_text.')
                block = Block('image', self.chapter, selected, id=selected[0].id,
                              image=f'images/p{page.number:04}-{index:03}.png', caption=region.get('caption', selected[0].text))
                images[selected[0].id] = (block, region)
                image_lines.update({l.id: block for l in selected})
            cover = self.config['cover']
            cover_lines = [l for l in page.lines if cover and cover['page'] == page.number and contains(cover['box'], l) and l.id not in self.excluded]
            if cover_lines:
                cover_block = Block('image', 'cover', cover_lines, id='source-cover', image='images/cover.png', caption='Cover')
                self.blocks.append(cover_block)
            active = [l for l in page.lines if l.id not in self.excluded and l not in cover_lines]
            if role == 'body' and page.width > page.height:
                self.ledger.fail('unsupported-layout', 'Landscape or jacket page requires explicit page roles and panel bounds.', page=page.number)
            ordered = page.lines
            if role == 'jacket':
                panels = rule.get('panels', [])
                ordered = sorted(page.lines, key=lambda line: (next((i for i, panel in enumerate(panels) if contains(panel['box'], line)), -1), line.top, line.x0))
            for line in ordered:
                if line.id in self.excluded:
                    self.ledger.claim(line, 'excluded', self.excluded[line.id])
                    continue
                if line in cover_lines:
                    self.ledger.claim(line, 'image', 'cover')
                    continue
                if line.id in image_lines:
                    if line.id in images:
                        self.flush()
                        block, region = images[line.id]
                        block.chapter = self.chapter
                        self.blocks.append(block)
                    self.ledger.claim(line, 'image', image_lines[line.id].image)
                    continue
                top, bottom = rule.get('top', lay['top']), rule.get('bottom', lay['bottom'])
                if role == 'body' and not top <= line.top < bottom:
                    self.ledger.fail('unclassified-margin', 'Margin text is not a verified print artifact.', line,
                                     suggestion='Correct page bounds or provide a verified duplicate/artifact rule.')
                if role == 'jacket':
                    if not any(contains(panel['box'], line) for panel in rule.get('panels', [])):
                        self.ledger.fail('unclassified-jacket', 'Jacket text lies outside configured panels/cover.', line)
                if not line.upright:
                    self.ledger.fail('rotated-text', 'Rotated text needs an illustration crop; prose cannot be rasterized.', line)
                override = self.config['line_overrides'].get(line.id)
                if override in ('heading1', 'heading2'):
                    self.heading(line, 'h1' if override == 'heading1' else 'h2')
                elif role in ('body', 'references') and (re.match(heads['chapter_pattern'], line.text) or (line.font == heads['font'] and line.size >= heads['h2_size'])):
                    self.heading(line, 'h1' if line.size >= heads['h1_size'] or re.match(heads['chapter_pattern'], line.text) else 'h2')
                elif override == 'note' or (role == 'body' and self.config['notes']['size'] == line.size and (not self.config['notes']['font'] or line.font.startswith(self.config['notes']['font']))):
                    self.note(line)
                else:
                    if not override and re.match(r'^(Figure|Table)\s+\d+[.\d]*', line.text) and line.font != lay['body_font']:
                        self.ledger.fail('uncropped-illustration', 'Figure/table caption requires a whole illustration crop.', line)
                    self.body(line, role, override)
            # Two independent lines sharing a baseline indicate multiple columns.
            if role == 'body':
                prose = [l for l in active if l.id not in image_lines and l.size >= lay['body_size'] * .95 and l.font == lay['body_font']]
                pairs = sum(1 for a, b in zip(prose, prose[1:]) if abs(a.top - b.top) < 2 and a.x1 + lay['body_size'] < b.x0)
                if pairs >= 3:
                    self.ledger.fail('multi-column', 'Multiple prose columns are unsupported.', page=page.number)
            # Large raster content cannot silently disappear.
            for box in page.raster_images:
                if (box[2] - box[0]) * (box[3] - box[1]) < 1000:
                    continue
                crops = [r['box'] for r in regions] + ([cover['box']] if cover and cover['page'] == page.number else [])
                if role != 'duplicate' and not any(overlaps(box, crop) for crop in crops):
                    self.ledger.fail('uncropped-image', 'Raster image has no configured crop.', page=page.number)
        self.flush()
        # Put notes at the end of their chapter, preserving their source order.
        output = []
        for i, block in enumerate(self.blocks):
            output.append(block)
            if i == len(self.blocks) - 1 or self.blocks[i + 1].chapter != block.chapter:
                output.extend(note for (ch, _), note in self.notes.items() if ch == block.chapter)
        # Only source superscripts with a matching note become links.
        refs = Counter()
        for block in output:
            if block.kind == 'note':
                continue
            for run in block.runs:
                if run.superscript and run.text.strip().isdigit():
                    key = (block.chapter, run.text.strip())
                    if key not in self.notes:
                        self.ledger.fail('missing-note', f'Superscript {run.text!r} has no matching note.', block.lines[0])
                    else:
                        refs[key] += 1
            if block.kind == 'image':
                for line in block.lines:
                    for run in line.runs:
                        key = (block.chapter, run.text.strip())
                        if run.superscript and key in self.notes and key[1] not in block.image_notes:
                            block.image_notes.append(key[1])
                            refs[key] += 1
        for key, note in self.notes.items():
            if not refs[key]:
                self.ledger.fail('unreferenced-note', f'Footnote {key[1]} has no source reference.', note.lines[0])
        self.ledger.finish(output)
        return output
