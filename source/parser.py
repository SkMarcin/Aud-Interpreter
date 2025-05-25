from typing import Callable, Dict, List, Optional

from source.tokens import Token, TokenType, Position
from source.lexer import Lexer
from source.nodes import *
from source.utils import ParserException, UnexpectedTokenException

BINARY_OP_MAP: Dict[TokenType, Callable[..., ExpressionNode]] = {
    TokenType.OP_PLUS: AddNode,
    TokenType.OP_MINUS: SubtractNode,
    TokenType.OP_MULTIPLY: MultiplyNode,
    TokenType.OP_DIVIDE: DivideNode,
    TokenType.OP_EQ: EqualsNode,
    TokenType.OP_NEQ: NotEqualsNode,
    TokenType.OP_LT: LessThanNode,
    TokenType.OP_LTE: LessThanOrEqualNode,
    TokenType.OP_GT: GreaterThanNode,
    TokenType.OP_GTE: GreaterThanOrEqualNode,
    TokenType.OP_AND: LogicalAndNode,
    TokenType.OP_OR: LogicalOrNode,
}

class Parser:
    def __init__(self, lexer: Lexer):
        self.lexer: Lexer = lexer
        self.current_token: Optional[Token] = None
        self._statement_try_parsers: List[Callable[[], Optional[StatementNode]]] = []
        self._factor_try_parsers: List[Callable[[], Optional[ExpressionNode]]] = []

        self._init_try_parsers()

        self._advance()

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

    def _match(self, expected_type: TokenType) -> Token:
        token = self.current_token
        if token and token.type == expected_type:
            self._advance()
            return token
        else:
            pos = token.code_position if token else self.lexer.get_current_pos()
            type_name = token.type.name if token else "None"
            raise UnexpectedTokenException(f"Expected {expected_type} but found {type_name}", pos)
        
    # --- PARSERS ---

    # program = { statement } ;
    def parse(self) -> ProgramNode:
        program_start_pos = Position(1,0)
        if self.current_token:
            program_start_pos = self.current_token.code_position
        else:
            program_start_pos = self.lexer.get_current_pos()

        statements: List[StatementNode] = []

        if not self.current_token: 
            return ProgramNode(start_position=program_start_pos, end_position=program_start_pos, statements=statements)

        while self.current_token and self.current_token.type != TokenType.EOF:
            statements.append(self._parse_statement())
        
        program_end_pos = self.current_token.code_position if self.current_token else program_start_pos

        if statements:
            statement_start_pos = statements[0].start_position
        else:
            statement_start_pos = program_start_pos

        return ProgramNode(start_position=statement_start_pos, end_position=program_end_pos, statements=statements)

    # statement       = block_statement | function_definition
    # block_statement = variable_declaration
    #                 | assignment
    #                 | function_call
    #                 | if_statement
    #                 | while_loop
    #                 | expression;
    def _parse_statement(self) -> StatementNode:
        for try_parser_func in self._statement_try_parsers:
            node = try_parser_func()
            if node is not None:
                return node

        pos = self.current_token.code_position if self.current_token else self.lexer.get_current_pos()
        type_name = self.current_token.type.name if self.current_token else "None"
        raise UnexpectedTokenException(position=pos, type=self.current_token.type) 

    # type      = "void"
    #           | "int"
    #           | "bool"
    #           | "string"
    #           | "Folder"
    #           | "File"
    #           | "Audio"
    #           | list_type ;
    # list_type = "List", "<", type, ">" ;
    def _parse_type(self) -> TypeNode:
        start_token = self.current_token
        simple_types = [TokenType.KEYWORD_INT, TokenType.KEYWORD_FLOAT, TokenType.KEYWORD_BOOL, 
                        TokenType.KEYWORD_STRING, TokenType.KEYWORD_VOID, TokenType.KEYWORD_FOLDER, 
                        TokenType.KEYWORD_FILE, TokenType.KEYWORD_AUDIO]
        
        if start_token.type == TokenType.KEYWORD_LIST:
            list_keyword_token = self._match(TokenType.KEYWORD_LIST)
            self._match(TokenType.OP_LT)
            child_node = self._parse_type()
            gt_token = self._match(TokenType.OP_GT)
            return ListTypeNode(start_position=list_keyword_token.code_position, 
                                end_position=gt_token.code_position,
                                type_name=str(list_keyword_token.value),
                                child_type_node=child_node)
        elif start_token.type in simple_types:
            matched_token = self._match(start_token.type)
            return TypeNode(start_position=matched_token.code_position,
                            end_position=matched_token.code_position,
                            type_name=str(matched_token.value))
        else:
            raise ParserException(f"Unexpected token {start_token.type} when expecting type keyword", start_token.code_position)

    # variable_declaration = type, identifier, "=", expression, ";" ;
    def _try_parse_variable_declaration(self) -> Optional[VariableDeclarationNode]:
        type_keywords = {
            TokenType.KEYWORD_INT, TokenType.KEYWORD_FLOAT, TokenType.KEYWORD_BOOL,
            TokenType.KEYWORD_STRING, TokenType.KEYWORD_FOLDER, TokenType.KEYWORD_FILE,
            TokenType.KEYWORD_AUDIO, TokenType.KEYWORD_LIST
        }
        if self.current_token.type not in type_keywords:
            return None
        
        var_type_node = self._parse_type()
        identifier_token = self._match(TokenType.IDENTIFIER)
        self._match(TokenType.OP_ASSIGN)
        value_expr = self._parse_expression()
        semicolon_token = self._match(TokenType.SEMICOLON)
        return VariableDeclarationNode(start_position=var_type_node.start_position,
                                       end_position=semicolon_token.code_position,
                                       var_type=var_type_node, 
                                       identifier_name=str(identifier_token.value), 
                                       value=value_expr)

    # parameter_list = type, identifier, { ",", type, identifier } ;
    def _parse_parameter_list(self) -> List[ParameterNode]:
        params = []
        param_type_node = self._parse_type()
        param_name_token = self._match(TokenType.IDENTIFIER)
        params.append(ParameterNode(start_position=param_type_node.start_position,
                                    end_position=param_name_token.code_position,
                                    param_type=param_type_node, 
                                    param_name=str(param_name_token.value)))

        while self.current_token.type == TokenType.COMMA:
            self._match(TokenType.COMMA)
            param_type_node = self._parse_type()
            param_name_token = self._match(TokenType.IDENTIFIER)
            params.append(ParameterNode(start_position=param_type_node.start_position,
                                        end_position=param_name_token.code_position,
                                        param_type=param_type_node, 
                                        param_name=str(param_name_token.value)))
        return params

    # return_statement = "return", [ expression ] ";" ;
    def _try_parse_return_statement(self) -> Optional[ReturnStatementNode]:
        if self.current_token.type != TokenType.KEYWORD_RETURN:
            return None
        
        return_keyword_token = self._match(TokenType.KEYWORD_RETURN)
        start_pos = return_keyword_token.code_position
        
        value_expr = None
        if self.current_token and self.current_token.type != TokenType.SEMICOLON:
            value_expr = self._parse_expression()
            
        semicolon_token = self._match(TokenType.SEMICOLON)
        end_pos = semicolon_token.code_position
        
        return ReturnStatementNode(start_position=start_pos, end_position=end_pos, value=value_expr)

    # function_definition = "func", type, identifier, "(", [ parameter_list ] ")",
    #                       function_body ;
    def _try_parse_function_definition(self) -> Optional[FunctionDefinitionNode]:
        if self.current_token.type != TokenType.KEYWORD_FUNC:
            return None
        
        func_keyword_token = self._match(TokenType.KEYWORD_FUNC)
        start_pos = func_keyword_token.code_position
        
        return_type_node = self._parse_type()
        name_token = self._match(TokenType.IDENTIFIER)
        self._match(TokenType.LPAREN)

        parameters: List[ParameterNode] = []
        if self.current_token and self.current_token.type != TokenType.RPAREN:
            parameters = self._parse_parameter_list()

        self._match(TokenType.RPAREN)
        body_node = self._parse_code_block()
        end_pos = body_node.end_position

        return FunctionDefinitionNode(start_position=start_pos,
                                      end_position=end_pos,
                                      return_type=return_type_node, 
                                      identifier_name=str(name_token.value), 
                                      parameters=parameters, 
                                      body=body_node)

    # code_block = "{", { block_statement }, "}"
    def _parse_code_block(self) -> CodeBlockNode:
        lbrace_token = self._match(TokenType.LBRACE)
        start_pos = lbrace_token.code_position

        statements: List[StatementNode] = []
        while self.current_token and self.current_token.type != TokenType.RBRACE:
            statements.append(self._parse_statement())

        rbrace_token = self._match(TokenType.RBRACE)
        end_pos = rbrace_token.code_position
        return CodeBlockNode(start_position=start_pos, end_position=end_pos, statements=statements)

    # if_statement = "if", "(", expression, ")",
    #                code_block,
    #                [ "else", code_block ] ;
    def _try_parse_if_statement(self) -> Optional[IfStatementNode]:
        if self.current_token.type != TokenType.KEYWORD_IF:
            return None
        
        if_keyword_token = self._match(TokenType.KEYWORD_IF)
        start_pos = if_keyword_token.code_position
        
        self._match(TokenType.LPAREN)
        condition = self._parse_expression()
        self._match(TokenType.RPAREN)
        
        if_block = self._parse_code_block()
        end_pos = if_block.end_position

        else_block = None
        if self.current_token and self.current_token.type == TokenType.KEYWORD_ELSE:
            self._match(TokenType.KEYWORD_ELSE)
            else_block = self._parse_code_block()
            end_pos = else_block.end_position

        return IfStatementNode(start_position=start_pos,
                               end_position=end_pos,
                               condition=condition, 
                               if_block=if_block, 
                               else_block=else_block)
    
    # while_loop = "while", "(", expression, ")", code_block ;
    def _try_parse_while_loop(self) -> Optional[WhileLoopNode]:
        if not self.current_token or self.current_token.type != TokenType.KEYWORD_WHILE:
            return None
        
        while_keyword_token = self._match(TokenType.KEYWORD_WHILE)
        start_pos = while_keyword_token.code_position
        
        self._match(TokenType.LPAREN)
        condition = self._parse_expression()
        self._match(TokenType.RPAREN)
        
        body = self._parse_code_block()
        end_pos = body.end_position

        return WhileLoopNode(start_position=start_pos,
                             end_position=end_pos,
                             condition=condition, 
                             body=body)
    
    # function_call = identifier, "(", [ argument_list ], ")" ;
    # or
    # identifier    = letter, { letter | digit | "_" } ;
    # or
    # expression    = logical_or ;
    def _try_parse_identifier_driven_statement(self) -> Optional[StatementNode]:
        if not self.current_token or self.current_token.type != TokenType.IDENTIFIER:
            return None

        initial_expr = self._parse_expression()
        start_pos = initial_expr.start_position

        if self.current_token and self.current_token.type == TokenType.OP_ASSIGN:
            if not isinstance(initial_expr, (IdentifierNode, MemberAccessNode)):
                err_pos = initial_expr.end_position
                raise ParserException(f"Invalid left-hand side ({type(initial_expr).__name__}) for assignment", err_pos)

            self._match(TokenType.OP_ASSIGN)
            value_expr = self._parse_expression()
            semicolon_token = self._match(TokenType.SEMICOLON)
            end_pos = semicolon_token.code_position
            return AssignmentNode(start_position=start_pos,
                                  end_position=end_pos,
                                  identifier=initial_expr, 
                                  value=value_expr)
        else:
            semicolon_token = self._match(TokenType.SEMICOLON)
            end_pos = semicolon_token.code_position

            if isinstance(initial_expr, FunctionCallNode):
                return FunctionCallStatementNode(start_position=start_pos,
                                                 end_position=end_pos,
                                                 call_expression=initial_expr)
            else:
                return ExpressionStatementNode(start_position=start_pos,
                                               end_position=end_pos,
                                               expression=initial_expr)

    # expression = logical_or ;
    def _try_parse_expression_statement(self) -> Optional[ExpressionStatementNode]:
        known_statement_keywords_or_starts = {
            TokenType.KEYWORD_INT, TokenType.KEYWORD_FLOAT, TokenType.KEYWORD_BOOL,
            TokenType.KEYWORD_STRING, TokenType.KEYWORD_FOLDER, TokenType.KEYWORD_FILE,
            TokenType.KEYWORD_AUDIO, TokenType.KEYWORD_LIST, TokenType.KEYWORD_FUNC, 
            TokenType.KEYWORD_IF, TokenType.KEYWORD_WHILE, TokenType.KEYWORD_RETURN, 
            TokenType.IDENTIFIER,
        }
        if self.current_token.type in known_statement_keywords_or_starts:
            return None

        try:
            expression = self._parse_expression()
            if self.current_token and self.current_token.type == TokenType.SEMICOLON:
                semicolon_token = self._match(TokenType.SEMICOLON)
                return ExpressionStatementNode(start_position=expression.start_position,
                                               end_position=semicolon_token.code_position,
                                               expression=expression)
        except ParserException:
            return None
        
    def _parse_primary_expression(self) -> ExpressionNode:
        for try_parser_func in self._factor_try_parsers:
            node = try_parser_func()
            if node is not None:
                return node
        
        token = self.current_token
        pos = token.code_position if token else self.lexer.get_current_pos()
        type_name = token.type.name if token else "None"
        val = token.value if token else ""
        raise ParserException(f"Unexpected token {type_name} ('{val}') when expecting the start of a factor (literal, identifier, '(', '[', constructor, etc.)", pos)   
    
    # factor = literal
            # | identifier
            # | function_call
            # | member_access
            # | constructor_call
            # | list
            # | "(", expression, ")" ;
    def _parse_factor(self) -> ExpressionNode:
        node = self._parse_primary_expression()
        
        while self.current_token and self.current_token.type == TokenType.DOT:
            self._match(TokenType.DOT)
            member_name_token = self._match(TokenType.IDENTIFIER)

            if self.current_token and self.current_token.type == TokenType.LPAREN:
                # Method call: object.member()
                member_access_expr = MemberAccessNode(start_position=node.start_position,
                                                      end_position=member_name_token.code_position,
                                                      object_expr=node, 
                                                      member_name=str(member_name_token.value))
                node = self._parse_function_call_args(member_access_expr)
            else:
                # Property access: object.member
                node = MemberAccessNode(start_position=node.start_position,
                                        end_position=member_name_token.code_position,
                                        object_expr=node, 
                                        member_name=str(member_name_token.value))
        return node

    # literal = integer_literal | float_literal | string_literal | boolean_literal ;
    def _try_parse_literal_factor(self) -> Optional[LiteralNode]:
        if not self.current_token: return None
        
        token_type = self.current_token.type
        value = self.current_token.value
        pos = self.current_token.code_position

        literal_types = {TokenType.LITERAL_INT, TokenType.LITERAL_FLOAT, TokenType.LITERAL_STRING,
                         TokenType.KEYWORD_TRUE, TokenType.KEYWORD_FALSE, TokenType.KEYWORD_NULL}
        if token_type in literal_types:
            self._advance()
            return LiteralNode(start_position=pos, end_position=pos, value=value)
        else:
            return None
    
    # list = "[", [ expression, { ",", expression } ], "]";
    def _try_parse_list_literal_factor(self) -> Optional[ListLiteralNode]:
        if not self.current_token or self.current_token.type != TokenType.LBRACKET:
            return None
        
        lbracket_token = self._match(TokenType.LBRACKET)
        start_pos = lbracket_token.code_position
        
        elements: List[ExpressionNode] = []
        if self.current_token and self.current_token.type != TokenType.RBRACKET:
            elements.append(self._parse_expression())
            while self.current_token and self.current_token.type == TokenType.COMMA:
                self._match(TokenType.COMMA)
                elements.append(self._parse_expression())
        
        rbracket_token = self._match(TokenType.RBRACKET)
        end_pos = rbracket_token.code_position
        return ListLiteralNode(start_position=start_pos, end_position=end_pos, elements=elements)

    # identifier = letter, { letter | digit | "_" } ;
    # or
    # function_call = identifier, "(", [ argument_list ], ")" ;
    def _try_parse_identifier_or_call_factor(self) -> Optional[ExpressionNode]:
        if self.current_token.type != TokenType.IDENTIFIER:
            return None
        
        ident_token = self._match(TokenType.IDENTIFIER)
        identifier_node = IdentifierNode(start_position=ident_token.code_position,
                                         end_position=ident_token.code_position,
                                         name=str(ident_token.value))

        if self.current_token and self.current_token.type == TokenType.LPAREN:
            return self._parse_function_call_args(identifier_node)
        else:
            return identifier_node

    # constructor_call = ( "File" | "Folder" | "Audio" ), "(", [ argument_list ], ")";
    def _try_parse_constructor_call_factor(self) -> Optional[ConstructorCallNode]:
        constructor_keywords = {TokenType.KEYWORD_FILE, TokenType.KEYWORD_FOLDER, TokenType.KEYWORD_AUDIO}
        if self.current_token.type not in constructor_keywords:
            return None

        type_token = self._match(self.current_token.type)
        type_name_str = str(type_token.value)
        type_name_start_pos = type_token.code_position
        
        if self.current_token and self.current_token.type == TokenType.LPAREN:
            return self._parse_constructor_call_args(type_name_str, type_name_start_pos)
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
        args: List[ExpressionNode] = []
        args.append(self._parse_expression())
        while self.current_token and self.current_token.type == TokenType.COMMA:
            self._match(TokenType.COMMA)
            args.append(self._parse_expression())
        return args

    # function_call = identifier, "(", [ argument_list ], ")" ;
    def _parse_function_call_args(self, function_name_node: ExpressionNode) -> FunctionCallNode:
        start_pos = function_name_node.start_position
        
        self._match(TokenType.LPAREN)
        args: List[ExpressionNode] = []
        if self.current_token and self.current_token.type != TokenType.RPAREN:
            args = self._parse_argument_list()
        
        rparen_token = self._match(TokenType.RPAREN)
        end_pos = rparen_token.code_position
        
        return FunctionCallNode(start_position=start_pos, 
                                end_position=end_pos, 
                                function_name=function_name_node, 
                                arguments=args)

    # "(", [ argument_list ], ")"
    def _parse_constructor_call_args(self, type_name_str: str, type_name_start_pos: Position) -> ConstructorCallNode:    
        start_pos = type_name_start_pos
        
        self._match(TokenType.LPAREN)
        args: List[ExpressionNode] = []
        if self.current_token and self.current_token.type != TokenType.RPAREN:
            args = self._parse_argument_list()
            
        rparen_token = self._match(TokenType.RPAREN)
        end_pos = rparen_token.code_position
        
        return ConstructorCallNode(start_position=start_pos,
                                   end_position=end_pos,
                                   type_name=type_name_str, 
                                   arguments=args)

    # --- EXPRESSION PARSING ---

    # expression = logical_or ;
    def _parse_expression(self) -> ExpressionNode:
        return self._parse_logical_or()

    # logical_or = logical_and, { "||", logical_and } ;
    def _parse_logical_or(self) -> ExpressionNode:
        node = self._parse_logical_and()
        while self.current_token and self.current_token.type == TokenType.OP_OR:
            op_token = self._match(TokenType.OP_OR)
            right = self._parse_logical_and()
            node_class = BINARY_OP_MAP[op_token.type]
            node = node_class(start_position=node.start_position,
                              end_position=right.end_position,
                              left=node, 
                              right=right)
        return node

    # logical_and = comparison, { "&&", comparison } ;
    def _parse_logical_and(self) -> ExpressionNode:
        node = self._parse_comparison()
        while self.current_token and self.current_token.type == TokenType.OP_AND:
            op_token = self._match(TokenType.OP_AND)
            right = self._parse_comparison()
            node_class = BINARY_OP_MAP[op_token.type]
            node = node_class(start_position=node.start_position,
                              end_position=right.end_position,
                              left=node, 
                              right=right)
        return node

    # comparison = additive_expression, [ ( "==" | "!=" | "<" | "<=" | ">" | ">=" ), additive_expression ] ;
    def _parse_comparison(self) -> ExpressionNode:
        node = self._parse_additive_expression()
        comparison_ops = {TokenType.OP_EQ, TokenType.OP_NEQ, TokenType.OP_LT,
                          TokenType.OP_LTE, TokenType.OP_GT, TokenType.OP_GTE}
        if self.current_token and self.current_token.type in comparison_ops:
            op_token = self._match(self.current_token.type)
            right = self._parse_additive_expression()
            node_class = BINARY_OP_MAP[op_token.type]
            node = node_class(start_position=node.start_position,
                              end_position=right.end_position,
                              left=node, 
                              right=right)
        return node

    # additive_expression = term, { ("+" | "-"), term } ;
    def _parse_additive_expression(self) -> ExpressionNode:
        node = self._parse_term()
        while self.current_token and self.current_token.type in {TokenType.OP_PLUS, TokenType.OP_MINUS}:
            op_token = self._match(self.current_token.type)
            right = self._parse_term()
            node_class = BINARY_OP_MAP[op_token.type]
            node = node_class(start_position=node.start_position,
                              end_position=right.end_position,
                              left=node, 
                              right=right)
        return node

    # term = unary_expression, { ("*" | "/"), unary_expression } ;
    def _parse_term(self) -> ExpressionNode:
        node = self._parse_unary_expression()
        while self.current_token and self.current_token.type in {TokenType.OP_MULTIPLY, TokenType.OP_DIVIDE}:
            op_token = self._match(self.current_token.type)
            right = self._parse_unary_expression()
            node_class = BINARY_OP_MAP[op_token.type]
            node = node_class(start_position=node.start_position,
                              end_position=right.end_position,
                              left=node, 
                              right=right)
        return node

    # unary_expression = ( "-" )? factor ;
    def _parse_unary_expression(self) -> ExpressionNode:
        if self.current_token and self.current_token.type == TokenType.OP_MINUS:
            op_token = self._match(TokenType.OP_MINUS)
            operand = self._parse_factor()
            return UnaryMinusNode(start_position=op_token.code_position,
                                  end_position=operand.end_position,
                                  operand=operand)
        else:
            return self._parse_factor()
