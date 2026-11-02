"""Build a small reproducible source preview or the final assignment archive."""
import argparse
import json
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--preview', action='store_true', help='Package sources/results without claiming final academic completion')
    parser.add_argument('--surnames', nargs='+', help='Two or three actual team surnames')
    parser.add_argument('--report', type=Path, help='Final report PDF')
    parser.add_argument('--video', type=Path, help='Final 4:30–5:30 video')
    args = parser.parse_args()
    if not args.preview:
        if not args.surnames or len(args.surnames) not in (2, 3):
            parser.error('Final submission needs two or three team surnames.')
        if not args.report or not args.report.is_file() or args.report.suffix.lower() != '.pdf':
            parser.error('Provide the final report PDF with --report.')
        if not args.video or not args.video.is_file():
            parser.error('The selected video option needs the final video with --video.')
    names = [name.strip().upper() for name in (args.surnames or ['PREVIEW'])]
    if any(not name or any(char in '<>:"/\\|?*' for char in name) for name in names):
        parser.error('Surnames must be nonempty and contain no filename/path characters.')
    output = ROOT / 'dist'
    output.mkdir(exist_ok=True)
    archive = output / ('daar-assignment2-' + '-'.join(names) + ( '-PREVIEW' if args.preview and args.surnames else '') + '.zip')
    members = []
    for directory in ['library', 'web', 'tests', 'scripts', 'docs', 'reports/final-results',
                      'reports/set-jaccard-results', 'reports/evaluation',
                      'reports/audit-2026-10-20/browser', 'reports/audit-2026-10-20/http']:
        for path in (ROOT / directory).rglob('*'):
            if path.is_file() and '__pycache__' not in path.parts and path.suffix not in ('.pyc', '.log'):
                members.append((path, path.relative_to(ROOT).as_posix()))
    for name in ['README.md', 'run.cmd', 'daar_projet2_en.pdf']:
        members.append((ROOT / name, name))
    for path, name in [(args.report, 'submission/report.pdf'), (args.video, 'submission/' + args.video.name if args.video else '')]:
        if path:
            if not path.is_file():
                parser.error(f'Missing material: {path}')
            members.append((path, name))
    with tempfile.NamedTemporaryFile(dir=output, suffix='.zip.tmp', delete=False) as stream:
        temporary = Path(stream.name)
    try:
        with zipfile.ZipFile(temporary, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=6) as package:
            for path, name in sorted(members, key=lambda item: item[1]):
                package.write(path, name)
            package.writestr('submission/package-status.json', json.dumps({
                'preview': args.preview, 'surnames': names,
                'corpus_included': False,
                'setup': 'python scripts/prepare_library.py --target 1700',
                'note': 'Sources and measurements only; preview is not a complete graded submission.' if args.preview else
                        'Manually verify report page count, video duration/playback, team names, and all academic requirements before uploading.'
            }, indent=2))
        size = temporary.stat().st_size
        if size > 30_000_000:
            parser.error(f'Archive is {size / 1_000_000:.2f} MB, above the conservative 30 MB limit; compress the video.')
        temporary.replace(archive)
    finally:
        temporary.unlink(missing_ok=True)
    with zipfile.ZipFile(archive) as package:
        bad = package.testzip()
        if bad:
            raise RuntimeError(f'Corrupt archive member: {bad}')
    print(f'{archive} ({size / 1_000_000:.2f} MB; {len(members)} files plus package status)')


if __name__ == '__main__':
    main()
