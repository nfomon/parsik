"""The Parsik parser and grammar-matching components."""

import logging

from parsik import logutils

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())

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

        from parsik import R
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

        Raises ParseError if the starting_rule is not in the grammar.

        If the input_string uses the CRLF ('\r\n') newline convention, it's
        recommended to combine these into a single linefeed ('\n') character as
        a preprocessing step before providing it here.  Otherwise the
        line-number logging will be off (because it tracks individual
        characters), and anyway this tends to simplify grammars.

        Raises ParseFailure if the parse was unsuccessful.  Otherwise, returns
        the output of the parse; the nature of this output is up to the
        Matchers.

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
        logger.info("Parsing%s {%s} against input string %s.",
                    language, starting_rule, logutils.squish(repr(input_string), 30))
        logger.info("")
        ParseLogger.log_parse_start()
        start_iter = DocumentIterator(input_string)
        try:
            result = self.grammar[starting_rule].match(start_iter)
            if result.success and result.end_iter.end():
                logger.info("Parse success: '%s'.",
                            logutils.squish(logutils.stringify(result.output), 60))
                logger.info("")
                return result.output
        except TerminateParse:
            logger.info("Parse terminated.")
        else:
            logger.info("Parse failed.")
        logger.info("")
        raise ParseFailure()

class ParseError(Exception):
    """Indicates an attempt to use the parser incorrectly."""
    pass

class ParseFailure(Exception):
    """Indicates that the document does not match the grammar."""
    pass

class ParseLogger:
    """Static helpers for logging nicely-formatted parse attempts."""

    @staticmethod
    def log_parse_start():
        """Log headers for the start of a parse."""

        logger.debug("{:<7} {:<10} {:<20}{} {:<15} {}".format(
            'pos', 'input', 'output', '✓|✕', 'rule', 'rule details'))
        logger.debug("{:<7} {:<10} {:<20}{} {:<15} {}".format(
            '-' * 7, '-' * 10, '-' * 19, '-' * 3, '-' * 15, '-' * 25))

    @staticmethod
    def log_match_attempt(matcher, depth, start_iter):
        """Log the start of an attempt to match a Matcher."""

        char = '$' if start_iter.end() else start_iter.peek()
        ParseLogger._log_match_line(matcher, depth, start_iter.pos, start_iter.pos, char, ' ')

    @staticmethod
    def log_match_result(matcher, depth, start_iter, result):
        """Log the result of an attempt to match a Matcher."""

        end_iter = result.end_iter if result.success else start_iter
        pos2 = '$' if end_iter.end() else end_iter.pos
        chars = '$' if start_iter.end() else start_iter.peek()
        if not end_iter.end():
            chars = start_iter.doc[start_iter.pos:end_iter.pos]
        status = '✓' if result.success else '✕'
        output_string = logutils.stringify(result.output) if result.success else ''
        ParseLogger._log_match_line(matcher, depth, start_iter.pos, pos2,
                                    chars, status, output_string)

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
        matcher_name = matcher.name or ''
        logger.debug("{:<7} {:<10} {:<20} {}  {:<15} {}".format(
            positions, chars, output, status, matcher_name, indented_matcher))

class DocumentIterator:
    r"""Document (string) iterator, that tracks line/column position.

    This is just an abstraction for a string and a position index.  You can
    peek the character at the current position, or use end() to check if the
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
        """Returns the character at the current position, or None if past the end."""
        return None if self.end() else self.doc[self.pos]

    def end(self):
        """Returns True if the position has moved past the end of the string."""
        return self.pos >= len(self.doc)

    def __iter__(self):
        return self

    def __next__(self):
        """Advances forward by a single character."""

        if self.end():
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
        return "line {} col {}: '{}'".format(self.line, self.col, self.peek() or '<end>')

class MatchResult:
    """The result of an attempt to match a Matcher."""

    @property
    def success(self):
        """Indicates if the match was successful."""
        return isinstance(self, MatchSuccess)

class MatchFailure(MatchResult):
    """Indicates that a match did not succeed."""
    pass

class MatchSuccess(MatchResult):
    """A successful match; contains the endpoint iterator and match output."""

    def __init__(self, end_iter, output=None):
        self.end_iter = end_iter
        self.output = output

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

        from parsik import R
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
