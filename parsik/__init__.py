"""A simplistic PEG (parsing expression grammar) parser.

You provide a grammar for your language, and you get a Parser that can
recognize if documents (strings) match the grammar.  You can attach callback
functions for when various parts of the grammar match or fail to match, and to
help construct the "output" of a successful parse.

Set the logging level to DEBUG for a step-by-step analysis of a parse attempt.

Public classes:
- Parser: Parses documents against a specified grammar.
  - raises ParseError on incorrect usage.

- Matchers: components of a grammar, that specify how to recognize documents.
  - Char:       matches a single character.
  - Regex:      matches a regular expression.
  - EOF:        matches the end of the input string.
  - R:          matches a rule that is defined elsewhere in the grammar.
    - but usually you can just use a string to refer to a rule by name.
  - Optional:   optionally matches an item.
  - Any:        matches any one of a number of possible items.
  - Sequence:   matches a sequence of items in a specific order.
  - Times:      matches an item a specific number of times, or range of times.
  - ZeroOrMore: matches an item zero or more times.
  - OneOrMore:  matches an item one or more times.
  - Fail:       if an item matches, then abort the parse.

Public functions:
- silent: a convenience to wrap a Matcher to make it provide no output.

For writing your own Matchers, refer to the following classes from parsik.parsik:
- Matcher: base class for all Matchers; subclass this and add a _match method.
- MatchResult: indicates the status of a match attempt.
  - MatchSuccess
  - MatchFailure
- DocumentIterator: iterator for the input string.
"""

import logging

from parsik.parsik import Parser, ParseError, Char, Regex, EOF, R, Optional, Any,\
                          Sequence, Times, ZeroOrMore, OneOrMore, Fail, silent

__version__ = '0.9.1'

