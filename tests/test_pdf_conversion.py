"""Regression tests for layout, illustrated pages, and chapter endnotes."""
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
try:
    import cmudict
    import pdfplumber
    import yaml
    import lxml
except ModuleNotFoundError as error:
    raise unittest.SkipTest('Run PDF tests with the installed pdf-to-epub Python environment.') from error
from pdf_to_epub.config import load
from pdf_to_epub.extract import extract
from pdf_to_epub.layout import infer, preflight
from pdf_to_epub.model import Block, ConversionError, Ledger, Line, Page, Run
from pdf_to_epub.reconstruct import Builder
from pdf_to_epub.package import source_html


def line(no, text, top, page=1, size=12, runs=None):
    return Line(f'p{page:04}-l{no:04}', page, (50, top, 550, top + size),
                text, 'Body', size, runs or [Run(text)])


def config():
    c = load(None)
    c['metadata']['title'] = 'Test'
    c['layout'].update(top=40, bottom=750, body_font='Body', body_size=12,
                       left=50, right=550, indent=65, line_height=14)
    c['headings'].update(font='Heading', h1_size=24, h2_size=18)
    return c


class ConversionTests(unittest.TestCase):
    def test_ragged_right_text_stays_in_one_paragraph(self):
        first = line(1, 'A short line that', 50)
        first.box = (50, 50, 400, 62)
        p = Page(1, 612, 792, [first, line(2, 'continues here.', 64)], [], [])
        ledger = Ledger([p])
        blocks = Builder([p], config(), ledger, {}).build()
        self.assertEqual(len(blocks), 1)
        self.assertEqual(''.join(r.text for r in blocks[0].runs), 'A short line that continues here.')

    def test_superscript_threshold_tolerates_pdf_float_rounding(self):
        chars = [dict(text=t, x0=50+i*10, x1=60+i*10, top=top, bottom=bottom,
                      size=size, fontname='Body', upright=True)
                 for i, (t, size, top, bottom) in enumerate([
                     ('A', 12, 50, 62), ('1', 9.6000000001, 49, 58.6), ('b', 12, 50, 62)])]
        class FakePage:
            width, height = 612, 792
            lines, rects, curves, images = [], [], [], []
            def extract_text_lines(self):
                return [dict(chars=chars, text='A1b', x0=50, x1=80, top=49, bottom=62)]
            def close(self):
                pass
        with patch('pdf_to_epub.extract.pdfplumber.open') as mocked:
            mocked.return_value.__enter__.return_value.pages = [FakePage()]
            mocked.return_value.__enter__.return_value.metadata = {}
            pages, _ = extract('unused.pdf')
        self.assertEqual([r.text for r in pages[0].lines[0].runs if r.superscript], ['1'])

    def test_inference_uses_outer_body_lines(self):
        lines = [line(i, 'This is a sufficiently long line of ordinary body text.', y)
                 for i, y in enumerate([58, 100, 400, 620, 720], 1)]
        c = load(None)
        infer([Page(1, 612, 792, lines, [], [])], c, {})
        self.assertLessEqual(c['layout']['top'], 58)
        self.assertGreater(c['layout']['bottom'], 720)

    def test_image_only_page_requires_complete_crop(self):
        page = Page(1, 612, 792, [], [], [(50, 50, 500, 700)])
        c = config()
        for crop, fails in [(None, True), ([50, 50, 100, 100], True), ([50, 50, 500, 700], False)]:
            c['illustrations'] = [] if crop is None else [{'page': 1, 'box': crop}]
            ledger = Ledger([page])
            preflight([page], c, ledger)
            self.assertEqual(any(i.code == 'scan' for i in ledger.issues), fails)

    def test_image_only_cover_emitted(self):
        c = config()
        c['cover'] = {'page': 1, 'box': [50, 50, 500, 700]}
        p = Page(1, 612, 792, [], [], [(50, 50, 500, 700)])
        ledger = Ledger([p])
        blocks = Builder([p], c, ledger, {}).build()
        self.assertEqual([b.id for b in blocks], ['source-cover'])
        self.assertFalse(ledger.issues)

    def test_image_stays_between_surrounding_paragraphs(self):
        c = config()
        c['illustrations'] = [{'page': 1, 'box': [50, 100, 500, 200]}]
        p = Page(1, 612, 792, [line(1, 'Before.', 50), line(2, 'After.', 220)], [], [(50, 100, 500, 200)])
        ledger = Ledger([p])
        blocks = Builder([p], c, ledger, {}).build()
        self.assertEqual([b.kind for b in blocks], ['p', 'image', 'p'])
        self.assertFalse(ledger.issues)

    def test_endnotes_keep_source_order_and_link_to_body_chapter(self):
        c = config()
        c['pages'][2] = {'role': 'endnotes'}
        c['notes'].update(start_pattern=r'^(\d{1,2})\s', sections={'p0002-l0001': 'p0001-l0001'})
        c['line_overrides']['p0001-l0001'] = 'heading1'
        pages = [Page(1, 612, 792, [line(1, 'Chapter One', 50),
                  line(2, 'Text1', 100, runs=[Run('Text'), Run('1', superscript=True)])], [], []),
                 Page(2, 612, 792, [line(1, 'Notes for One', 50, page=2, size=24),
                  line(2, '1 A note from', 100, page=2), line(3, '1815 continues here.', 114, page=2)], [], [])]
        ledger = Ledger(pages)
        blocks = Builder(pages, c, ledger, {}).build()
        self.assertFalse(ledger.issues, ledger.issues)
        self.assertEqual([b.kind for b in blocks], ['h1', 'p', 'h2', 'note'])
        note = blocks[-1]
        self.assertEqual(len(note.lines), 2)
        html = source_html(blocks, c)
        self.assertIn('href="#note-p0001-l0001-1"', html)
        self.assertIn('href="#ref-p0001-l0001-1-1"', html)

    def test_unmatched_reference_still_fails(self):
        c = config()
        p = Page(1, 612, 792, [line(1, 'Text1', 50, runs=[Run('Text'), Run('1', superscript=True)])], [], [])
        ledger = Ledger([p])
        Builder([p], c, ledger, {}).build()
        self.assertIn('missing-note', [i.code for i in ledger.issues])

    def test_preserved_notes_do_not_create_broken_links(self):
        c = config()
        c['notes']['mode'] = 'preserve'
        p = Page(1, 612, 792, [line(1, 'Text1', 50, runs=[Run('Text'), Run('1', superscript=True)])], [], [])
        ledger = Ledger([p])
        blocks = Builder([p], c, ledger, {}).build()
        self.assertFalse(ledger.issues)
        self.assertIn('<sup>1</sup>', source_html(blocks, c))
        self.assertNotIn('<a ', source_html(blocks, c))

    def test_soft_hyphen_reflows_without_word_space(self):
        p = Page(1, 612, 792, [line(1, 'A trans\u00ad', 50), line(2, 'formation.', 64)], [], [])
        ledger = Ledger([p])
        blocks = Builder([p], config(), ledger, {}).build()
        self.assertFalse(ledger.issues)
        self.assertEqual(''.join(r.text for r in blocks[0].runs), 'A transformation.')

    def test_index_second_column_has_separate_entries(self):
        c = config()
        c['pages'][1] = {'role': 'references', 'reading_regions': [[0, 0, 300, 792], [300, 0, 612, 792]]}
        lines = [line(1, 'Alpha, 1', 50), line(2, 'Beta, 2', 50), line(3, 'Gamma, 3', 64)]
        lines[0].box = (50, 50, 200, 62)
        lines[1].box = (350, 50, 500, 62)
        lines[2].box = (350, 64, 500, 76)
        p = Page(1, 612, 792, lines, [], [])
        ledger = Ledger([p])
        blocks = Builder([p], c, ledger, {}).build()
        self.assertEqual(len(blocks), 3)
        self.assertFalse(ledger.issues)

    def test_reviewed_artifact_cannot_exclude_body_text(self):
        c = config()
        z = line(1, 'Ordinary prose', 200)
        c['artifacts'] = [{'line': z.id, 'kind': 'running_header', 'reviewed_text': z.text}]
        page = Page(1, 612, 792, [z], [], [])
        ledger = Ledger([page])
        self.assertNotIn(z.id, preflight([page], c, ledger))
        self.assertIn('unverified-exclusion', [i.code for i in ledger.issues])

    def test_reading_regions_preserve_columns_and_reject_missing_glyphs(self):
        class FakePage:
            width, height = 612, 792
            lines, rects, curves, images = [], [], [], []
            def __init__(self, chars):
                self.chars = chars
            def within_bbox(self, box):
                return FakePage([c for c in self.chars if c['x0'] >= box[0] and c['x1'] <= box[2]])
            def extract_text_lines(self):
                return [dict(c, chars=[c]) for c in sorted(self.chars, key=lambda c: (c['top'], c['x0']))]
            def close(self):
                pass
        chars = [dict(text=t, x0=x, x1=x+80, top=y, bottom=y+12,
                      size=12, fontname='Body', upright=True)
                 for t, x, y in [('Alpha', 50, 50), ('Beta', 50, 64), ('Gamma', 350, 50), ('Delta', 350, 64)]]
        c = config()
        c['pages'][1] = {'reading_regions': [[0, 0, 300, 792], [300, 0, 612, 792]]}
        with patch('pdf_to_epub.extract.pdfplumber.open') as mocked:
            mocked.return_value.__enter__.return_value.pages = [FakePage(chars)]
            mocked.return_value.__enter__.return_value.metadata = {}
            pages, _ = extract('unused.pdf', c)
            self.assertEqual([l.text for l in pages[0].lines], ['Alpha', 'Beta', 'Gamma', 'Delta'])
            c['pages'][1]['reading_regions'].pop()
            with self.assertRaises(ConversionError):
                extract('unused.pdf', c)


if __name__ == '__main__':
    unittest.main()
