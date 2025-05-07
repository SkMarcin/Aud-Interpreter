from typing import Callable, Dict

from source.tokens import Token, TokenType
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

            TokenType.IDENTIFIER: lambda: ( self._parse_assignment()
                                        if self.peeked_token.type == TokenType.OP_ASSIGN
                                        else self._parse_call_or_expression_statement() )
        }

        self._advance()
        self._advance()

    # --- HELPER ---

    def _advance(self):
        self.current_token = self.peeked_token
        if self.current_token is not None and self.current_token.type != TokenType.EOF:
            self.peeked_token = self.lexer.get_next_token()
        elif self.peeked_token is None:
            self.peeked_token = self.lexer.get_next_token()

    def _match(self, expected_type: TokenType):
        token = self.current_token
        if token.type == expected_type:
            self._advance()
            return token
        else:
            raise ParserException(f"Expected {expected_type} but found {token.type}", token.code_position)

    # --- PARSERS ---

    def parse(self):
        statements = []
        if not self.current_token:
            return ProgramNode(statements)
        while self.current_token.type != TokenType.EOF:
            statements.append(self._parse_statement())
        return ProgramNode(statements)

    def _parse_statement(self) -> StatementNode:
        token_type = self.current_token.type

        parser_func = self.statement_parsers.get(token_type)
        if parser_func:
            return parser_func()

        else:
            expression = self._parse_expression()
            self._match(TokenType.SEMICOLON)
            return ExpressionNode(expression)

    def _parse_block_statement(self) -> BlockStatementNode:
        token_type = self.current_token.type

        if token_type == TokenType.KEYWORD_FUNC:
            raise ParserException(f"Cannot define function inside function", self.current_token.code_position)

        if token_type == TokenType.KEYWORD_RETURN:
            return

        parser_func = self.statement_parsers.get(token_type)
        if parser_func:
            return parser_func()

        else:
            expr = self._parse_expression()
            self._match(TokenType.SEMICOLON)
            return ExpressionStatementNode(expression=expr) # TODO: change

    def _parse_type(self) -> TypeNode:
        token = self.current_token
        if token.type == TokenType.KEYWORD_LIST:
            self._advance()
            self._match(TokenType.OP_LT)
            child_node = self._parse_type()
            self._match(TokenType.OP_GT)
            return ListTypeNode(token, child_node)
        else:
            self._advance()
            return TypeNode(token)

    def _parse_variable_declaration(self) -> VariableDeclarationNode:
        var_type_node = self._parse_type()
        identifier = self._match(TokenType.IDENTIFIER)
        self._match(TokenType.OP_ASSIGN)
        value_expr = self._parse_expression()
        self._match(TokenType.SEMICOLON)
        return VariableDeclarationNode(var_type_node, identifier, value_expr)

    def _parse_parameter_list(self) -> List[ParameterNode]:
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

    def _parse_return_statement(self) -> ReturnStatementNode:
        # return_statement = "return", [ expression ] ";" ;
        self._match(TokenType.KEYWORD_RETURN)
        value_expr = None
        if self.current_token and self.current_token.type != TokenType.SEMICOLON:
            value_expr = self._parse_expression()
        self._match(TokenType.SEMICOLON)
        return ReturnStatementNode(value_expr)

    def _parse_function_body(self) -> FunctionBodyNode:
        self._match(TokenType.LBRACE)

        statements = []
        while self.current_token.type not in [TokenType.RBRACE, TokenType.EOF, TokenType.KEYWORD_RETURN]:
            statements.append(self._parse_block_statement())

        return_statement = self._parse_return_statement()

        self._match(TokenType.RBRACE)
        return FunctionBodyNode(statements, return_statement)

    def _parse_function_definition(self) -> FunctionDefinitionNode:
        self._match(TokenType.KEYWORD_FUNC)
        return_type = self._parse_type()
        name = self._match(TokenType.IDENTIFIER)
        self._match(TokenType.LPAREN)

        parameters = []
        if self.current_token.type != TokenType.RPAREN:
            parameters = self._parse_parameter_list()

        self._match(TokenType.RPAREN)
        body = self._parse_function_body()

        return FunctionDefinitionNode(return_type, name, parameters, body)

    def _parse_code_block(self) -> CodeBlockNode:
        self._match(TokenType.LBRACE)

        statements = []
        while self.current_token and self.current_token.type != TokenType.RBRACE:
            statements.append(self._parse_block_statement())

        self._match(TokenType.RBRACE)
        return CodeBlockNode(statements)

    def _parse_if_statement(self) -> IfStatementNode:
        self._match(TokenType.KEYWORD_IF)
        self._match(TokenType.LPAREN)
        condition = self._parse_expression()

        self._match(TokenType.RPAREN)
        if_block = self._parse_code_block()

        else_block = None
        if self.current_token and self.current_token.type == TokenType.KEYWORD_ELSE:
            self._match(TokenType.KEYWORD_ELSE)
            else_block = self._parse_code_block()

        return IfStatementNode(condition, if_block, else_block)

    def _parse_while_loop(self) -> WhileLoopNode:
        self._match(TokenType.KEYWORD_WHILE)
        self._match(TokenType.LPAREN)
        condition = self._parse_expression()

        self._match(TokenType.RPAREN)
        body = self._parse_code_block()

        return WhileLoopNode(condition, body)

    def _parse_assignment(self) -> AssignmentNode:
        identifier_node = self._parse_factor()

        if not isinstance(identifier_node, (IdentifierNode, MemberAccessNode)):
            pos = self.current_token.code_position
            raise ParserException(f"Invalid left-hand side ({type(identifier_node).__name__}) for assignment", pos)

        self._match(TokenType.OP_ASSIGN)
        value_expr = self._parse_expression()
        self._match(TokenType.SEMICOLON)
        return AssignmentNode(identifier_node, value_expr)

    def _parse_call_or_expression_statement(self) -> BlockStatementNode:
        """
        Handles the case where an IDENTIFIER is seen, but not followed by '='.
        It could be a function call statement 'func(...);' or just an expression 'expr;'.
        """
        expr = self._parse_expression()

        self._match(TokenType.SEMICOLON)

        if isinstance(expr, FunctionCallNode):
            return FunctionCallStatementNode(call_expression=expr)
        else:
            return ExpressionStatementNode(expression=expr)

    def _parse_factor(self) -> ExpressionNode:
        """Parses the highest precedence items: literals, identifiers, calls, parens, etc."""
        token = self.current_token

        node: ExpressionNode = None

        # --- Check for Primary Expression Starters ---
        # Literals
        literal_types = {TokenType.LITERAL_INT, TokenType.LITERAL_FLOAT, TokenType.LITERAL_STRING,
                        TokenType.KEYWORD_TRUE, TokenType.KEYWORD_FALSE, TokenType.KEYWORD_NULL}
        if token.type in literal_types:
            node = LiteralNode(token=self._match(token.type))

        # Identifier
        elif token.type == TokenType.IDENTIFIER:
            ident_token = self._match(TokenType.IDENTIFIER)
            if self.current_token and self.current_token.type == TokenType.LPAREN:
                # Function call
                node = self._parse_function_call(IdentifierNode(token=ident_token))
            else:
                # Identifier
                node = IdentifierNode(token=ident_token)

        # Constructor Call
        elif token.type in {TokenType.KEYWORD_FILE, TokenType.KEYWORD_FOLDER, TokenType.KEYWORD_AUDIO}:
            type_token = self._match(token.type)
            if self.current_token and self.current_token.type == TokenType.LPAREN:
                node = self._parse_constructor_call(type_token)
            else:
                pos = getattr(self.current_token or token, 'code_position')
                raise ParserException(f"Expected '(' after constructor keyword {type_token.value}", pos)

        # List Literal
        elif token.type == TokenType.LBRACKET:
            node = self._parse_list_literal()

        # Parenthesized Expression ( ... )
        elif token.type == TokenType.LPAREN:
            self._match(TokenType.LPAREN)
            node = self._parse_expression()
            self._match(TokenType.RPAREN)

        # --- Error on Unexpected Token ---
        else:
            pos = token.code_position
            raise ParserException(f"Unexpected token {token.type.name} ('{token.value}') when expecting the start of a factor (literal, identifier, '(', '[', etc.)", pos)

        # --- Handle Postfix Operations (Member Access, Method Calls) ---
        while self.current_token and self.current_token.type == TokenType.DOT:
            self._match(TokenType.DOT)
            member_name = self._match(TokenType.IDENTIFIER)
            if self.current_token and self.current_token.type == TokenType.LPAREN:
                # Method call
                member_access_expr = MemberAccessNode(object_expr=node, member_name=member_name)
                node = self._parse_function_call(member_access_expr)
            else:
                # Property access
                node = MemberAccessNode(object_expr=node, member_name=member_name)

        return node

    def _parse_argument_list(self) -> List[ExpressionNode]:
        # argument_list = expression { "," expression } ;
        args = []
        args.append(self._parse_expression())
        while self.current_token and self.current_token.type == TokenType.COMMA:
            self._match(TokenType.COMMA)
            args.append(self._parse_expression())
        return args

    def _parse_function_call(self, function_name_node: ExpressionNode) -> FunctionCallNode:
        # Parses: '(', [ argument_list ], ')'
        self._match(TokenType.LPAREN)
        args = []
        if self.current_token and self.current_token.type != TokenType.RPAREN:
            args = self._parse_argument_list()
        self._match(TokenType.RPAREN)
        return FunctionCallNode(function_name=function_name_node, arguments=args)

    def _parse_constructor_call(self, type_token: Token) -> ConstructorCallNode:
        # Parses: '(', [ argument_list ], ')'
        self._match(TokenType.LPAREN)
        args = []
        if self.current_token and self.current_token.type != TokenType.RPAREN:
            args = self._parse_argument_list()
        self._match(TokenType.RPAREN)
        return ConstructorCallNode(type_token=type_token, arguments=args)

    def _parse_list_literal(self) -> ListLiteralNode:
        # list = "[", [ expression, { ",", expression } ], "]";
        self._match(TokenType.LBRACKET)
        elements = []
        if self.current_token and self.current_token.type != TokenType.RBRACKET:
            elements.append(self._parse_expression())
            while self.current_token and self.current_token.type == TokenType.COMMA:
                self._match(TokenType.COMMA)
                elements.append(self._parse_expression())

        self._match(TokenType.RBRACKET)
        return ListLiteralNode(elements=elements)


    # --- Expression Parsing ---

    # expression = logical_or ;
    def _parse_expression(self) -> ExpressionNode:
        return self._parse_logical_or()

    # logical_or = logical_and, { "||", logical_and } ;
    def _parse_logical_or(self) -> ExpressionNode:
        node = self._parse_logical_and()
        while self.current_token and self.current_token.type == TokenType.OP_OR:
            op_token = self._match(TokenType.OP_OR)
            right = self._parse_logical_and()
            node = BinaryOpNode(left=node, operator=op_token, right=right)
        return node

    # logical_and = comparison, { "&&", comparison } ;
    def _parse_logical_and(self) -> ExpressionNode:
        node = self._parse_comparison()
        while self.current_token and self.current_token.type == TokenType.OP_AND:
            op_token = self._match(TokenType.OP_AND)
            right = self._parse_comparison()
            node = BinaryOpNode(left=node, operator=op_token, right=right)
        return node

    # comparison = additive_expression, [ ( "==" | "!=" | "<" | "<=" | ">" | ">=" ), additive_expression ] ;
    def _parse_comparison(self) -> ExpressionNode:
        node = self._parse_additive_expression()
        # Check if the current token is one of the comparison operators
        comparison_ops = {TokenType.OP_EQ, TokenType.OP_NEQ, TokenType.OP_LT,
                          TokenType.OP_LTE, TokenType.OP_GT, TokenType.OP_GTE}
        if self.current_token and self.current_token.type in comparison_ops:
            op_token = self._match(self.current_token.type)
            right = self._parse_additive_expression()
            node = BinaryOpNode(left=node, operator=op_token, right=right)
        return node

    # additive_expression = term, { ("+" | "-"), term } ;
    def _parse_additive_expression(self) -> ExpressionNode:
        node = self._parse_term()
        while self.current_token and self.current_token.type in {TokenType.OP_PLUS, TokenType.OP_MINUS}:
            op_token = self._match(self.current_token.type)
            right = self._parse_term()
            node = BinaryOpNode(left=node, operator=op_token, right=right)
        return node

    # term = unary_expression, { ("*" | "/"), unary_expression } ;
    def _parse_term(self) -> ExpressionNode:
        node = self._parse_unary_expression()
        while self.current_token and self.current_token.type in {TokenType.OP_MULTIPLY, TokenType.OP_DIVIDE}:
            op_token = self._match(self.current_token.type)
            right = self._parse_unary_expression()
            node = BinaryOpNode(left=node, operator=op_token, right=right)
        return node

    # unary_expression = ( "-" )? factor ;
    def _parse_unary_expression(self) -> ExpressionNode:
        if self.current_token and self.current_token.type == TokenType.OP_MINUS:
            op_token = self._match(TokenType.OP_MINUS)
            operand = self._parse_factor()
            return UnaryOpNode(operator=op_token, operand=operand)
        else:
            return self._parse_factor()