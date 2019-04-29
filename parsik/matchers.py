"""Ready-to-use grammar components (matchers) for Parsik parsers."""

from copy import copy
import re

from parsik import logutils
from parsik.parser import Matcher, MatchFailure, MatchSuccess, TerminateParse

class Any(Matcher):
    """Matches any one of a number of possible items.  The first to match wins.

    Example: Any(Char('a'), Char('ab'), Char('b'))
    - In this example, the Char('ab') would never match.

    Outputs the output of the child that matches.
    """

    def __init__(self, *children, on_match=lambda x: x):
        super().__init__(children=list(children), on_match=on_match)

    def _match(self, start_iter, depth):
        """Greedily match the first child that matches."""
        for child in self.children:
            result = child.match(start_iter, depth)
            if result.success:
                return result
        return MatchFailure()

    def __str__(self):
        return "any({})".format(logutils.stringify(self.children))

class Char(Matcher):
    """Matches a single character.

    Example: grammar = { 'A': Char('a') }

    The output is the character that was matched.
    """

    def __init__(self, char, on_match=lambda x: x):
        super().__init__(on_match=on_match)
        self.char = char

    def _match(self, start_iter, depth):
        if start_iter.end():
            return MatchFailure()
        c = start_iter.peek()
        if c == self.char:
            end_iter = copy(start_iter)
            next(end_iter)
            return MatchSuccess(end_iter, c)
        return MatchFailure()

    def __str__(self):
        return "'{}'".format(self.char)

class EOF(Matcher):
    r"""Matches the end of input.

    Example: Any(Char('\n'), EOF())
    """

    def __init__(self, on_match=lambda x: x):
        super().__init__(on_match=on_match)

    def _match(self, start_iter, depth):
        if start_iter.end():
            return MatchSuccess(start_iter)
        return MatchFailure()

    def __str__(self):
        return 'EOF'

class Fail(Matcher):
    """If it matches, calls a callback and terminates the parse.

    Example: Sequence(Char('a'), Fail(Char('b'), on_fail=bad_b_happened))

    This is useful to abort a parse early when a particular failure can be
    detected, and to help provide specific and useful error messages.

    You can even use the Fail with no children, indicating that the parse
    attempt should terminate unconditionally if it reaches that point in the
    grammar.  Example:  Sequence(Char('a'), Char('b'), Fail())
    """

    def __init__(self, child=None, on_fail=None):
        super().__init__(children=[child] if child else None, on_match=None)
        self.on_fail = on_fail

    def _match(self, start_iter, depth):
        fail = True
        if len(self.children) > 0:
            result = self.children[0].match(start_iter, depth)
            fail = result.success
        if fail:
            if self.on_fail:
                self.on_fail(start_iter)
            raise TerminateParse()
        return MatchFailure()

    def __str__(self):
        if len(self.children) > 0:
            return 'Fail({})'.format(self.children[0])
        return 'Fail'

class Optional(Matcher):
    """Optionally matches an item.

    Example: Optional(Char('a'))

    Outputs the output of the item if it matches, or None otherwise.
    """

    def __init__(self, child, on_match=lambda x: x):
        super().__init__(children=[child], on_match=on_match)

    def _match(self, start_iter, depth):
        result = self.children[0].match(start_iter, depth)
        if result.success:
            return result
        return MatchSuccess(start_iter)

    def __str__(self):
        return "?({})".format(self.children[0])

class R(Matcher):
    """Matches a rule by name that is defined elsewhere in the grammar.

    Example: grammar = {
        'TOP': Sequence(R('A'), R('B')),
        'A': ZeroOrMore(Char('a')),
        'B': OneOrMore(Char('b')),
    }

    Generally you can just name the grammar rule as a string directly, without
    needing to invoke R() explicitly.  For example:
        'TOP': Sequence('A', 'B'),

    Behind the scenes, that will use an R matcher anyway.  But if you want to
    override the on_match function, then you will need to use the R() form.
    """

    def __init__(self, rule_name, on_match=lambda x: x):
        super().__init__(on_match=on_match)
        self.rule_name = rule_name

    def prepare(self, grammar, name=None):
        self.name = name
        self.children = [grammar[self.rule_name]]

    def _match(self, start_iter, depth):
        return self.children[0].match(start_iter, depth)

    def __str__(self):
        return "{{{}}}".format(self.rule_name)

class Regex(Matcher):
    r"""Matches a regular expression, using the standard re module.

    Example: Regex(r'[^abc]+\d{3,7}')

    By default, the re flag re.DOTALL is provided.  You can override this with
    the flags parameter.

    Outputs the input substring that was matched by the regular expression.
    """

    def __init__(self, pattern, flags=re.DOTALL, on_match=lambda x: x):
        super().__init__(on_match=on_match)
        self.pattern = re.compile(pattern, flags)

    def _match(self, start_iter, depth):
        match = self.pattern.match(start_iter.doc, start_iter.pos)
        if match:
            end_iter = start_iter
            if match.end() > start_iter.pos:
                end_iter = copy(start_iter)
                for i in range(0, match.end() - start_iter.pos):
                    next(end_iter)
            return MatchSuccess(end_iter, match.group())
        return MatchFailure()

    def __str__(self):
        return "r'{}'".format(self.pattern.pattern)

class Sequence(Matcher):
    """Matches a sequence of items in the specified order.

    Example: Sequence(Char('a'), Char('b'), Char('c'))

    The output is the list of outputs of the children, except any Nones are
    discarded.  You can change that by providing a different item_filter.
    """

    def __init__(self, *children, on_match=lambda x: x, item_filter=lambda x: x is not None):
        super().__init__(children=list(children), on_match=on_match)
        self.item_filter = item_filter

    def _match(self, start_iter, depth):
        result = MatchSuccess(start_iter, [])
        for child in self.children:
            child_result = child.match(result.end_iter, depth)
            if not child_result.success:
                return child_result
            result.end_iter = child_result.end_iter
            if self.item_filter(child_result.output):
                result.output.append(child_result.output)
        return result

    def __str__(self):
        return "[{}]".format(logutils.stringify(self.children, sep=0))

class Times(Matcher):
    """Matches an item between a min and (optional) max number of times.

    Example: Times(Char('a'), min_times=3, max_times=7)

    If max_times is None, then it will match any number of times >= the minimum.
    Each match must advance the document iterator forward, otherwise the matching
    will stop.

    The output is the list of outputs of the children, except any Nones are
    discarded.  You can change that by providing a different item_filter.
    """

    def __init__(self, child, min_times, max_times=None,
                 on_match=lambda x: x, item_filter=lambda x: x is not None):
        super().__init__(children=[child], on_match=on_match)
        self.min_times = min_times
        self.max_times = max_times
        self.item_filter = item_filter

    def _match(self, start_iter, depth):
        time = 0
        result = MatchSuccess(start_iter, [])
        while self.max_times is None or time < self.max_times:
            child_result = self.children[0].match(result.end_iter, depth)
            if not child_result.success or child_result.end_iter.pos == result.end_iter.pos:
                break
            result.end_iter = child_result.end_iter
            if self.item_filter(child_result.output):
                result.output.append(child_result.output)
            time += 1
        if time >= self.min_times:
            return result
        return MatchFailure()

    def __str__(self):
        max_ = '∞' if self.max_times is None else self.max_times
        return "X{{{},{}}}({})".format(self.min_times, max_, self.children[0])

class ZeroOrMore(Times):
    """Matches an item zero or more times.

    Example: ZeroOrMore(Char('a'))

    This is the same as Times(child, min_times=0)
    """

    def __init__(self, child, on_match=lambda x: x):
        super().__init__(child, min_times=0, on_match=on_match)

    def __str__(self):
        return "*({})".format(self.children[0])

class OneOrMore(Times):
    """Matches an item one or more times.

    Example: OneOrMore(Char('a'))

    This is the same as Times(child, min_times=1)
    """

    def __init__(self, child, on_match=lambda x: x):
        super().__init__(child, min_times=1, on_match=on_match)

    def __str__(self):
        return "+({})".format(self.children[0])

def silent(matcher):
    """Discard the output of a matcher.

    Example: Sequence(Char('a'), silent(Char('b')), Char('c'))
    """

    if isinstance(matcher, str):
        matcher = R(matcher)
    matcher.on_match = lambda x: None
    return matcher
