"""Resumable corpus collection using the PG catalog and an official mirror."""
import csv
import hashlib
import json
import time
import urllib.error
import urllib.request
from pathlib import Path

from .text import clean_text, normalize_newlines, tokens

CATALOG = 'https://www.gutenberg.org/cache/epub/feeds/pg_catalog.csv'
MIRROR = 'https://mirror.cs.odu.edu/gutenberg-epub'
SEED_IDS = [11, 84, 1342, 1661, 2701, 1400, 98, 74, 76, 174, 345, 1260]


def fetch(url, retries=3, max_bytes=20_000_000):
    request = urllib.request.Request(url, headers={'User-Agent': 'DAAR-BookSearch-StudentProject/1.0'})
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(request, timeout=45) as response:
                return response.read(max_bytes + 1)
        except urllib.error.HTTPError as error:
            if error.code in (404, 403):
                raise
            if attempt + 1 == retries:
                raise
        except (urllib.error.URLError, TimeoutError):
            if attempt + 1 == retries:
                raise
        time.sleep(2 ** (attempt + 1))


def write_json(path, value):
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')
    temporary.replace(path)


def collect(data_dir, target=1700, seed=False, delay=2.0, mirror=MIRROR):
    if target < 1 or delay < 0:
        raise ValueError('Target must be positive and delay non-negative.')
    directory = Path(data_dir)
    books_dir = directory / 'books'
    books_dir.mkdir(parents=True, exist_ok=True)
    catalog = directory / 'pg_catalog.csv'
    if not catalog.exists():
        print('Downloading Gutenberg metadata catalog...', flush=True)
        raw = fetch(CATALOG, max_bytes=100_000_000)
        if len(raw) > 100_000_000:
            raise ValueError('Catalog exceeds download size limit.')
        catalog.write_bytes(raw)
    with catalog.open(encoding='utf-8-sig', newline='') as stream:
        rows = list(csv.DictReader(stream))
    if not rows or not {'Text#', 'Title', 'Authors', 'Language', 'Type'} <= rows[0].keys():
        raise ValueError('Unexpected Gutenberg CSV schema; inspect the saved catalog.')
    state_path = directory / 'collection.json'
    state = json.loads(state_path.read_text(encoding='utf-8')) if state_path.exists() else {}
    hashes = set()
    accepted = 0
    print('Checking saved corpus and reconciling content hashes...', flush=True)
    for path in books_dir.glob('*.json'):
        book = json.loads(path.read_text(encoding='utf-8'))
        text_path = path.with_suffix('.txt')
        if not text_path.exists():
            raise ValueError(f'Missing text for book {book["id"]}: {text_path}')
        # Read without universal-newline conversion so the legacy CRCRLF can
        # be repaired without confusing it with intentional empty lines.
        with text_path.open(encoding='utf-8', newline='') as stream:
            original = stream.read()
        text = normalize_newlines(original)
        content = clean_text(text)
        digest = hashlib.sha256(content.encode('utf-8')).hexdigest()
        count = len(tokens(content))
        if count < 10000:
            raise ValueError(f'Saved book {book["id"]} has only {count:,} words.')
        if digest in hashes:
            raise ValueError(f'Duplicate saved contents at book {book["id"]}.')
        if text != original:
            temporary = text_path.with_suffix('.txt.tmp')
            temporary.write_text(text, encoding='utf-8', newline='')
            temporary.replace(text_path)
        if book['digest'] != digest or book['words'] != count:
            book.update(digest=digest, words=count)
            write_json(path, book)
        hashes.add(digest)
        accepted += 1
        if accepted % 250 == 0:
            print(f'Checked {accepted} saved books.', flush=True)
    candidates = [r for r in rows if r['Type'] == 'Text' and r['Language'].strip() == 'en']
    candidates.sort(key=lambda r: (int(r['Text#']) not in SEED_IDS, int(r['Text#'])))
    if seed:
        candidates = [r for r in candidates if int(r['Text#']) in SEED_IDS]
        target = min(target, len(SEED_IDS))
    print(f'Corpus: {accepted}/{target} valid books. Downloads are resumable.', flush=True)
    failures = 0
    for row in candidates:
        if accepted >= target:
            break
        book_id = int(row['Text#'])
        key = str(book_id)
        if (books_dir / f'{book_id}.json').exists() or state.get(key, {}).get('status') in ('short', 'duplicate', 'missing'):
            continue
        url = f'{mirror.rstrip("/")}/{book_id}/pg{book_id}.txt'
        try:
            raw = fetch(url)
            if len(raw) > 20_000_000:
                raise ValueError('Book exceeds 20 MB download limit.')
            text = normalize_newlines(raw.decode('utf-8-sig'))
            if text.lstrip().lower().startswith(('<!doctype html', '<html')):
                raise ValueError('Mirror returned HTML instead of plain text.')
            content = clean_text(text)
            count = len(tokens(content))
            digest = hashlib.sha256(content.encode('utf-8')).hexdigest()
            if count < 10000:
                state[key] = {'status': 'short', 'words': count}
            elif digest in hashes:
                state[key] = {'status': 'duplicate'}
            else:
                book = {'id': book_id, 'title': row['Title'], 'author': row['Authors'] or 'Unknown',
                        'source': f'https://www.gutenberg.org/ebooks/{book_id}',
                        'download_url': url, 'language': 'en', 'words': count, 'digest': digest}
                # Retain the source text including its original Gutenberg license.
                (books_dir / f'{book_id}.txt').write_text(text, encoding='utf-8', newline='')
                write_json(books_dir / f'{book_id}.json', book)
                hashes.add(digest)
                accepted += 1
                state[key] = {'status': 'accepted', 'words': count}
                print(f'[{accepted}/{target}] {book_id}: {row["Title"][:75]} ({count:,} words)', flush=True)
            failures = 0
        except urllib.error.HTTPError as error:
            if error.code == 403:
                raise ValueError('Mirror refused access. Stop and select another permitted mirror.') from error
            state[key] = {'status': 'missing' if error.code == 404 else 'error', 'error': str(error)}
            failures += error.code != 404
            print(f'Skipped {book_id}: HTTP {error.code}', flush=True)
        except (urllib.error.URLError, TimeoutError, UnicodeError, ValueError) as error:
            state[key] = {'status': 'error', 'error': str(error)}
            failures += 1
            print(f'Could not download {book_id}: {error}', flush=True)
        write_json(state_path, state)
        if failures >= 5:
            raise ValueError('Five consecutive download failures. Check connectivity and rerun to resume.')
        time.sleep(delay)
    print(f'Collection finished: {accepted} valid books.', flush=True)
    return accepted


def index_directory(db, directory):
    from .engine import configure_bulk_import, import_book
    configure_bulk_import(db)
    imported = 0
    term_ids = {word: term_id for term_id, word in db.execute('SELECT id,word FROM terms')}
    paths = sorted(Path(directory).glob('*.json'), key=lambda p: int(p.stem))
    try:
        for i, path in enumerate(paths, 1):
            book = json.loads(path.read_text(encoding='utf-8'))
            if db.execute('SELECT 1 FROM books WHERE id=?', (book['id'],)).fetchone():
                # Word postings are unchanged by newline normalization; migrate
                # old hashes to the canonical content representation.
                with path.with_suffix('.txt').open(encoding='utf-8', newline='') as stream:
                    digest = hashlib.sha256(clean_text(stream.read()).encode('utf-8')).hexdigest()
                db.execute('UPDATE books SET digest=? WHERE id=?', (digest, book['id']))
            else:
                text = path.with_suffix('.txt').read_text(encoding='utf-8')
                if import_book(db, book, text, term_ids=term_ids, commit=False):
                    imported += 1
            if i % 25 == 0 or i == len(paths):
                # Commit a bounded batch, so shared postings pages are written
                # once per batch rather than once for each individual book.
                db.commit()
                print(f'Indexed {i}/{len(paths)} corpus entries.', flush=True)
        db.commit()
    except BaseException:
        db.rollback()
        raise
    return imported
