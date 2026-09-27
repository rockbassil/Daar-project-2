"""Run collection, indexing, graph and validation, with durable progress logs."""
import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--target', type=int, default=1700)
    parser.add_argument('--delay', type=float, default=2)
    args = parser.parse_args()
    if args.target < 1664:
        parser.error('Use the collect --seed command for development; full preparation requires at least 1664 books.')
    data = ROOT / 'data'
    data.mkdir(exist_ok=True)
    status_path = data / 'preparation.json'
    status = {'pid': os.getpid(), 'target': args.target, 'started': datetime.now(timezone.utc).isoformat()}

    def save(stage, **extra):
        status.update(stage=stage, updated=datetime.now(timezone.utc).isoformat(), **extra)
        temporary = status_path.with_suffix('.tmp')
        temporary.write_text(json.dumps(status, indent=2), encoding='utf-8')
        temporary.replace(status_path)

    stages = [('collect', ['collect', '--target', str(args.target), '--delay', str(args.delay)]),
              ('index', ['index']), ('graph', ['graph']), ('validate', ['validate'])]
    env = dict(os.environ, PYTHONUTF8='1', PYTHONUNBUFFERED='1')
    with (data / 'preparation.log').open('a', encoding='utf-8', buffering=1) as log:
        for name, command in stages:
            save(name)
            print(f'{name}: started', flush=True)
            log.write(f'\n{status["updated"]} — {name}\n')
            result = subprocess.run([sys.executable, '-m', 'library', *command], cwd=ROOT,
                                    env=env, stdout=log, stderr=subprocess.STDOUT)
            if result.returncode:
                save('failed', failed_stage=name, exit_code=result.returncode)
                print(f'{name} failed. See data/preparation.log; rerun to resume.', flush=True)
                return result.returncode
            print(f'{name}: finished', flush=True)
    save('complete', exit_code=0)
    print('Full corpus, index and graph are ready.', flush=True)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
