"""Strict, versioned YAML configuration. Coordinates are PDF points, top-origin."""
from __future__ import annotations

import copy
import math
from pathlib import Path

import yaml

from .model import ConversionError

DEFAULT = {
    'version': 1,
    'source_sha256': None,
    'metadata': {'title': None, 'author': None, 'publisher': None, 'language': 'en'},
    'layout': {'top': None, 'bottom': None, 'body_font': None, 'body_size': None,
               'left': None, 'right': None, 'indent': None, 'line_height': None},
    'headings': {'h1_size': None, 'h2_size': None, 'font': None,
                 'chapter_pattern': r'^CHAPTER\s+\d+$'},
    'notes': {'font': None, 'size': None},
    'pages': {},
    'hyphenation': {'keep': [], 'join': []},
    'illustrations': [],
    'duplicates': [],
    'artifacts': [],
    'line_overrides': {},
    'cover': None,
    'render_dpi': 240,
}

PAGE_KEYS = {'role', 'duplicate_of', 'top', 'bottom', 'panels'}
ROLES = {'body', 'frontmatter', 'references', 'contents', 'jacket', 'duplicate'}


class UniqueLoader(yaml.SafeLoader):
    pass


def unique_mapping(loader, node, deep=False):
    result = {}
    for k, v in node.value:
        key = loader.construct_object(k, deep=deep)
        if key in result:
            raise ConversionError(f'Duplicate YAML key: {key}')
        result[key] = loader.construct_object(v, deep=deep)
    return result


UniqueLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, unique_mapping)


def mapping(value, keys, where):
    if not isinstance(value, dict):
        raise ConversionError(f'{where} must be a mapping.')
    extra = set(value) - keys
    if extra:
        raise ConversionError(f'Unknown {where} keys: {sorted(str(k) for k in extra)}')


def number(value, where, low=0, high=10000):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or not low <= value <= high:
        raise ConversionError(f'{where} must be a finite number in [{low}, {high}].')


def box(value, where):
    if not isinstance(value, list) or len(value) != 4:
        raise ConversionError(f'{where} must be [left, top, right, bottom].')
    for n in value:
        number(n, where)
    if value[0] >= value[2] or value[1] >= value[3]:
        raise ConversionError(f'{where} has reversed or empty bounds.')


def validate(config):
    mapping(config, set(DEFAULT), 'profile')
    if type(config.get('version')) is not int or config['version'] != 1:
        raise ConversionError('Only YAML profile version 1 is supported.')
    for group in ('metadata', 'layout', 'headings', 'notes', 'hyphenation'):
        mapping(config[group], set(DEFAULT[group]), group)
    if config['metadata']['language'] != 'en':
        raise ConversionError('Only English-language books are supported (language: en).')
    for key, value in config['metadata'].items():
        if value is not None and not isinstance(value, str):
            raise ConversionError(f'metadata.{key} must be text or null.')
    for key, value in config['layout'].items():
        if value is not None:
            if key == 'body_font':
                if not isinstance(value, str):
                    raise ConversionError('layout.body_font must be text.')
            else:
                number(value, f'layout.{key}')
    for key in ('h1_size', 'h2_size'):
        if config['headings'][key] is not None:
            number(config['headings'][key], f'headings.{key}', 1, 200)
    for key in ('font', 'chapter_pattern'):
        if config['headings'][key] is not None and not isinstance(config['headings'][key], str):
            raise ConversionError(f'headings.{key} must be text.')
    import re
    try:
        re.compile(config['headings']['chapter_pattern'])
    except (re.error, TypeError) as e:
        raise ConversionError(f'Invalid chapter pattern: {e}') from e
    if config['notes']['size'] is not None:
        number(config['notes']['size'], 'notes.size', 1, 200)
    if config['notes']['font'] is not None and not isinstance(config['notes']['font'], str):
        raise ConversionError('notes.font must be text.')
    if config['source_sha256'] is not None and not re.fullmatch('[a-f0-9]{64}', str(config['source_sha256'])):
        raise ConversionError('source_sha256 must be a lowercase SHA-256 digest.')
    number(config['render_dpi'], 'render_dpi', 144, 600)
    for key in ('keep', 'join'):
        if not isinstance(config['hyphenation'][key], list) or not all(isinstance(x, str) and '-' in x for x in config['hyphenation'][key]):
            raise ConversionError(f'hyphenation.{key} must be a list of split words.')
    if set(config['hyphenation']['keep']) & set(config['hyphenation']['join']):
        raise ConversionError('A hyphenation cannot appear in both keep and join.')
    mapping(config['pages'], set(config['pages']) if isinstance(config['pages'], dict) else set(), 'pages')
    for page, rule in config['pages'].items():
        if type(page) is not int or page < 1:
            raise ConversionError('Page keys must be positive integers (one-based PDF pages).')
        mapping(rule, PAGE_KEYS, f'pages.{page}')
        if rule.get('role', 'body') not in ROLES:
            raise ConversionError(f'Unsupported page role on page {page}; full-page image fallback is forbidden.')
        for key in ('top', 'bottom'):
            if key in rule:
                number(rule[key], f'pages.{page}.{key}')
        if rule.get('role') == 'duplicate' and (type(rule.get('duplicate_of')) is not int or rule['duplicate_of'] == page or rule['duplicate_of'] < 1):
            raise ConversionError('Duplicate pages must name a different duplicate_of page.')
        if 'panels' in rule:
            if not isinstance(rule['panels'], list):
                raise ConversionError('panels must be a list.')
            for panel in rule['panels']:
                mapping(panel, {'box', 'title'}, 'panel')
                box(panel.get('box'), 'panel.box')
                if not isinstance(panel.get('title'), str):
                    raise ConversionError('Panel title must be text.')
    for name, keys in [('illustrations', {'page', 'box', 'rotate', 'caption', 'retain_text'}),
                       ('duplicates', {'line', 'of'}), ('artifacts', {'line', 'kind'})]:
        if not isinstance(config[name], list):
            raise ConversionError(f'{name} must be a list.')
        for rule in config[name]:
            mapping(rule, keys, name)
            if name == 'illustrations':
                if type(rule.get('page')) is not int or rule['page'] < 1:
                    raise ConversionError('Illustration page must be a positive integer.')
                box(rule.get('box'), 'illustration.box')
                if rule.get('rotate', 0) not in (0, 90, 180, 270):
                    raise ConversionError('Rotation must be 0, 90, 180, or 270 clockwise degrees.')
                if 'caption' in rule and not isinstance(rule['caption'], str):
                    raise ConversionError('Illustration caption must be text.')
                if not isinstance(rule.get('retain_text', []), list) or not all(isinstance(s, str) for s in rule.get('retain_text', [])):
                    raise ConversionError('retain_text must list line IDs.')
            else:
                if not isinstance(rule.get('line'), str):
                    raise ConversionError(f'{name}.line must be a source line ID.')
                if name == 'duplicates' and (not isinstance(rule.get('of'), list) or not all(isinstance(s, str) for s in rule['of'])):
                    raise ConversionError('duplicates.of must list source line IDs.')
                if name == 'artifacts' and rule.get('kind') not in ('page_number', 'printer_mark'):
                    raise ConversionError('Artifact exclusions support only verified page_number and printer_mark rules.')
    mapping(config['line_overrides'], set(config['line_overrides']) if isinstance(config['line_overrides'], dict) else set(), 'line_overrides')
    for key, value in config['line_overrides'].items():
        if not isinstance(key, str) or value not in ('paragraph', 'continue', 'heading1', 'heading2', 'note'):
            raise ConversionError('Line overrides support paragraph, continue, heading1, heading2, or note.')
    if config['cover'] is not None:
        mapping(config['cover'], {'page', 'box'}, 'cover')
        if type(config['cover'].get('page')) is not int or config['cover']['page'] < 1:
            raise ConversionError('cover.page must be a positive integer.')
        box(config['cover'].get('box'), 'cover.box')
    return config


def load(path: Path | None):
    config = copy.deepcopy(DEFAULT)
    if path:
        try:
            supplied = yaml.load(path.read_text(), Loader=UniqueLoader)
        except (OSError, yaml.YAMLError, TypeError) as e:
            raise ConversionError(f'Cannot read profile: {e}') from e
        mapping(supplied, set(DEFAULT), 'profile')
        for key, value in supplied.items():
            if key in ('metadata', 'layout', 'headings', 'notes', 'hyphenation'):
                mapping(value, set(DEFAULT[key]), key)
                config[key].update(value)
            else:
                config[key] = value
    return validate(config)


def dump(config):
    return yaml.safe_dump(config, sort_keys=False, allow_unicode=True)
