from parsik import logutils

from copy import copy
import logging
import re

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())

class ParseError(Exception):
    """Indicates an attempt to use the parser incorrectly."""
    pass

class Parser:
    """Parses documents according to a grammar.

    This is a simplistic PEG (parsing expression grammar) parser.  You make a
    Parser for a grammar, which is a dictionary of "rules" (Matchers) that will
    be used to recognize (match) parts of an input document.  Then you can use
    the parse() method to parse documents (strings) against the grammar.
    """

    def __init__(self, grammar, name=''):
        """Construct a parser for the specified grammar.

        The grammar is a dictionary of "rules".  The key is the name of the
        rule, and the value is a Matcher object (or the name of another rule).

        Example:
            grammar = {
                'MAIN': Sequence('FIRST', 'SECOND', 'THIRD'),
                'FIRST': OneOrMore(Char('a')),
                'SECOND': Any(Char('b'), Char('c')),
                'THIRD': 'FIRST',
            }
            p = Parser(grammar, "Quick example")

        The second argument is a name for the grammar (language).  This is
        optional and only used for logging.
        """

        self.grammar = grammar
        self.name = name
        for rule_name, matcher in grammar.items():
            # Treat a string as an alias for another rule in the grammar.
            if isinstance(matcher, str):
                matcher = R(matcher)
                grammar[rule_name] = matcher
        # Initialize the matchers with the full grammar, so that rules can
        # refer to each other.
        for rule_name, matcher in grammar.items():
            matcher.prepare(grammar, rule_name)

    def parse(self, starting_rule, input_string):
        r"""Parse an input string against a specific rule in the grammar.

        The starting_rule must be the name of a rule in the grammar; otherwise
        a ParseError is raised.

        If the input_string uses the CRLF ('\r\n') newline convention, it's
        recommended to combine these into a single linefeed ('\n') character as
        a preprocessing step before providing it here.  Otherwise the
        line-number logging will be off (because it tracks individual
        characters), and anyway this tends to simplify grammars.

        Returns a 2-tuple.  If the parse was not successful (i.e. the input
        string was not completely matched by the starting_rule), then it
        returns (False, None).  If the parse was successful, it returns (True,
        output), where the nature of the "output" is up to the Matchers.

        Each Matcher has a default behaviour for its output. For example, the
        Char and Regex matchers will output strings corresponding to the
        subsequences of the input that they match.  "Aggregate" matchers, such
        as Sequence or OneOrMore, will output a list of the outputs of their
        child matchers.  And so on.

        The output of a Matcher can be customized anywhere in the grammar, by
        providing an on_match callback.  So the output could be any
        user-defined structure and is not limited to the default behaviours.
        """

        if starting_rule not in self.grammar:
            raise ParseError("Starting rule {} is not in the grammar.".format(starting_rule))
        language = ""
        if self.name:
            language = " {}".format(self.name)
        logger.info("Parsing{} {{{}}} against input string {}.".format(language, starting_rule, logutils.squish(repr(input_string), 30)))
        logger.info("")
        ParseLogger.log_parse_start()
        start_iter = DocumentIterator(input_string)
        try:
            result = self.grammar[starting_rule].match(start_iter)
            if result.success and result.end_iter.EOF():
                logger.info("Parse success: '{}'.".format(logutils.squish(logutils.stringify(result.output), 60)))
                logger.info("")
                return True, result.output
        except TerminateParse:
            logger.info("Parse terminated.")
        else:
            logger.info("Parse failed.")
        logger.info("")
        return False, None

class ParseLogger:
    """Static helpers for logging nicely-formatted parse attempts."""

    @staticmethod
    def log_parse_start():
        """Log headers for the start of a parse."""

        logger.debug("{:<7} {:<10} {:<20}{} {:<15} {}".format('pos', 'input', 'output', '✓|✕', 'rule', 'rule details'))
        logger.debug("{:<7} {:<10} {:<20}{} {:<15} {}".format('-------', '----------', '-------------------', '---', '---------------', '-------------------------'))

    @staticmethod
    def log_match_attempt(matcher, depth, start_iter):
        """Log the start of an attempt to match a Matcher."""

        char = '$' if start_iter.EOF() else start_iter.peek()
        ParseLogger._log_match_line(matcher, depth, start_iter.pos, start_iter.pos, char, ' ')

    @staticmethod
    def log_match_result(matcher, depth, start_iter, result):
        """Log the result of an attempt to match a Matcher."""

        end_iter = result.end_iter if result.success else start_iter
        pos2 = '$' if end_iter.EOF() else end_iter.pos
        chars = '$' if start_iter.EOF() else start_iter.peek()
        if not end_iter.EOF():
            chars = start_iter.doc[start_iter.pos:end_iter.pos]
        status = '✓' if result.success else '✕'
        output_string = logutils.stringify(result.output) if result.success else ''
        ParseLogger._log_match_line(matcher, depth, start_iter.pos, pos2, chars, status, output_string)

    @staticmethod
    def _log_match_line(matcher, depth, pos1, pos2, chars, status, output=''):
        """Helper function for logging a match attempt."""

        indented_matcher = "{}{}".format(logutils.indent(depth), matcher)
        positions = str(pos1) if pos1 == pos2 else '{}-{}'.format(pos1, pos2)
        chars = logutils.squish("'{}'".format(chars), 10)
        if output:
            output = logutils.squish("'{}'".format(output), 20)
        else:
            output = ''
        logger.debug("{:<7} {:<10} {:<20} {}  {:<15} {}".format(positions, chars, output, status, matcher.name or '', indented_matcher))

class DocumentIterator:
    r"""Document (string) iterator, that tracks line/column position.

    This is just an abstraction for a string and a position index.  You can
    peek the character at the current position, or use EOF() to check if the
    end of input has been reached.  As the iterator advances forward, the
    line/column position are tracked, which is useful for logging.

    The iterator operates on individual characters.  If the document string
    uses the CRLF ('\r\n') newline convention, it's recommended to replace
    these by a single linefeed character ('\n') as a preprocessing step before
    providing the document to the Parsik parser.  Otherwise the line-tracking
    information will be off, as it will count each newline character.

    The line/column tracking adds some overhead to every parse attempt.  A
    better parsing module might instead do this tracking only when necessary,
    e.g. when a parse has failed and logging is enabled.

    The DocumentIterator implements the Python iterator interface, so you can
    use next(x) to advance the iterator forward, or use the iterator in a loop.
    However the usage throughout this module is to peek at the current
    character and only move next when it has matched.
    """

    def __init__(self, doc):
        self.doc = doc
        self.pos = 0
        self.line = 1
        self.col = 1

    def peek(self):
        """Returns the character at the current position, or None at EOF."""

        return None if self.EOF() else self.doc[self.pos]

    def EOF(self):
        """Returns True if the position has moved past the end of the string."""

        return self.pos >= len(self.doc)

    def __iter__(self):
        return self

    def __next__(self):
        """Advances forward by a single character."""

        if self.EOF():
            raise StopIteration
        c = self.doc[self.pos]
        if c == '\r' or c == '\n' or c == '\x85':
            self.line += 1
            self.col = 1
        else:
            self.col += 1
        self.pos += 1
        return c

    def __str__(self):
        return "line {} col {}: '{}'".format(self.line, self.col, self.peek() or '<EOF>')

class MatchResult:
    """The result of an attempt to match a Matcher.

    The `success` property indicates if the match was successful.
    """

    @property
    def success(self):
        return isinstance(self, MatchSuccess)

class MatchSuccess(MatchResult):
    """A successful match, with the endpoint iterator and match output."""

    def __init__(self, end_iter, output=None):
        self.end_iter = end_iter
        self.output = output

class MatchFailure(MatchResult):
    """Indicates that a match did not succeed."""
    pass

class TerminateParse(Exception):
    """Matchers can raise this to completely terminate a parse attempt."""
    pass

class Matcher:
    """A Matcher defines how to recognize part of the input document.

    This is the base class for all Matchers such as Sequence, Regex, etc.

    A Matcher matches a range of characters along the input string.  It could
    do this directly, or it might be an "aggregate" structure that delegates to
    child matchers.  Either way, a useful Matcher will be a subclass of this
    base, that provides a _match method to perform the matching.

    The _match methods give some default output on a successful match (e.g. the
    characters that were matched).  But users can always provide an on_match
    callback that can transform or replace that default to whatever they want.
    """

    def __init__(self, children=None, on_match=lambda x: x):
        """Construct a Matcher.

        If this is an "aggregate" matcher (such as Sequence or OneOrMore) that
        delegates its work to child matchers, then these are provided in as the
        `children` list.  This is uniform so that the prepare() method can form
        recursive cycles throughout the grammar.

        Each matcher's _match function has some default behaviour for its
        output.  Users can customize this by providing an on_match callback.
        It takes one argument, which is the default output of the matcher, and
        whatever it returns will be used as the output instead.

        Example:  Char('a', on_match=lambda x: 'b')
        The Char matcher normally outputs the character that it matches.
        But here the Char('a') would output a 'b' after a successful match.
        """

        self.name = None
        self.children = children or []
        self.on_match = on_match

    def prepare(self, grammar, name=None):
        """Set up the matcher with the completed grammar.

        This is an initialization step that allows the matcher (and its
        children) to form recursive cycles by looking up rules by name against
        the completed grammar.  Also, since the grammar has a name for some
        rules, we can provide those names to the matchers to help with logging.
        """

        self.name = name
        for i, child in enumerate(self.children):
            if isinstance(child, str):
                child = R(child)
                self.children[i] = child
            child.prepare(grammar)

    def match(self, start_iter, depth=0):
        """Attempt to match at a specific location in the input document.

        This is the base-class "outer" match function, that should not be
        overridden by subclasses.  It is called in the first place by
        Parser.parse(), and by "aggregate" matchers whenever they ask their
        children to attempt a match.

        It does logging of the match attempt (whether it succeeds or not).  And
        if the match is successful, it invokes the user's on_match callback to
        transform the match output.  The actual matching logic is performed by
        a _match method that must be provided by any Matcher implementation
        (subclass).
        """

        ParseLogger.log_match_attempt(self, depth, start_iter)
        result = self._match(start_iter, depth+1)
        ParseLogger.log_match_result(self, depth, start_iter, result)
        if result.success:
            result.output = self.on_match(result.output)
        return result

    def _match(self, start_iter, depth):
        """Try to match a piece of the input document.

        Any useful Matcher should provide an implementation of this method that
        does the matching logic.  start_iter is the DocumentIterator for where
        the match attempt should begin, and must not be modified.

        The depth is the recursion depth and used only for logging.  If this
        matcher wants to attempt a match of any children, it should call
        their match() method (not _match()), and provide this depth unmodified.

        Returns either MatchSuccess or MatchFailure.  MatchSuccess includes an
        iterator for the endpoint of the match, as well as the match output.
        Since the start_iter should be left unmodified, the end_iter should be
        a copy of it that is then advanced (by next()) to include any
        characters that are covered by the match.  Note that a successful match
        might not consume any characters of input (such as an Optional()), in
        which case the end_iter is simply a copy of the start_iter.

        Whatever output is provided by default, the user could override this by
        providing an on_match callback to the Matcher constructor.
        """

        raise NotImplementedError

class Char(Matcher):
    """Matches a single character.

    Example: grammar = { 'A': Char('a') }

    The output is the character that was matched.
    """

    def __init__(self, char, on_match=lambda x: x):
        super().__init__(on_match=on_match)
        self.char = char

    def _match(self, start_iter, depth):
        if start_iter.EOF():
            return MatchFailure()
        c = start_iter.peek()
        if c == self.char:
            end_iter = copy(start_iter)
            next(end_iter)
            return MatchSuccess(end_iter, c)
        return MatchFailure()

    def __str__(self):
        return "'{}'".format(self.char)

class Regex(Matcher):
    """Matches a regular expression, using the standard re module.

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

class EOF(Matcher):
    """Matches the end of input.

    Example: Any(Char('\n'), EOF())
    """

    def __init__(self, on_match=lambda x: x):
        super().__init__(on_match=on_match)

    def _match(self, start_iter, depth):
        if start_iter.EOF():
            return MatchSuccess(start_iter)
        return MatchFailure()

    def __str__(self):
        return 'EOF'

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

    def __init__(self, child, min_times, max_times=None, on_match=lambda x: x, item_filter=lambda x: x is not None):
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
        return "X{{{},{}}}({})".format(self.min_times, '∞' if self.max_times is None else self.max_times, self.children[0])

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

def silent(matcher):
    """Discard the output of a matcher.

    Example: Sequence(Char('a'), silent(Char('b')), Char('c'))
    """

    if isinstance(matcher, str):
        matcher = R(matcher)
    matcher.on_match=lambda x: None
    return matcher

