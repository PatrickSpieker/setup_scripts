"""The command entry point: inspect freely; publish only validated EPUBs."""
import argparse
import hashlib
from importlib.metadata import version as package_version
from pathlib import Path
import platform
import sys
import re
import tempfile

from . import config as configuration
from .extract import extract
from .layout import infer, preflight
from .model import ConversionError, Ledger
from .package import package, version
from .reconstruct import Builder
from .report import atomic_write, write_report


def main():
    parser = argparse.ArgumentParser(prog='pdf-to-epub')
    sub = parser.add_subparsers(dest='command', required=True)
    for name in ('inspect', 'convert'):
        command = sub.add_parser(name)
        command.add_argument('pdf', type=Path)
        command.add_argument('--profile', type=Path)
        command.add_argument('--output', type=Path, required=name == 'convert', help='EPUB destination; inspection only uses its directory/stem')
    args = parser.parse_args()
    source = args.pdf.resolve()
    output = (args.output or source.with_suffix('.epub')).resolve()
    profile = args.profile.resolve() if args.profile else None
    report = output.with_suffix('.report.html')
    effective = output.with_suffix('.effective.yaml')
    # Protect inputs even when paths use symlinks or hard links.
    paths = [output, report, effective]
    for target in paths:
        for input_path in [source] + ([profile] if profile else []):
            if target == input_path or (target.exists() and input_path.exists() and target.samefile(input_path)):
                parser.error(f'Artifact path aliases an input: {target}')
    if output.suffix.lower() != '.epub':
        parser.error('--output must end in .epub')
    if not output.parent.is_dir():
        parser.error('Output directory does not exist.')
    config = configuration.load(None)
    pages, ledger, versions, joins = [], Ledger([]), {}, []
    result = 1
    try:
        config = configuration.load(profile)
        for dependency, pinned in re.findall(r'^([\w.-]+)==([^\s]+)', Path(__file__).with_name('requirements.lock').read_text(), re.M):
            if package_version(dependency) != pinned:
                raise ConversionError(f'Dependency version mismatch: {dependency}; rerun the installer.')
        if sys.version_info[:2] != (3, 12):
            raise ConversionError('Python 3.12 is required; rerun the installer.')
        if sys.platform != 'darwin':
            raise ConversionError('Only macOS is supported.')
        if not source.is_file() or source.suffix.lower() != '.pdf':
            raise ConversionError('Input must be an existing PDF file.')
        sha = hashlib.sha256(source.read_bytes()).hexdigest()
        if config['source_sha256'] and config['source_sha256'] != sha:
            raise ConversionError('Profile source_sha256 does not match this PDF.')
        config['source_sha256'] = sha
        versions = {name: package_version(name) for name in ('pdfplumber', 'pdfminer.six', 'pypdfium2', 'Pillow', 'lxml', 'PyYAML', 'cmudict')}
        versions.update({'python': platform.python_version(), 'platform': platform.platform()})
        pages, metadata = extract(source, config)
        ledger = Ledger(pages)
        infer(pages, config, metadata)
        excluded = preflight(pages, config, ledger)
        builder = Builder(pages, config, ledger, excluded)
        blocks = builder.build()
        joins = builder.joins
        if not config['metadata']['title']:
            ledger.fail('missing-title', 'Set metadata.title in the profile.')
        with tempfile.TemporaryDirectory(prefix='pdf-to-epub-') as tmp:
            root = Path(tmp)
            versions['calibre'] = version(root)
            if args.command == 'convert' and not ledger.issues:
                final = package(source, blocks, config, versions, root)
                # Write reports before replacing an existing book.
                atomic_write(effective, configuration.dump(config).encode())
                write_report(report, source, pages, config, ledger, versions, 'Conversion passed', joins)
                atomic_write(output, final.read_bytes())
                print(output)
                return 0
        result = 0 if args.command == 'inspect' else 1
    except Exception as error:
        ledger.fail('conversion-failed', str(error))
    status = 'Inspection — configuration required' if args.command == 'inspect' else 'Conversion failed — EPUB not replaced'
    atomic_write(effective, configuration.dump(config).encode())
    write_report(report, source, pages, config, ledger, versions, status, joins)
    print(f'{len(ledger.issues)} issue(s). Report: {report}\nProfile: {effective}', file=sys.stderr if result else sys.stdout)
    return result


if __name__ == '__main__':
    raise SystemExit(main())
