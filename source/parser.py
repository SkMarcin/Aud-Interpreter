from tokens import Token, TokenType
from lexer import Lexer

class Parser:
    def __init__(self, lexer: Lexer):
        self.lexer = lexer
        self.current_token: Token = None

    def parse(self):
        statements = []
        while self.current_token.type != TokenType.EOF:
            statements.append(self._parse_statement())

    def _parse_statement(self):
        pass
