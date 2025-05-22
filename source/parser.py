from typing import Callable, Dict

from source.tokens import Token, TokenType
from source.lexer import Lexer
from source.nodes import *
from source.utils import ParserException

class Parser:
    def __init__(self, lexer: Lexer):
        self.lexer: Lexer = lexer
        self.current_token: Token = None
        self._statement_try_parsers: List[Callable[[], Optional[StatementNode]]] = []
        self._factor_try_parsers: List[Callable[[], Optional[ExpressionNode]]] = []

        self._init_try_parsers()

        self._advance()

    # --- HELPER ---

    def _init_try_parsers(self):
        self._statement_try_parsers = [
            self._try_parse_variable_declaration,
            self._try_parse_function_definition,
            self._try_parse_if_statement,
            self._try_parse_while_loop,
            self._try_parse_return_statement,
            self._try_parse_identifier_driven_statement,
            self._try_parse_expression_statement,
        ]

        self._factor_try_parsers = [
            self._try_parse_literal_factor,
            self._try_parse_identifier_or_call_factor,
            self._try_parse_constructor_call_factor,
            self._try_parse_list_literal_factor,
            self._try_parse_parenthesized_expression_factor,
        ]

    def _advance(self):
        if self.current_token and self.current_token.type != TokenType.EOF:
            self.current_token = self.lexer.get_next_token()
        elif self.current_token is None:
            self.current_token = self.lexer.get_next_token()

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
        for try_parser_func in self._statement_try_parsers:
            node = try_parser_func()
            if node is not None:
                return node

        pos = self.current_token.code_position if self.current_token else None
        type_name = self.current_token.type.name if self.current_token else "None"
        raise ParserException(f"Invalid or unexpected token {type_name} at start of statement", pos)

    def _parse_type(self) -> TypeNode:
        token = self.current_token
        simple_types = [TokenType.KEYWORD_INT, TokenType.KEYWORD_FLOAT, TokenType.KEYWORD_BOOL, 
                        TokenType.KEYWORD_STRING, TokenType.KEYWORD_VOID, TokenType.KEYWORD_FOLDER, 
                        TokenType.KEYWORD_FILE, TokenType.KEYWORD_AUDIO]
        if token.type == TokenType.KEYWORD_LIST:
            self._advance()
            self._match(TokenType.OP_LT)
            child_node = self._parse_type()
            self._match(TokenType.OP_GT)
            return ListTypeNode(token, child_node)
        elif token.type in simple_types:
            self._advance()
            return TypeNode(token)
        else:
            raise ParserException(f"Unexpected token {token.type} when expecting type keyword", token.code_position)

    def _try_parse_variable_declaration(self) -> Optional[VariableDeclarationNode]:
        type_keywords = {
            TokenType.KEYWORD_INT, TokenType.KEYWORD_FLOAT, TokenType.KEYWORD_BOOL,
            TokenType.KEYWORD_STRING, TokenType.KEYWORD_FOLDER, TokenType.KEYWORD_FILE,
            TokenType.KEYWORD_AUDIO, TokenType.KEYWORD_LIST
        }
        if self.current_token.type not in type_keywords:
            return None
        
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

    def _try_parse_return_statement(self) -> ReturnStatementNode:
        # return_statement = "return", [ expression ] ";" ;
        if self.current_token.type != TokenType.KEYWORD_RETURN:
            return None
        self._match(TokenType.KEYWORD_RETURN)
        value_expr = None
        if self.current_token and self.current_token.type != TokenType.SEMICOLON:
            value_expr = self._parse_expression()
        self._match(TokenType.SEMICOLON)
        return ReturnStatementNode(value_expr)

    def _parse_function_body(self) -> FunctionBodyNode:
        self._match(TokenType.LBRACE)

        statements = []
        while self.current_token.type not in [TokenType.RBRACE, TokenType.EOF]:
            statements.append(self._parse_statement())

        self._match(TokenType.RBRACE)
        return FunctionBodyNode(statements)

    def _try_parse_function_definition(self) -> Optional[FunctionDefinitionNode]:
        if self.current_token.type != TokenType.KEYWORD_FUNC:
            return None
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
            statements.append(self._parse_statement())

        self._match(TokenType.RBRACE)
        return CodeBlockNode(statements)

    def _try_parse_if_statement(self) -> Optional[IfStatementNode]:
        if self.current_token.type != TokenType.KEYWORD_IF:
            return None
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

    def _try_parse_while_loop(self) -> WhileLoopNode:
        if self.current_token.type != TokenType.KEYWORD_WHILE:
            return None
        
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
            raise ParserException(f"Invalid left-hand side ({identifier_node}) for assignment", pos)

        self._match(TokenType.OP_ASSIGN)
        value_expr = self._parse_expression()
        self._match(TokenType.SEMICOLON)
        return AssignmentNode(identifier_node, value_expr)
    
    def _try_parse_identifier_driven_statement(self) -> Optional[StatementNode]:
        if self.current_token.type != TokenType.IDENTIFIER:
            return None
        initial_expr = self._parse_expression()

        if self.current_token and self.current_token.type == TokenType.OP_ASSIGN:
            # It's an assignment
            if not isinstance(initial_expr, (IdentifierNode, MemberAccessNode)):
                err_pos = self.current_token.code_position
                if hasattr(initial_expr, 'token') and initial_expr.token: # For LiteralNode, IdentifierNode itself
                    err_pos = initial_expr.token.code_position
                elif isinstance(initial_expr, FunctionCallNode):
                    if hasattr(initial_expr.function_name, 'token') and initial_expr.function_name.token:
                        err_pos = initial_expr.function_name.token.code_position

                raise ParserException(f"Invalid left-hand side ({type(initial_expr).__name__}) for assignment", err_pos)

            self._match(TokenType.OP_ASSIGN)
            value_expr = self._parse_expression()
            self._match(TokenType.SEMICOLON)
            return AssignmentNode(identifier=initial_expr, value=value_expr)
        else:
            # Not an assignment. It's a call statement or an expression statement.
            self._match(TokenType.SEMICOLON)

            if isinstance(initial_expr, FunctionCallNode):
                return FunctionCallStatementNode(call_expression=initial_expr)
            else:
                return ExpressionStatementNode(expression=initial_expr)
            
    def _try_parse_expression_statement(self) -> Optional[ExpressionStatementNode]:
        known_statement_keywords = {
            TokenType.KEYWORD_INT, TokenType.KEYWORD_FLOAT, TokenType.KEYWORD_BOOL,
            TokenType.KEYWORD_STRING, TokenType.KEYWORD_FOLDER, TokenType.KEYWORD_FILE,
            TokenType.KEYWORD_AUDIO, TokenType.KEYWORD_LIST,
            TokenType.KEYWORD_FUNC, TokenType.KEYWORD_IF, TokenType.KEYWORD_WHILE, TokenType.KEYWORD_RETURN,
            TokenType.IDENTIFIER
        }
        if self.current_token.type in known_statement_keywords:
            return None

        try:
            expression = self._parse_expression()
            self._match(TokenType.SEMICOLON)
            return ExpressionStatementNode(expression=expression)
        except ParserException:
            return None
            
    def _parse_primary_expression(self) -> ExpressionNode:
        for try_parser_func in self._factor_try_parsers:
            node = try_parser_func()
            if node is not None:
                return node
        
        token = self.current_token
        pos = token.code_position if token else None
        type_name = token.type.name if token else "None"
        val = token.value if token else ""
        raise ParserException(f"Unexpected token {type_name} ('{val}') when expecting the start of a factor (literal, identifier, '(', '[', etc.)", pos)   
    

    def _parse_factor(self) -> ExpressionNode:
        """Parses the highest precedence items: literals, identifiers, calls, parens, etc."""
        node = self._parse_primary_expression()
        
        # --- Handle Postfix Operations (Member Access, Method Calls) ---
        if node is not None:
            while self.current_token and self.current_token.type == TokenType.DOT:
                self._match(TokenType.DOT)
                member_name = self._match(TokenType.IDENTIFIER)
                if self.current_token and self.current_token.type == TokenType.LPAREN:
                    # Method call
                    member_access_expr = MemberAccessNode(object_expr=node, member_name=member_name)
                    node = self._parse_function_call_args(member_access_expr)
                else:
                    # Property access
                    node = MemberAccessNode(object_expr=node, member_name=member_name)

            return node

    def _try_parse_literal_factor(self) -> Optional[LiteralNode]:
        if not self.current_token: return None
        literal_types = {TokenType.LITERAL_INT, TokenType.LITERAL_FLOAT, TokenType.LITERAL_STRING,
                         TokenType.KEYWORD_TRUE, TokenType.KEYWORD_FALSE, TokenType.KEYWORD_NULL}
        if self.current_token.type in literal_types:
            return LiteralNode(token=self._match(self.current_token.type))
        return None
    
    def _try_parse_list_literal_factor(self) -> Optional[ListLiteralNode]:
        if not self.current_token or self.current_token.type != TokenType.LBRACKET:
            return None
        
        self._match(TokenType.LBRACKET)
        elements = []
        if self.current_token and self.current_token.type != TokenType.RBRACKET:
            elements.append(self._parse_expression())
            while self.current_token and self.current_token.type == TokenType.COMMA:
                self._match(TokenType.COMMA)
                elements.append(self._parse_expression())
        self._match(TokenType.RBRACKET)
        return ListLiteralNode(elements=elements)

    def _try_parse_identifier_or_call_factor(self) -> Optional[ExpressionNode]:
        if not self.current_token or self.current_token.type != TokenType.IDENTIFIER:
            return None
        
        ident_token = self._match(TokenType.IDENTIFIER)
        if self.current_token and self.current_token.type == TokenType.LPAREN:
            return self._parse_function_call_args(IdentifierNode(token=ident_token))
        else:
            return IdentifierNode(token=ident_token)

    def _try_parse_constructor_call_factor(self) -> Optional[ConstructorCallNode]:
        if not self.current_token: return None
        constructor_keywords = {TokenType.KEYWORD_FILE, TokenType.KEYWORD_FOLDER, TokenType.KEYWORD_AUDIO}
        if self.current_token.type not in constructor_keywords:
            return None

        type_token = self._match(self.current_token.type)
        if self.current_token and self.current_token.type == TokenType.LPAREN:
            return self._parse_constructor_call_args(type_token)
        else:
            pos = getattr(self.current_token or type_token, 'code_position')
            raise ParserException(f"Expected '(' after constructor keyword {type_token.value}", pos)

    def _try_parse_parenthesized_expression_factor(self) -> Optional[ExpressionNode]:
        if not self.current_token or self.current_token.type != TokenType.LPAREN:
            return None
        
        self._match(TokenType.LPAREN)
        node = self._parse_expression()
        self._match(TokenType.RPAREN)
        return node

    def _parse_argument_list(self) -> List[ExpressionNode]:
        # argument_list = expression { "," expression } ;
        args = []
        args.append(self._parse_expression())
        while self.current_token and self.current_token.type == TokenType.COMMA:
            self._match(TokenType.COMMA)
            args.append(self._parse_expression())
        return args

    def _parse_function_call_args(self, function_name_node: ExpressionNode) -> FunctionCallNode:
        # Parses: '(', [ argument_list ], ')'
        self._match(TokenType.LPAREN)
        args = []
        if self.current_token and self.current_token.type != TokenType.RPAREN:
            args = self._parse_argument_list()
        self._match(TokenType.RPAREN)
        return FunctionCallNode(function_name=function_name_node, arguments=args)

    def _parse_constructor_call_args(self, type_token: Token) -> ConstructorCallNode:
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
