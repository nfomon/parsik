#!/usr/bin/env python3

import logging
import unittest
from parsik import *

#logging.basicConfig(level=logging.DEBUG, format='%(message)s',)

class TestParsik(unittest.TestCase):
    def parse(self, grammar, s):
        return Parser(grammar).parse('A', s)

    def bad(self, grammar, s):
        success, output = self.parse(grammar, s)
        self.assertFalse(success)

    def good(self, grammar, s, expected_output):
        success, output = self.parse(grammar, s)
        self.assertTrue(success)
        self.assertEqual(output, expected_output)

    def test_EOF(self):
        g = {
          'A': EOF(),
        }
        self.good(g, '', None)
        self.bad(g, 'x')
        self.bad(g, 'xx')

    def test_Char(self):
        g = {
          'A': Char('a'),
        }
        self.bad(g, '')
        self.good(g, 'a', 'a')
        self.bad(g, 'A')

        g = {
          'A': Char('aa'),
        }
        self.bad(g, '')
        self.bad(g, 'a')
        self.bad(g, 'aa')

        g = {
          'A': Char(''),
        }
        self.bad(g, '')
        self.bad(g, 'a')
        self.bad(g, 'aa')

        g = {
          'A': Char(None),
        }
        self.bad(g, '')
        self.bad(g, 'a')
        self.bad(g, 'aa')

    def test_Fail(self):
        self.f = False
        def faily(dociter):
            self.f = True
        g = {
          'A': Fail(on_fail=faily),
        }
        self.bad(g, '')
        self.assertTrue(self.f)
        self.f = False
        self.bad(g, 'x')
        self.assertTrue(self.f)

        self.f = False
        g = {
          'A': Any(Char('a'), Fail(on_fail=faily)),
        }
        self.bad(g, '')
        self.assertTrue(self.f)
        self.f = False
        self.bad(g, 'x')
        self.assertTrue(self.f)
        self.f = False
        self.good(g, 'a', 'a')
        self.assertFalse(self.f)

    def test_silent(self):
        g = {
          'A': silent(Char('a')),
        }
        self.bad(g, '')
        self.good(g, 'a', None)
        self.bad(g, 'x')

        g = {
          'A': silent(Sequence(Char('a'), Char('b'), Char('c'))),
        }
        self.bad(g, '')
        self.bad(g, 'a')
        self.bad(g, 'ab')
        self.good(g, 'abc', None)
        self.bad(g, 'abcd')
        self.bad(g, 'x')

    def test_Regex(self):
        g = {
          'A': Regex(r'[1-3]+'),
        }
        self.bad(g, '')
        self.bad(g, '0')
        self.bad(g, 'x')
        self.good(g, '1', '1')
        self.good(g, '2', '2')
        self.good(g, '3', '3')
        self.good(g, '11', '11')
        self.good(g, '31211323', '31211323')
        self.bad(g, '4')
        self.bad(g, '1234')

    def test_Any(self):
        self.f = False
        def faily(dociter):
            self.f = True

        g = {
          'A': Any(Char('a'), Char('b'), Char('c')),
        }
        self.bad(g, '')
        self.good(g, 'a', 'a')
        self.good(g, 'b', 'b')
        self.good(g, 'c', 'c')
        self.bad(g, 'x')
        self.bad(g, 'aa')
        self.bad(g, 'ab')
        self.bad(g, 'ax')
        self.bad(g, 'ba')
        self.bad(g, 'bb')

        g = {
          'A': Any(Char('a'), Char('b'), Sequence(Char('a'), Char('b'))),
        }
        self.bad(g, '')
        self.good(g, 'a', 'a')
        self.good(g, 'b', 'b')
        self.bad(g, 'c')
        self.bad(g, 'x')
        self.bad(g, 'aa')
        self.bad(g, 'ab')
        self.bad(g, 'abc')
        self.bad(g, 'ax')
        self.bad(g, 'ba')
        self.bad(g, 'bb')

        g = {
          'A': Any(Char('a'), Fail(Char('a'), on_fail=faily)),
        }
        self.bad(g, '')
        self.good(g, 'a', 'a')
        self.bad(g, 'b')
        self.bad(g, 'c')
        self.bad(g, 'x')
        self.bad(g, 'aa')
        self.bad(g, 'ab')
        self.assertFalse(self.f)

        g = {
          'A': Any(Char('a'), Fail(Char('a'), on_fail=faily), Char('b')),
        }
        self.bad(g, '')
        self.good(g, 'a', 'a')
        self.good(g, 'b', 'b')
        self.bad(g, 'c')
        self.bad(g, 'x')
        self.bad(g, 'aa')
        self.bad(g, 'ab')
        self.assertFalse(self.f)

        g = {
          'A': Any(Sequence(Char('a'), Char('b')), Sequence(Char('a'), Char('c'))),
        }
        self.bad(g, '')
        self.bad(g, 'a')
        self.bad(g, 'aa')
        self.good(g, 'ab', ['a', 'b'])
        self.bad(g, 'aba')
        self.bad(g, 'abb')
        self.bad(g, 'ba')
        self.bad(g, 'bb')
        self.good(g, 'ac', ['a', 'c'])
        self.bad(g, 'abc')
        self.bad(g, 'acb')

    def test_Sequence(self):
        g = {
          'A': Sequence(Char('a'), Char('b'), Char('c'))
        }
        self.bad(g, '')
        self.bad(g, 'a')
        self.bad(g, 'ab')
        self.bad(g, 'cba')
        self.good(g, 'abc', ['a', 'b', 'c'])
        self.bad(g, 'abcd')
        self.bad(g, 'abcabc')

        g = {
          'A': Sequence(Char('a')),
        }
        self.bad(g, '')
        self.good(g, 'a', ['a'])
        self.bad(g, 'b')
        self.bad(g, 'ab')
        self.bad(g, 'cba')
        self.bad(g, 'abc')
        self.bad(g, 'abcd')

        g = {
          'A': Sequence(Sequence(Char('a'), Char('b'))),
        }
        self.bad(g, '')
        self.bad(g, 'a')
        self.bad(g, 'b')
        self.good(g, 'ab', [['a', 'b']])
        self.bad(g, 'abc')
        self.bad(g, 'cba')
        self.bad(g, 'abcd')

        g = {
          'A': Sequence(ZeroOrMore(Char('a')), Char('a'), Char('b')),
        }
        self.bad(g, '')
        self.bad(g, 'a')
        self.bad(g, 'b')
        self.bad(g, 'ab')
        self.bad(g, 'aab')
        self.bad(g, 'aaab')
        self.bad(g, 'aaaab')
        self.bad(g, 'aaaaab')
        self.bad(g, 'aaabb')

        g = {
          'A': Sequence(ZeroOrMore(Char('a')), Sequence(Char('a'), Char('b'))),
        }
        self.bad(g, '')
        self.bad(g, 'a')
        self.bad(g, 'b')
        self.bad(g, 'ab')
        self.bad(g, 'aab')
        self.bad(g, 'aaab')
        self.bad(g, 'aaaab')
        self.bad(g, 'aaaaab')
        self.bad(g, 'aaabb')

        g = {
          'A': Sequence(Times(Char('a'), 1, 2), Char('a'), Char('b')),
        }
        self.bad(g, '')
        self.bad(g, 'a')
        self.bad(g, 'b')
        self.bad(g, 'ab')
        self.bad(g, 'aab')  # !
        self.good(g, 'aaab', [['a', 'a'], 'a', 'b'])
        self.bad(g, 'aaaab')
        self.bad(g, 'aaaab')
        self.bad(g, 'aaaaab')
        self.bad(g, 'aabb')
        self.bad(g, 'aaabb')

        g = {
          'A': Sequence(ZeroOrMore(Char('a')), Char('b'), ZeroOrMore(Char('c')))
        }
        self.bad(g, '')
        self.bad(g, 'a')
        self.good(g, 'b', [[], 'b', []])
        self.bad(g, 'bb')
        self.good(g, 'ab', [['a'], 'b', []])
        self.good(g, 'aab', [['a']*2, 'b', []])
        self.good(g, 'aaab', [['a']*3, 'b', []])
        self.good(g, 'bc', [[], 'b', ['c']])
        self.good(g, 'bcc', [[], 'b', ['c']*2])
        self.good(g, 'bccc', [[], 'b', ['c']*3])
        self.good(g, 'abc', [['a'], 'b', ['c']])
        self.good(g, 'aabc', [['a']*2, 'b', ['c']])
        self.good(g, 'abcc', [['a'], 'b', ['c']*2])
        self.good(g, 'aabcc', [['a']*2, 'b', ['c']*2])
        self.good(g, 'aaaabccc', [['a']*4, 'b', ['c']*3])
        self.bad(g, 'bd')
        self.bad(g, 'abd')
        self.bad(g, 'bcd')
        self.bad(g, 'abcd')
        self.bad(g, 'aabccd')
        self.bad(g, 'abb')
        self.bad(g, 'bbc')
        self.bad(g, 'abbc')

    def test_Times(self):
        g = {
          'A': Times(Char('a'), 0),
        }
        self.good(g, '', [])
        self.good(g, 'a', ['a'])
        self.good(g, 'aa', ['a'] * 2)
        self.good(g, 'aaa', ['a'] * 3)

        g = {
          'A': Times(Char('a'), 1),
        }
        self.bad(g, '')
        self.good(g, 'a', ['a'])
        self.good(g, 'aa', ['a'] * 2)
        self.good(g, 'aaa', ['a'] * 3)

        g = {
          'A': Times(Char('a'), 2),
        }
        self.bad(g, '')
        self.bad(g, 'a')
        self.good(g, 'aa', ['a'] * 2)
        self.good(g, 'aaa', ['a'] * 3)

        g = {
          'A': Times(Char('a'), 3),
        }
        self.bad(g, '')
        self.bad(g, 'a')
        self.bad(g, 'aa')
        self.good(g, 'aaa', ['a'] * 3)

        g = {
          'A': Times(Char('a'), 0, 0),
        }
        self.good(g, '', [])
        self.bad(g, 'a')
        self.bad(g, 'aa')
        self.bad(g, 'aaa')

        g = {
          'A': Times(Char('a'), 0, 1),
        }
        self.good(g, '', [])
        self.good(g, 'a', ['a'])
        self.bad(g, 'aa')
        self.bad(g, 'aaa')

        g = {
          'A': Times(Char('a'), 0, 2),
        }
        self.good(g, '', [])
        self.good(g, 'a', ['a'])
        self.good(g, 'aa', ['a'] * 2)
        self.bad(g, 'aaa')

        g = {
          'A': Times(Char('a'), 1, 0),
        }
        self.bad(g, '')
        self.bad(g, 'a')
        self.bad(g, 'aa')
        self.bad(g, 'aaa')

        g = {
          'A': Times(Char('a'), 1, 1),
        }
        self.bad(g, '')
        self.good(g, 'a', ['a'])
        self.bad(g, 'aa')
        self.bad(g, 'aaa')

        g = {
          'A': Times(Char('a'), 1, 2),
        }
        self.bad(g, '')
        self.good(g, 'a', ['a'])
        self.good(g, 'aa', ['a'] * 2)
        self.bad(g, 'aaa')

        g = {
          'A': Times(Char('a'), 2, 0),
        }
        self.bad(g, '')
        self.bad(g, 'a')
        self.bad(g, 'aa')
        self.bad(g, 'aaa')

        g = {
          'A': Times(Char('a'), 2, 2),
        }
        self.bad(g, '')
        self.bad(g, 'a')
        self.good(g, 'aa', ['a'] * 2)
        self.bad(g, 'aaa')

        g = {
          'A': Times(Char('a'), 2, 3),
        }
        self.bad(g, '')
        self.bad(g, 'a')
        self.good(g, 'aa', ['a'] * 2)
        self.good(g, 'aaa', ['a'] * 3)

    def test_ZeroOrMore(self):
        g = {
          'A': ZeroOrMore(Char('a')),
        }
        self.good(g, '', [])
        self.good(g, 'a', ['a'])
        self.good(g, 'aa', ['a'] * 2)
        self.good(g, 'aaa', ['a'] * 3)
        self.good(g, 'aaaa', ['a'] * 4)
        self.good(g, 'aaaaa', ['a'] * 5)

    def test_OneOrMore(self):
        g = {
          'A': OneOrMore(Char('a')),
        }
        self.bad(g, '')
        self.good(g, 'a', ['a'])
        self.good(g, 'aa', ['a'] * 2)
        self.good(g, 'aaa', ['a'] * 3)
        self.good(g, 'aaaa', ['a'] * 4)
        self.good(g, 'aaaaa', ['a'] * 5)

    def test_Optional(self):
        g = {
          'A': Optional(Char('a')),
        }
        self.good(g, '', None)
        self.good(g, 'a', 'a')
        self.bad(g, 'x')

        g = {
          'A': Optional(ZeroOrMore(Char('a'))),
        }
        self.good(g, '', [])
        self.good(g, 'a', ['a'])
        self.bad(g, 'x')

        g = {
          'A': Optional(OneOrMore(Char('a'))),
        }
        self.good(g, '', None)
        self.good(g, 'a', ['a'])
        self.bad(g, 'x')

        g = {
          'A': Optional(Times(Char('a'), 2)),
        }
        self.good(g, '', None)
        self.bad(g, 'a')
        self.good(g, 'aa', ['a']*2)
        self.good(g, 'aaa', ['a']*3)
        self.good(g, 'aaaa', ['a']*4)
        self.bad(g, 'b')
        self.bad(g, 'ab')
        self.bad(g, 'aab')
        self.bad(g, 'aaab')

        g = {
          'A': Optional(Times(Char('a'), 3)),
        }
        self.good(g, '', None)
        self.bad(g, 'a')
        self.bad(g, 'aa')
        self.good(g, 'aaa', ['a']*3)
        self.good(g, 'aaaa', ['a']*4)
        self.bad(g, 'b')
        self.bad(g, 'ab')
        self.bad(g, 'aab')
        self.bad(g, 'aaab')

    def test_R(self):
        g = {
          'A': R('B'),
          'B': Char('b'),
        }
        self.bad(g, '')
        self.bad(g, 'a')
        self.good(g, 'b', 'b')
        self.bad(g, 'x')

    def test_R_str(self):
        g = {
          'A': 'B',
          'B': Char('b'),
        }
        self.bad(g, '')
        self.bad(g, 'a')
        self.good(g, 'b', 'b')
        self.bad(g, 'x')

    def test_phonenum(self):
        # A grammar for 7- or 10-digit phone numbers.
        grammar = {
            'PHONENUM': Sequence(
                            Optional(R('AREACODE')),
                            R('THREE'), silent(Char('-')), R('FOUR')
                        ),
            'AREACODE': Sequence(
                            silent(Char('(')), 'THREE', silent(Regex(r'\) ')),
                            on_match=lambda x: x[0]
                        ),
            'THREE':    Regex(r'\d{3}'),
            'FOUR':     Regex(r'\d{4}'),
        }
        parser = Parser(grammar, "Phone numbers")

        success, output = parser.parse("PHONENUM", "123-4567")
        assert success
        assert output == ['123', '4567']

        success, output = parser.parse("PHONENUM", "(555) 123-4567")
        assert success
        assert output == ['555', '123', '4567']

        success, output = parser.parse("PHONENUM", "123-456")
        assert not success
        assert output is None

        success, output = parser.parse("PHONENUM", "123-45678")
        assert not success
        assert output is None

    def test_phonenum_str(self):
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
            'THREE':    Regex(r'\d{3}'),
            'FOUR':     Regex(r'\d{4}'),
        }
        parser = Parser(grammar, "Phone numbers")

        success, output = parser.parse("PHONENUM", "123-4567")
        assert success
        assert output == ['123', '4567']

        success, output = parser.parse("PHONENUM", "(555) 123-4567")
        assert success
        assert output == ['555', '123', '4567']

        success, output = parser.parse("PHONENUM", "123-456")
        assert not success
        assert output is None

        success, output = parser.parse("PHONENUM", "123-45678")
        assert not success
        assert output is None

    def test_quick_example(self):
        grammar = {
            'MAIN': Sequence('FIRST', 'SECOND', 'THIRD'),
            'FIRST': OneOrMore(Char('a')),
            'SECOND': Any(Char('b'), Char('c')),
            'THIRD': 'FIRST',
        }
        p = Parser(grammar, "Quick example")

        success, output = p.parse("MAIN", "abaa")
        assert success
        assert output == [['a'], 'b', ['a', 'a']]

    def test_quick_example_2(self):
        grammar = {
            'MAIN': Sequence('FIRST', 'SECOND', 'THIRD'),
            'FIRST': ZeroOrMore(Regex(r'ab')),
            'SECOND': Any(Char('x'), Char('y')),
            'THIRD': 'FIRST',
        }
        p = Parser(grammar, "Quick example")

        success, output = p.parse("MAIN", "ababy")
        assert success
        assert output == [['ab', 'ab'], 'y', []]

if __name__ == '__main__':
    unittest.main()

