"""Shared normalization for corpus validation and keyword indexing."""
import re
import unicodedata
from collections import Counter

WORDS = re.compile(r"[^\W\d_]+(?:['’][^\W\d_]+)*", re.UNICODE)
START = re.compile(r"^\*\*\*\s*START OF (?:THE|THIS) PROJECT GUTENBERG.*?\*\*\*", re.I | re.M)
END = re.compile(r"^\*\*\*\s*END OF (?:THE|THIS) PROJECT GUTENBERG.*?\*\*\*", re.I | re.M)


def clean_text(text):
    """Remove Gutenberg's wrapper; keep the original file separately."""
    start = START.search(text)
    if start:
        text = text[start.end():]
    end = END.search(text)
    if end:
        text = text[:end.start()]
    return unicodedata.normalize('NFC', text).strip()


def tokens(text):
    return WORDS.findall(unicodedata.normalize('NFC', text).casefold().replace('’', "'"))


def frequencies(text):
    return Counter(tokens(text))
