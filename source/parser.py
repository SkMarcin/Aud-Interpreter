from tokens import Token, TokenType
from typing import Callable, Dict

from source.lexer import Lexer
from source.nodes import ExpressionNode

class Parser:
    def __init__(self, lexer: Lexer):
        self.lexer: Lexer = lexer
        self.current_token: Token = None
        self.peeked_token: Token = None
        self.statement_parsers: Dict[TokenType, Callable] = {
            TokenType.KEYWORD_INT: self._parse_variable_declaration,
            TokenType.KEYWORD_FLOAT: self._parse_variable_declaration,
            TokenType.KEYWORD_BOOL: self._parse_variable_declaration,
            TokenType.KEYWORD_STRING: self._parse_variable_declaration,
            TokenType.KEYWORD_FOLDER: self._parse_variable_declaration,
            TokenType.KEYWORD_FILE: self._parse_variable_declaration,
            TokenType.KEYWORD_AUDIO: self._parse_variable_declaration,
            TokenType.KEYWORD_LIST: self._parse_variable_declaration,

            TokenType.KEYWORD_FUNC: self._parse_function_definition,
            TokenType.KEYWORD_IF: self._parse_if_statement,
            TokenType.KEYWORD_WHILE: self._parse_while_loop,

            TokenType.IDENTIFIER: lambda: self._parse_assignment
                                        if self._peek_token().type == TokenType.OP_ASSIGN
                                        else self._parse_expression_or_call()
        }

        self._advance()
        self._advance()

    # --- HELPER ---

    def _advance(self):
        self.current_token = self.peeked_token
        if self.current_token is not None and self.current_token.type != TokenType.EOF:
            self.lookahead_token = self.lexer.get_next_token()
        else:
            self.lookahead_token = self.current_token

    # --- PARSERS ---

    def parse(self):
        statements = []
        while self.current_token.type != TokenType.EOF:
            statements.append(self._parse_statement())

    def _parse_statement(self):
        token_type = self._peek().type

        parser_func = self.statement_parsers.get(token_type)
        if parser_func:
            return parser_func()



        else:
            expr = self._parse_expression()
            self._match(TokenType.SEMICOLON)
            return ExpressionNode(expression=expr)

    def _parse_variable_declaration(self):
        pass

    def _parse_function_definition(self):
        pass

    def _parse_if_statement(self):
        pass

    def _parse_while_loop(self):
        pass

    def _parse_assignment(self):
        pass

    def _parse_expression_or_call(self):
        pass

    def _parse_expression(self):
        pass

