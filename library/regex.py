"""Thompson epsilon-NFA compiler and whole-word matcher.

Supported grammar: literals, ., (), |, *, +, ?, character classes/ranges,
and escaped literals. No backreferences or backtracking. O(m*n) matching
for expression size m and word length n. See docs/algorithms.md.
"""
from dataclasses import dataclass


@dataclass
class State:
    kind: str
    value: object = None
    out: int | None = None
    other: int | None = None


class Regex:
    def __init__(self, pattern):
        if not pattern or len(pattern) > 128:
            raise ValueError('Use an expression between 1 and 128 characters.')
        self.pattern = pattern
        self.pos = 0
        self.states = []
        self.start, pending = self.expression()
        if self.pos != len(pattern):
            raise ValueError(f'Unexpected character at position {self.pos + 1}.')
        end = self.add('match')
        self.patch(pending, end)
        self.initial = self.closure({self.start})

    def add(self, kind, value=None, out=None, other=None):
        self.states.append(State(kind, value, out, other))
        return len(self.states) - 1

    def patch(self, pending, target):
        for index, field in pending:
            setattr(self.states[index], field, target)

    def peek(self):
        return self.pattern[self.pos:self.pos + 1]

    def expression(self):
        start, pending = self.sequence()
        while self.peek() == '|':
            self.pos += 1
            right, right_pending = self.sequence()
            start = self.add('split', out=start, other=right)
            pending += right_pending
        return start, pending

    def sequence(self):
        first = None
        pending = []
        while self.peek() and self.peek() not in ')|':
            start, tails = self.repeated()
            if first is None:
                first = start
            else:
                self.patch(pending, start)
            pending = tails
        if first is None:
            first = self.add('split')
            pending = [(first, 'out')]
        return first, pending

    def repeated(self):
        start, pending = self.atom()
        op = self.peek()
        if op and op in '*+?':
            self.pos += 1
            split = self.add('split', out=start)
            if op in '*+':
                self.patch(pending, split)
                pending = [(split, 'other')]
                if op == '*':
                    start = split
            else:
                start = split
                pending += [(split, 'other')]
            if self.peek() and self.peek() in '*+?':
                raise ValueError('Repeated quantifiers are not supported.')
        return start, pending

    def literal(self):
        char = self.peek()
        if not char:
            raise ValueError('Incomplete escape or character class.')
        self.pos += 1
        if char == '\\':
            char = self.peek()
            if not char:
                raise ValueError('Incomplete escape.')
            self.pos += 1
            if char.isalnum():
                raise ValueError('Use explicit characters/classes; shorthand escapes are not supported.')
        return char

    def atom(self):
        char = self.peek()
        if char == '(':
            self.pos += 1
            fragment = self.expression()
            if self.peek() != ')':
                raise ValueError('Missing closing parenthesis.')
            self.pos += 1
            return fragment
        if char == '[':
            self.pos += 1
            negate = self.peek() == '^'
            if negate:
                self.pos += 1
            chars = set()
            while self.peek() and self.peek() != ']':
                lo = self.literal()
                if self.peek() == '-' and self.pattern[self.pos + 1:self.pos + 2] not in ('', ']'):
                    self.pos += 1
                    hi = self.literal()
                    if ord(hi) < ord(lo) or ord(hi) - ord(lo) > 512:
                        raise ValueError('Invalid or excessively large character range.')
                    chars.update(chr(x) for x in range(ord(lo), ord(hi) + 1))
                else:
                    chars.add(lo)
            if self.peek() != ']' or not chars:
                raise ValueError('Unclosed or empty character class.')
            self.pos += 1
            start = self.add('class', (frozenset(chars), negate))
        elif char == '.':
            self.pos += 1
            start = self.add('any')
        elif char in '*+?^${}':
            raise ValueError(f'Unsupported or misplaced operator: {char}. Patterns match whole indexed words.')
        else:
            start = self.add('char', self.literal())
        return start, [(start, 'out')]

    def closure(self, seeds):
        seen, active = set(), set()
        stack = list(seeds)
        while stack:
            index = stack.pop()
            if index is None or index in seen:
                continue
            seen.add(index)
            state = self.states[index]
            if state.kind == 'split':
                stack.extend((state.out, state.other))
            else:
                active.add(index)
        return frozenset(active)

    def fullmatch(self, word):
        active = self.initial
        for char in word:
            targets = set()
            for index in active:
                state = self.states[index]
                matches = (state.kind == 'any' or
                           state.kind == 'char' and state.value == char or
                           state.kind == 'class' and ((char in state.value[0]) != state.value[1]))
                if matches:
                    targets.add(state.out)
            active = self.closure(targets)
            if not active:
                return False
        return any(self.states[i].kind == 'match' for i in active)
