from tokens import Token, TokenType
from typing import Callable, Dict

from source.lexer import Lexer
from source.nodes import *
from source.utils import ParserException

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

            TokenType.IDENTIFIER: lambda: ( self._parse_assignment
                                        if self.peeked_token.type == TokenType.OP_ASSIGN
                                        else self._parse_expression() )                     # =     -> assignment
                                        if self.peeked_token.type != TokenType.LPAREN      # (     -> function call
                                        else self._parse_function_call()                    # other -> expression
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

    def _match(self, expected_type: TokenType):
        token = self.current_token
        if token.type == expected_type:
            self._advance()
            return token
        else:
            raise ParserException(f"Unexpected token {token.type}", token.code_position)

    # --- PARSERS ---

    def parse(self):
        statements = []
        while self.current_token.type != TokenType.EOF:
            statements.append(self._parse_statement())

    def _parse_statement(self):
        token_type = self.current_token.type

        parser_func = self.statement_parsers.get(token_type)
        if parser_func:
            return parser_func()

        else:
            expression = self._parse_expression()
            self._match(TokenType.SEMICOLON)
            return ExpressionNode(expression)

    def _parse_function_statement(self):
        token_type = self.current_token.type

        if token_type == TokenType.KEYWORD_FUNC:
            raise ParserException(f"Cannot define function inside function", self.current_token.code_position)

        parser_func = self.statement_parsers.get(token_type)
        if parser_func:
            return parser_func()

        else:
            expr = self._parse_expression()
            self._match(TokenType.SEMICOLON)
            return ExpressionNode(expression=expr)

    def _parse_type(self):
        token = self.current_token
        if self.current_token.type == TokenType.KEYWORD_LIST:
            self._advance()
            self._match(TokenType.OP_LT)
            child_node = self._parse_type()
            self._match(TokenType.OP_GT)
            return ListTypeNode(self.current_token, child_node)
        else:
            self._advance()
            return TypeNode(token)

    def _parse_variable_declaration(self):
        var_type_node = self._parse_type()
        identifier = self._match(TokenType.IDENTIFIER)
        self._match(TokenType.OP_ASSIGN)
        value_expr = self._parse_expression()
        self._match(TokenType.SEMICOLON)
        return VariableDeclarationNode(var_type_node, identifier, value_expr)

    def _parse_parameter_list(self):
        params = []
        param_type = self._parse_type()
        param_name = self._match(TokenType.IDENTIFIER)
        params.append(ParameterNode(param_type, param_name))

        while self.current_token.type == TokenType.COMMA:
            self._match(TokenType.COMMA)
            param_type = self._parse_type()
            param_name = self._match(TokenType.IDENTIFIER)
            params.append(ParameterNode(param_type, param_name))

        return params

    def _parse_function_body(self):
        self._match(TokenType.LBRACE)

        statements = []
        while self.peeked_token.type != TokenType.RBRACE and self.peeked_token.type != TokenType.EOF:
            statements.append(self._parse_function_statement())

        self._match(TokenType.RBRACE)
        return FunctionBodyNode(statements)

    def _parse_function_definition(self):
        self._match(TokenType.KEYWORD_FUNC)
        return_type = self._parse_type()
        name = self._match(TokenType.IDENTIFIER)
        self._match(TokenType.LPAREN)

        parameters = []
        if self.peeked_token.type != TokenType.RPAREN:
            parameters = self._parse_parameter_list()

        self._match(TokenType.RPAREN)
        body = self._parse_function_body()

        return FunctionDefinitionNode(return_type, name, parameters, body)

    def _parse_if_statement(self):
        pass

    def _parse_while_loop(self):
        pass

    def _parse_assignment(self):
        pass

    def _parse_function_call(self):
        pass

    def _parse_expression(self):
        pass

