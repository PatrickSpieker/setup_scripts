"""Source provenance shared by inspection, conversion, and reporting."""
from __future__ import annotations

import hashlib
import re
import unicodedata
from collections import Counter
from dataclasses import dataclass, field


def normalized(text: str) -> str:
    return ''.join(c for c in unicodedata.normalize('NFKC', text).casefold() if c.isalnum())


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


@dataclass
class Run:
    text: str
    bold: bool = False
    italic: bool = False
    superscript: bool = False


@dataclass
class Line:
    id: str
    page: int
    box: tuple[float, float, float, float]
    text: str
    font: str
    size: float
    runs: list[Run]
    upright: bool = True
    word_boxes: list[tuple] = field(default_factory=list)

    @property
    def x0(self):
        return self.box[0]

    @property
    def top(self):
        return self.box[1]

    @property
    def x1(self):
        return self.box[2]

    @property
    def bottom(self):
        return self.box[3]


@dataclass
class Page:
    number: int
    width: float
    height: float
    lines: list[Line]
    marks: list[tuple]
    raster_images: list[tuple]


@dataclass
class Issue:
    code: str
    message: str
    page: int | None = None
    line: str | None = None
    suggestion: str = ''


@dataclass
class Block:
    kind: str
    chapter: str
    lines: list[Line] = field(default_factory=list)
    runs: list[Run] = field(default_factory=list)
    id: str = ''
    image: str = ''
    caption: str = ''
    note: str = ''
    css: str = ''
    image_notes: list[str] = field(default_factory=list)


class ConversionError(Exception):
    pass


class Ledger:
    """Every nonempty source line needs exactly one verified destination."""

    def __init__(self, pages):
        self.source = {line.id: line for page in pages for line in page.lines}
        self.entries = {}
        self.issues: list[Issue] = []

    def claim(self, line, kind, detail=''):
        if line.id in self.entries:
            self.issues.append(Issue('duplicate-accounting', 'Line was handled more than once.', line.page, line.id))
        else:
            self.entries[line.id] = {'kind': kind, 'detail': detail}

    def fail(self, code, message, line=None, page=None, suggestion=''):
        self.issues.append(Issue(code, message, line.page if line else page, line.id if line else None, suggestion))

    def finish(self, blocks):
        for key, line in self.source.items():
            if key not in self.entries:
                self.fail('unaccounted-content', 'Source line has no destination.', line)
        # Check each block against its own ordered source lines, including cross-page joins.
        represented = Counter()
        for block in blocks:
            if block.kind == 'image':
                represented.update(line.id for line in block.lines)
                continue
            before = normalized(''.join(line.text for line in block.lines))
            after = normalized(''.join(run.text for run in block.runs))
            if before != after:
                self.fail('text-changed', 'Reconstruction changed or reordered substantive characters.',
                          block.lines[0] if block.lines else None)
            represented.update(line.id for line in block.lines)
        for key, entry in self.entries.items():
            if entry['kind'] != 'excluded' and represented[key] != 1:
                self.fail('missing-output', 'Accounted line was not emitted exactly once.', self.source[key])


def heading_key(text):
    return normalized(re.sub(r'^Chapter\s+\d+\.\s*', '', text, flags=re.I))
