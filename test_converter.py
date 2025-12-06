import unittest
import sys
import io
from main import Converter

class TestConverter(unittest.TestCase):
    def setUp(self):
        self.conv = Converter()

    def test_empty(self):
        data = "// комментарий\n#| блок |#"
        res = self.conv.parse_content(data)
        self.assertEqual(res, {})

    def test_basic_dict(self):
        data = """
            [
                kint => 123,
                kstr => 'Hello',
                ktrue => true,
                kfalse => false
            ]
        """
        res = self.conv.parse_content(data)
        expected = {
            'kint': 123,
            'kstr': 'Hello',
            'ktrue': True,
            'kfalse': False
        }
        self.assertEqual(res, expected)

    def test_arrays(self):
        data = """
            [
                nums => (list 1 2 3 4),
                strs => (list 'a' 'b' 'c'),
                mixed => (list 1 'two' true)
            ]
        """
        res = self.conv.parse_content(data)
        expected = {
            'nums': [1, 2, 3, 4],
            'strs': ['a', 'b', 'c'],
            'mixed': [1, 'two', True]
        }
        self.assertEqual(res, expected)

    def test_nested(self):
        data = """
            [
                outer => [
                    inner => 'test',
                    nested => [
                        val => 99
                    ]
                ]
            ]
        """
        res = self.conv.parse_content(data)
        expected = {
            'outer': {
                'inner': 'test',
                'nested': {
                    'val': 99
                }
            }
        }
        self.assertEqual(res, expected)

    def test_constants(self):
        data = """
            global port = 80;
            [
                result => ^{port 10 +}
            ]
        """
        res = self.conv.parse_content(data)
        self.assertEqual(res['result'], 90)
        self.assertEqual(self.conv.trans.consts['port'], 80)

    def test_math_ops(self):
        data = """
            global a = 10;
            global b = 5;
            [
                add => ^{a b +},
                sub => ^{a b -},
                mul => ^{a b *},
                div => ^{a b /}
            ]
        """
        res = self.conv.parse_content(data)
        self.assertEqual(res['add'], 15)
        self.assertEqual(res['sub'], 5)
        self.assertEqual(res['mul'], 50)
        self.assertEqual(res['div'], 2.0)

    def test_sqrt(self):
        data = """
            global val = 144;
            [
                root => ^{val sqrt}
            ]
        """
        res = self.conv.parse_content(data)
        self.assertEqual(res['root'], 12.0)

    def test_len(self):
        data = """
            global s = 'abcdefg';
            global arr = (list 1 2 3 4);
            [
                len_s => ^{s len},
                len_arr => ^{arr len}
            ]
        """
        res = self.conv.parse_content(data)
        self.assertEqual(res['len_s'], 7)
        self.assertEqual(res['len_arr'], 4)

    def test_expr(self):
        data = """
            [
                sum => ^{10 20 +},
                concat => ^{'Val ' '1' +}
            ]
        """
        res = self.conv.parse_content(data)
        self.assertEqual(res['sum'], 30)
        self.assertEqual(res['concat'], 'Val 1')

    def test_syntax_error(self):
        data = "[key => 123"
        with self.assertRaisesRegex(ValueError, "Ошибка синтаксиса"):
            self.conv.parse_content(data)

    def test_div_zero(self):
        data = "[res => ^{10 0 /}]"
        with self.assertRaisesRegex(ValueError, "Деление на ноль"):
            self.conv.parse_content(data)

    def test_unknown_const(self):
        data = "[res => ^{unknown 1 +}]"
        with self.assertRaisesRegex(ValueError, "Константа не найдена"):
            self.conv.parse_content(data)

    def test_bad_expr(self):
        data = "[res => ^{1 2 3 +}]"
        with self.assertRaisesRegex(ValueError, "Ошибка в выражении"):
            self.conv.parse_content(data)

if __name__ == '__main__':
    sys.stderr = io.StringIO()
    try:
        unittest.main(exit=False)
    finally:
        sys.stderr = sys.__stderr__