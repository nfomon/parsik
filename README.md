# Parsik

A simplistic PEG (parsing expression grammar) parser.

You provide a grammar for your language, and this module gives you a Parser
that you can use to recognize if documents (strings) match the grammar.  You
can attach callback functions for when various parts of the grammar match, and
to help construct some "output" of the parse (e.g. a parse tree).

The library is simple and unoptimized in time and space.  And a grammar with
left-recursion could put the parser into an infinite-loop.  But the
implementation is small and straightforward, and there is extensive logging to
help analyze the parser's behaviour.

If you're looking for something even slightly more complex or elegant, I
recommend parsy (https://github.com/python-parsy/parsy).


## Example

```python
from parsik import *

# A grammar for 7- or 10-digit phone numbers.
grammar = {
    'PHONENUM': Sequence(
                    Optional('AREACODE'),
                    'THREE', silent(Char('-')), 'FOUR'
                ),
    'AREACODE': Sequence(
                    silent(Char('(')), 'THREE', silent(Regex(r'\) ')),
                    on_match=lambda x: x[0]
                ),
    'THREE':    Regex(r'\d{3}'),    # three digits
    'FOUR':     Regex(r'\d{4}'),    # four digits
}
parser = Parser(grammar, "Phone numbers")

success, output = parser.parse("PHONENUM", "123-4567")
assert success
assert output == [ '123', '4567']

success, output = parser.parse("PHONENUM", "(555) 123-4567")
assert success
assert output == [ '555', '123', '4567']

success, output = parser.parse("PHONENUM", "123-456")
assert not success
assert output is None
```


## Matchers

Parsik comes with several "Matchers" that you can use to express your grammar:
components like Sequence, Optional, ZeroOrMore, Regex, etc.  These Matchers can
be composed and can refer to other rules in the grammar; even recursively, so
long as they aren't "left-recursive" which could cause an infinite-loop.

The included Matchers are:
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

You can also make your own types of Matchers.

There isn't any special syntax or operator-overloading for expressing the
grammar.  It's just a dictionary where the keys are rule-names, and the values
are Matchers.  Some Matchers, like Sequence, are composed of other matchers or
rules.  They just take the list of child matchers in their constructor.  You
can also refer to other grammar rules by name, even if it forms a cycle.


## Logging

Parsik uses python's standard logging.  If you enable it at DEBUG level:

```
logging.basicConfig(level=logging.DEBUG, format='%(message)s',)
```

then you'll get an elaborate analysis of any parse attempt.  For example:

```python
grammar = {
    'MAIN': Sequence('FIRST', 'SECOND', 'THIRD'),
    'FIRST': ZeroOrMore(Regex(r'ab')),
    'SECOND': Any(Char('x'), Char('y')),
    'THIRD': 'FIRST',
}
p = Parser(grammar, "Quick example")
success, output = p.parse("MAIN", "ababy")
```

This will log:

```
Parsing Quick example {MAIN} against input string 'ababy'.

pos     input      output              ✓|✕ rule            rule details
------- ---------- ------------------- --- --------------- -------------------------
0       'a'                                MAIN            [[{FIRST},{SECOND},{THIRD}]]
0       'a'                                                  {FIRST}
0       'a'                                FIRST               *(r'ab')
0       'a'                                                      r'ab'
0-2     'ab'       'ab'                 ✓                        r'ab'
2       'a'                                                      r'ab'
2-4     'ab'       'ab'                 ✓                        r'ab'
4       'y'                                                      r'ab'
4       ''                              ✕                        r'ab'
0-4     'abab'     '[ab, ab]'           ✓  FIRST               *(r'ab')
0-4     'abab'     '[ab, ab]'           ✓                    {FIRST}
4       'y'                                                  {SECOND}
4       'y'                                SECOND              any(['x', 'y'])
4       'y'                                                      'x'
4       ''                              ✕                        'x'
4       'y'                                                      'y'
4-$     'y'        'y'                  ✓                        'y'
4-$     'y'        'y'                  ✓  SECOND              any(['x', 'y'])
4-$     'y'        'y'                  ✓                    {SECOND}
5       '$'                                                  {THIRD}
5       '$'                                THIRD               {FIRST}
5       '$'                                FIRST                 *(r'ab')
5       '$'                                                        r'ab'
5-$     '$'                             ✕                          r'ab'
5-$     '$'        '[]'                 ✓  FIRST                 *(r'ab')
5-$     '$'        '[]'                 ✓  THIRD               {FIRST}
5-$     '$'        '[]'                 ✓                    {THIRD}
0-$     'a'        '[[ab, ab], y, []]'  ✓  MAIN            [[{FIRST},{SECOND},{THIRD}]]
Parse success: '[[ab, ab], y, []]'.
```

Each row shows a step in the recursive-descent parse attempt.  A Matcher will
log a line immediately before and immediately after it attempts to match.  So,
one line where the ✓|✕ column is blank, and another where it has the result.

The columns are:
- pos: The position(s) (character #s) in the input document under view.
  - `$` means EOF.
- input: The text of the input document at those positions.
- output: If a matcher was successful, this is its output.
- ✓|✕:
  - blank means that the matcher is going to attempt a match.
  - ✓ means that the match was successful.
  - ✕ means that the match failed.
- rule: The name of the rule, if the matcher is a named rule in the grammar.
- rule details: A concise representation of what the matcher will attempt to
  recognize.  They display as:
  - Char: ``'x'``
  - Regex: ``r'pattern'``
  - EOF: ``EOF``
  - R: ``{rule name}``
  - Optional: ``?(...)``
  - Any: ``any(...)``
  - Sequence: ``[...]``
  - Times: ``X{min,max}(...)``
  - ZeroOrMore: ``*(...)``
  - OneOrMore: ``+(...)``
  - Fail: ``Fail(...)``
 

## License

This package is licensed under the GNU GPL v3.

