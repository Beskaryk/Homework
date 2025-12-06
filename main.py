#!/usr/bin/env python3

import sys
import argparse
import yaml
from pathlib import Path
from lark import Lark, Transformer, Token
from lark.exceptions import LarkError
import math
import re

grammar = r"""
    start: (const_decl | dict)*
    
    const_decl: "global" NAME "=" value ";"
    
    const_expr: "^" "{" expr_items "}"
    expr_items: (simple_value | NAME | OPERATION)*
    
    dict: "[" dict_items "]"
    dict_items: (dict_item ("," dict_item)*)?
    dict_item: NAME "=>" value
    
    array: "(" "list" array_items ")"
    array_items: array_value*
    
    array_value: NUMBER | ESCAPED_STRING | BOOL
    
    value: simple_value | array | dict | const_expr | NAME
    
    simple_value: NUMBER | STRING | BOOL
    
    NAME: /[a-zA-Z]+/
    NUMBER: /[0-9]+/
    STRING: /'[^']*'/
    ESCAPED_STRING: /'[^']*'/
    BOOL: "true" | "false"
    OPERATION: "+" | "-" | "*" | "/" | "sqrt" | "len"
    
    SINGLE_COMMENT: "//" /[^\n]*/
    
    %import common.WS
    %ignore WS
    %ignore SINGLE_COMMENT
"""

class MyTransformer(Transformer):
    def __init__(self):
        super().__init__()
        self.consts = {}
    
    def start(self, items):
        res = {}
        for i in items:
            if isinstance(i, dict) and i:
                res.update(i)
        return res
    
    def dict(self, items):
        if items and items[0] is not None:
            return items[0]
        return {}
    
    def dict_items(self, items):
        res = {}
        for i in items:
            if i and isinstance(i, tuple) and len(i) == 2:
                k, v = i
                res[k] = v
        return res
    
    def dict_item(self, items):
        if len(items) >= 2:
            return (str(items[0]), items[1])
        return None
    
    def array(self, items):
        lst = []
        for i in items:
            if isinstance(i, list):
                lst = i
                break
        return lst
    
    def array_items(self, items):
        return list(items)
    
    def array_value(self, items):
        return items[0] if items else None
    
    def const_decl(self, items):
        if len(items) >= 2:
            name = str(items[0])
            val = items[1]
            self.consts[name] = val
        return {}
    
    def const_expr(self, items):
        if items and items[0] is not None:
            return self._calc(items[0])
        return None
    
    def expr_items(self, items):
        return [i for i in items if i is not None]
    
    def _calc(self, items):
        stack = []
        for i in items:
            if isinstance(i, Token) and i.type == 'NAME':
                n = str(i)
                if n in self.consts:
                    stack.append(self.consts[n])
                elif n in ['sqrt', 'len']:
                    self._apply_op(n, stack)
                else:
                    raise ValueError(f"Константа не найдена: {n}")
            
            elif isinstance(i, Token) and i.type == 'OPERATION':
                self._apply_op(str(i), stack)
            
            else:
                stack.append(i)
        
        if len(stack) != 1:
            raise ValueError(f"Ошибка в выражении: {stack}")
        return stack[0]
    
    def _apply_op(self, op, stack):
        if op in ('+', '-', '*', '/'):
            if len(stack) < 2:
                raise ValueError(f"Мало аргументов для {op}")
            b = stack.pop()
            a = stack.pop()
            
            if op == '+':
                if isinstance(a, str) or isinstance(b, str):
                    stack.append(str(a) + str(b))
                else:
                    stack.append(a + b)
            elif op == '-':
                stack.append(a - b)
            elif op == '*':
                if isinstance(a, str) and isinstance(b, int):
                    stack.append(a * b)
                elif isinstance(a, int) and isinstance(b, str):
                    stack.append(b * a)
                else:
                    stack.append(a * b)
            elif op == '/':
                if b == 0:
                    raise ValueError("Деление на ноль")
                stack.append(a / b)
        
        elif op == 'sqrt':
            if not stack:
                raise ValueError("Мало аргументов для sqrt")
            a = stack.pop()
            if a < 0:
                raise ValueError("Корень из отрицательного")
            stack.append(math.sqrt(a))
        
        elif op == 'len':
            if not stack:
                raise ValueError("Мало аргументов для len")
            a = stack.pop()
            if isinstance(a, (list, dict, str)):
                stack.append(len(a))
            else:
                raise ValueError(f"len нельзя применить к {type(a).__name__}")
    
    def value(self, items):
        if not items:
            return None
            
        i = items[0]
        
        if isinstance(i, Token) and i.type == 'NAME':
            n = str(i)
            
            if n in self.consts:
                return self.consts[n]
            
            if n in ('true', 'false'):
                return self.BOOL(i)
            
            raise ValueError(f"Неизвестная константа {n}")

        return i
    
    def simple_value(self, items):
        return items[0] if items else None
    
    def NAME(self, token):
        return Token('NAME', str(token))
    
    def NUMBER(self, token):
        return int(token)
    
    def STRING(self, token):
        return str(token)[1:-1]
    
    def ESCAPED_STRING(self, token):
        return str(token)[1:-1]
    
    def BOOL(self, token):
        return str(token) == 'true'
    
    def OPERATION(self, token):
        return Token('OPERATION', str(token))

class Converter:
    def __init__(self):
        self.trans = MyTransformer()
        self.parser = Lark(grammar, parser='lalr', transformer=self.trans)
    
    def parse_file(self, path):
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = f.read()
            return self.parse_content(data)
        except FileNotFoundError:
            raise ValueError(f"Нет файла: {path}")
        except IOError as e:
            raise ValueError(f"Ошибка чтения: {e}")
    
    def parse_content(self, text):
        text = re.sub(r'#\|.*?\|#', '', text, flags=re.DOTALL)
        try:
            res = self.parser.parse(text)
            return res if res is not None else {}
        except LarkError as e:
            raise ValueError(f"Ошибка синтаксиса: {e}")
        except ValueError as e:
            raise ValueError(f"Ошибка вычисления: {e}")
    
    def to_yaml(self, cfg):
        return yaml.dump(cfg, allow_unicode=True, default_flow_style=False, sort_keys=False)

def main():
    parser = argparse.ArgumentParser(description='Конвертер конфигов в YAML')
    parser.add_argument('-i', '--input', type=str, required=True, help='Входной файл')
    args = parser.parse_args()
    
    try:
        conv = Converter()
        cfg = conv.parse_file(Path(args.input))
        print(conv.to_yaml(cfg))
        return 0
    except Exception as e:
        print(f"Ошибка: {e}", file=sys.stderr)
        return 1

if __name__ == "__main__":
    sys.exit(main())