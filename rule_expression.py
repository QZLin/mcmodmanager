import dataclasses
import re
from typing import *

token_word = re.compile(r'\$?[A-z|0-9_]+?(?=[()+\-\s])|\$?[A-z|0-9_]+?$')
token_symbol = re.compile(r'[()+\-]')


@dataclasses.dataclass
class Token:
    content: str
    span: Tuple[int, int]
    type: Literal['operator', 'name']

    level: int = 0


def to_ast(text: str) -> List[Token]:
    words = (Token(x.group(), x.span(), 'name')
             for x in re.finditer(token_word, text))
    symbols = (Token(x.group(), x.span(), 'operator')
               for x in re.finditer(token_symbol, text))
    tokens = []
    tokens.extend(words)
    tokens.extend(symbols)
    tokens.sort(key=lambda x: x.span[0])
    # print(tokens)

    c_level = 0
    for x in tokens:
        reduce_level = False
        if x.type == 'operator':
            if x.content == '(':
                c_level += 1
                reduce_level = True
            elif x.content == ')':
                c_level -= 1
        # elif x.type == 'name':
        #     if x.content.startswith('$'):
        #         pass
        if c_level < 0:
            raise RuntimeError(f'bracket miss matched {x}')
        x.level = c_level - 1 if reduce_level else c_level

    return tokens


def operate(symbol: Literal['+', '-'], data: List[Any], value: List[Any]) -> List[Any]:
    if symbol == '+':
        data.extend(x for x in value if x not in data)
    elif symbol == '-':
        data = [x for x in data if x not in value]
    else:
        raise NotImplementedError()
    return data


def execute(tokens: List[Token], rules: Dict[str, List[Any]]) -> List[Any]:
    result = []
    last_operator = None
    # for i, x in enumerate(tokens):
    index = 0
    while True:
        token = tokens[index]
        value = None
        if token.type == 'name':
            value = rules[token.content]
        if token.type == 'operator':
            if token.content == '(':
                next_bracket = index
                while True:
                    next_bracket += 1
                    if next_bracket >= len(tokens):
                        raise RuntimeError(f'bracket miss matched {token}')
                    test_token = tokens[next_bracket]
                    if test_token.level == token.level and test_token.content == ')':
                        break
                value = execute(tokens[index+1: next_bracket], rules)
                index += next_bracket
            elif token.content == ')':
                raise RuntimeError()
            else:
                last_operator = token.content
        if last_operator is not None and value is not None:
            result = operate(last_operator, result, value)
        elif value is not None:
            result = value
        index += 1
        if index >= len(tokens):
            break
    return result


def debug_tokens(tokens: List[Token]) -> str:
    return '\n'.join(['    ' * x.level + x.content for x in tokens])


test = '((a+b-c)+$test-a1)+b_1'
ast = to_ast(test)
print(debug_tokens(ast))

rules1 = {'a': [1, 2, 3], 'a1': [4, 5, 6], 'b': [1, 3, 9], 'b_1': [2, 4, 6], 'c': [2],
          '$test': [1, 2, 3, 4, 5, 6, 7, 8, 9]}
r = execute(ast, rules1)
print(r)
