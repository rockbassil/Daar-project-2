"""Test the preview source archive in a clean temporary extraction, without network access."""
import json
import subprocess
import sys
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def main():
    archive = ROOT / 'dist/daar-assignment2-PREVIEW.zip'
    evidence = ROOT / 'reports/audit-2026-10-20'
    evidence.mkdir(parents=True, exist_ok=True)
    checks = []
    with tempfile.TemporaryDirectory(prefix='package-check-', dir=ROOT / 'dist') as directory:
        extracted = Path(directory).resolve()
        if not extracted.is_relative_to((ROOT / 'dist').resolve()):
            raise ValueError('Temporary extraction must remain inside project dist.')
        with zipfile.ZipFile(archive) as package:
            if package.testzip() is not None:
                raise ValueError('Archive integrity failed.')
            for name in package.namelist():
                if not (extracted / name).resolve().is_relative_to(extracted):
                    raise ValueError(f'Unsafe archive member: {name}')
            package.extractall(extracted)
        for command in [[sys.executable, '-m', 'unittest', 'discover', '-s', 'tests', '-v'],
                        [sys.executable, '-m', 'library', '--help'],
                        [sys.executable, 'scripts/build_report.py']]:
            result = subprocess.run(command, cwd=extracted, capture_output=True, text=True,
                                    encoding='utf-8', errors='replace', timeout=120)
            checks.append(dict(command=command[1:], exit_code=result.returncode,
                               stdout=result.stdout, stderr=result.stderr))
        # A clean source checkout must not accidentally carry the bulk dataset.
        no_corpus = not (extracted / 'data/library.sqlite3').exists()
    result = dict(utc=datetime.now(timezone.utc).isoformat(), archive=archive.name,
                  archive_bytes=archive.stat().st_size, archive_integrity=True,
                  clean_extraction=True, network_downloads=False, no_bulk_database=no_corpus,
                  checks=checks, passed=no_corpus and all(c['exit_code'] == 0 for c in checks),
                  scope='Offline source tests, CLI and report HTML build. Full corpus download/rebuild and physical clients excluded.')
    (evidence / 'package-check.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k != 'checks'}, indent=2))
    return 0 if result['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
