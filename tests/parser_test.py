import unittest
from typing import List, Any
from dataclasses import fields, is_dataclass

from source.utils import UnexpectedTokenException, Position
from source.tokens import TokenType, Token
from source.parser import Parser
from source.nodes import *

def _get_token_end_position(token: Token) -> Position:
    if token.value is None:
        return token.code_position
    value_str = str(token.value)
    return Position(token.code_position.line, token.code_position.column + len(value_str) - 1)

class MockLexer:
    def __init__(self, tokens: List[Token]):
        self.tokens = tokens
        self.pos = 0

    def get_next_token(self) -> Token:
        if self.pos < len(self.tokens):
            token = self.tokens[self.pos]
            self.pos += 1
            return token
        last_token = self.tokens[-1] if self.tokens else None
        line = last_token.code_position.line if last_token else 1
        col = (_get_token_end_position(last_token).column + 1) if last_token else 1
        return Token(TokenType.EOF, None, Position(line, col))
    
    def get_current_pos(self) -> Position:
        if self.pos < len(self.tokens):
            return self.tokens[self.pos].code_position
        last_token = self.tokens[-1] if self.tokens else None
        line = last_token.code_position.line if last_token else 1
        col = (_get_token_end_position(last_token).column + 1) if last_token else 1
        return Position(line, col)

# --- Test Class ---
class TestParser(unittest.TestCase):

    def assertNodesEqual(self, actual, expected, msg=None):
        if type(actual) != type(expected):
            self.fail(self._formatMessage(msg, f"Node types differ: {type(actual).__name__} vs {type(expected).__name__}"))

        if isinstance(actual, list) and isinstance(expected, list):
            self.assertEqual(len(actual), len(expected), 
                             self._formatMessage(msg, f"List length mismatch. Actual: {actual}, Expected: {expected}"))
            for i, (act_item, exp_item) in enumerate(zip(actual, expected)):
                self.assertNodesEqual(act_item, exp_item, 
                                      self._formatMessage(msg, f"Mismatch in list item {i}"))

        if is_dataclass(actual):
            for f in fields(actual):
                if f.name in ('start_position', 'end_position'):
                    continue

                actual_value = getattr(actual, f.name)
                expected_value = getattr(expected, f.name)

                # Special handling for lists of nodes/expressions
                if isinstance(actual_value, list) and isinstance(expected_value, list):
                    self.assertEqual(len(actual_value), len(expected_value), 
                                     self._formatMessage(msg, f"List length mismatch for field '{f.name}' in {type(actual).__name__}"))
                    for i, (act_item, exp_item) in enumerate(zip(actual_value, expected_value)):
                        self.assertNodesEqual(act_item, exp_item, 
                                              self._formatMessage(msg, f"Mismatch in list item {i} of field '{f.name}' in {type(actual).__name__}"))
                elif is_dataclass(actual_value) and is_dataclass(expected_value):
                    self.assertNodesEqual(actual_value, expected_value, 
                                          self._formatMessage(msg, f"Mismatch in nested dataclass field '{f.name}' in {type(actual).__name__}"))
                else:
                    # For not Node values
                    self.assertEqual(actual_value, expected_value,
                                     self._formatMessage(msg, f"Field '{f.name}' mismatch in {type(actual).__name__}: {actual_value!r} != {expected_value!r}"))
        else:
            self.assertEqual(actual, expected, msg)


    # Helper to create tokens with explicit position.
    def _token(self, type: TokenType, value: Any, line: int = 1, col: int = 1) -> Token:
        return Token(type, value, Position(line, col))

    def _create_parser(self, token_list: List[Token]) -> Parser:
        if not token_list or token_list[-1].type != TokenType.EOF:
            line, col = (1,1)
            if token_list:
                last_t = token_list[-1]
                line = last_t.code_position.line
                col = _get_token_end_position(last_t).column + 1
            token_list.append(Token(TokenType.EOF, None, Position(line, col)))

        mock_lexer = MockLexer(token_list)
        return Parser(mock_lexer)

    def test_empty_program(self):
        parser = self._create_parser([])
        program_node = parser.parse()
        
        expected_node = ProgramNode(
            start_position=Position(0,0),
            end_position=Position(0,0),
            statements=[]
        )
        self.assertNodesEqual(program_node, expected_node)

    # --- TYPE PARSING ---

    def test_parse_type_simple(self):
        types_to_test = [
            (TokenType.KEYWORD_INT, "int"), (TokenType.KEYWORD_VOID, "void"),
            (TokenType.KEYWORD_BOOL, "bool"), (TokenType.KEYWORD_STRING, "string"),
            (TokenType.KEYWORD_FOLDER, "Folder"), (TokenType.KEYWORD_FILE, "File"),
            (TokenType.KEYWORD_AUDIO, "Audio"), (TokenType.KEYWORD_FLOAT, "float")
        ]
        for token_type, type_name in types_to_test:
            with self.subTest(type=type_name):
                type_token = self._token(token_type, type_name)
                parser = self._create_parser([type_token])
                node = parser._parse_type()

                expected_node = TypeNode(
                    start_position=Position(0,0),
                    end_position=Position(0,0),
                    type_name=type_name
                )
                self.assertNodesEqual(node, expected_node)

    def test_parse_type_list(self):
        # List<string>
        list_kw = self._token(TokenType.KEYWORD_LIST, "List", 1, 1)
        op_lt = self._token(TokenType.OP_LT, "<", 1, 5)
        str_kw = self._token(TokenType.KEYWORD_STRING, "string", 1, 6)
        op_gt = self._token(TokenType.OP_GT, ">", 1, 12)
        tokens = [list_kw, op_lt, str_kw, op_gt]
        parser = self._create_parser(tokens)
        node = parser._parse_type()

        expected_child_node = TypeNode(
            start_position=Position(0,0), end_position=Position(0,0),
            type_name="string"
        )
        expected_node = ListTypeNode(
            start_position=Position(0,0), end_position=Position(0,0),
            type_name="List",
            child_type_node=expected_child_node
        )
        self.assertNodesEqual(node, expected_node)

    def test_parse_type_nested_list(self):
        # List<List<int>>
        list_kw1 = self._token(TokenType.KEYWORD_LIST, "List", 1, 1)
        op_lt1 = self._token(TokenType.OP_LT, "<", 1, 5)
        list_kw2 = self._token(TokenType.KEYWORD_LIST, "List", 1, 6)
        op_lt2 = self._token(TokenType.OP_LT, "<", 1, 10)
        int_kw = self._token(TokenType.KEYWORD_INT, "int", 1, 11)
        op_gt1 = self._token(TokenType.OP_GT, ">", 1, 14)
        op_gt2 = self._token(TokenType.OP_GT, ">", 1, 15)

        tokens = [list_kw1, op_lt1, list_kw2, op_lt2, int_kw, op_gt1, op_gt2]
        parser = self._create_parser(tokens)
        node = parser._parse_type()

        expected_innermost_child = TypeNode(
            start_position=Position(0,0), end_position=Position(0,0),
            type_name="int"
        )
        expected_middle_child = ListTypeNode(
            start_position=Position(0,0), end_position=Position(0,0),
            type_name="List",
            child_type_node=expected_innermost_child
        )
        expected_node = ListTypeNode(
            start_position=Position(0,0), end_position=Position(0,0),
            type_name="List",
            child_type_node=expected_middle_child
        )
        self.assertNodesEqual(node, expected_node)

    # ERRORS
    def test_parse_type_list_missing_gt(self):
        # List<int
        list_kw = self._token(TokenType.KEYWORD_LIST, "List", 1, 1)
        op_lt = self._token(TokenType.OP_LT, "<", 1, 5)
        int_kw = self._token(TokenType.KEYWORD_INT, "int", 1, 6)
        tokens = [list_kw, op_lt, int_kw]
        parser = self._create_parser(tokens)
        with self.assertRaisesRegex(UnexpectedTokenException, "Expected OP_GT but found EOF"):
            parser._parse_type()

    def test_parse_type_list_missing_child_type(self):
        # List<>
        list_kw = self._token(TokenType.KEYWORD_LIST, "List", 1, 1)
        op_lt = self._token(TokenType.OP_LT, "<", 1, 5)
        op_gt = self._token(TokenType.OP_GT, ">", 1, 6)
        tokens = [list_kw, op_lt, op_gt]
        parser = self._create_parser(tokens)
        with self.assertRaisesRegex(UnexpectedTokenException, "Expected type keyword but found OP_GT"):
            parser._parse_type()


    # --- VARIABLE DECLARATION ---
    def test_variable_declaration_int(self):
        # int x = 10;
        int_kw = self._token(TokenType.KEYWORD_INT, "int", 1, 1)
        ident_x = self._token(TokenType.IDENTIFIER, "x", 1, 5)
        op_assign = self._token(TokenType.OP_ASSIGN, "=", 1, 7)
        literal_10 = self._token(TokenType.LITERAL_INT, 10, 1, 9)
        semicolon = self._token(TokenType.SEMICOLON, ";", 1, 11)

        tokens = [int_kw, ident_x, op_assign, literal_10, semicolon]
        parser = self._create_parser(tokens)
        node = parser._parse_statement()

        expected_var_type = TypeNode(Position(0,0), Position(0,0), "int")
        expected_value = LiteralNode(Position(0,0), Position(0,0), 10)
        expected_node = VariableDeclarationNode(
            start_position=Position(0,0), end_position=Position(0,0),
            var_type=expected_var_type,
            identifier_name="x",
            value=expected_value
        )
        self.assertNodesEqual(node, expected_node)

    def test_variable_declaration_constructor_types(self):
        # File f = File("a.txt");
        test_cases = [
            (TokenType.KEYWORD_FILE, "File"),
            (TokenType.KEYWORD_FOLDER, "Folder"),
            (TokenType.KEYWORD_AUDIO, "Audio"),
        ]
        for type_kw_type, type_val in test_cases:
            with self.subTest(type=type_val):
                type_token = self._token(type_kw_type, type_val, 1, 1)
                ident_token = self._token(TokenType.IDENTIFIER, "obj", 1, 6)
                op_assign = self._token(TokenType.OP_ASSIGN, "=", 1, 10)
                constructor_type_token = self._token(type_kw_type, type_val, 1, 12)
                lparen = self._token(TokenType.LPAREN, "(", 1, 16)
                arg_token = self._token(TokenType.LITERAL_STRING, "path", 1, 17)
                rparen = self._token(TokenType.RPAREN, ")", 1, 23)
                semicolon = self._token(TokenType.SEMICOLON, ";", 1, 24)

                tokens = [
                    type_token, ident_token, op_assign, constructor_type_token, lparen,
                    arg_token, rparen, semicolon,
                ]
                parser = self._create_parser(tokens)
                node = parser._try_parse_variable_declaration()

                expected_var_type = TypeNode(Position(0,0), Position(0,0), type_val)
                expected_constructor_arg = LiteralNode(Position(0,0), Position(0,0), "path")
                expected_constructor_call = ConstructorCallNode(
                    start_position=Position(0,0), end_position=Position(0,0),
                    type_name=type_val,
                    arguments=[expected_constructor_arg]
                )
                expected_node = VariableDeclarationNode(
                    start_position=Position(0,0), end_position=Position(0,0),
                    var_type=expected_var_type,
                    identifier_name="obj",
                    value=expected_constructor_call
                )
                self.assertNodesEqual(node, expected_node)

    def test_list_type_declaration(self):
        # List<int> myList = [];
        list_kw_token = self._token(TokenType.KEYWORD_LIST, "List", 1, 1)
        op_lt = self._token(TokenType.OP_LT, "<", 1, 5)
        int_kw_token = self._token(TokenType.KEYWORD_INT, "int", 1, 6)
        op_gt = self._token(TokenType.OP_GT, ">", 1, 9)
        ident_token = self._token(TokenType.IDENTIFIER, "myList", 1, 11)
        op_assign = self._token(TokenType.OP_ASSIGN, "=", 1, 18)
        lbracket = self._token(TokenType.LBRACKET, "[", 1, 20)
        rbracket = self._token(TokenType.RBRACKET, "]", 1, 21)
        semicolon = self._token(TokenType.SEMICOLON, ";", 1, 22)

        tokens = [
            list_kw_token, op_lt, int_kw_token, op_gt,
            ident_token, op_assign,
            lbracket, rbracket, semicolon,
        ]
        parser = self._create_parser(tokens)
        node = parser._parse_statement()

        expected_child_type = TypeNode(Position(0,0), Position(0,0), "int")
        expected_list_type = ListTypeNode(Position(0,0), Position(0,0), "List", expected_child_type)
        expected_list_literal = ListLiteralNode(Position(0,0), Position(0,0), [])
        expected_node = VariableDeclarationNode(
            start_position=Position(0,0), end_position=Position(0,0),
            var_type=expected_list_type,
            identifier_name="myList",
            value=expected_list_literal
        )
        self.assertNodesEqual(node, expected_node)

    # ERRORS
    def test_missing_semicolon_after_var_decl(self):
        # int x = 10
        tokens = [
            self._token(TokenType.KEYWORD_INT, "int", 1, 1), self._token(TokenType.IDENTIFIER, "x", 1, 5),
            self._token(TokenType.OP_ASSIGN, "=", 1, 7), self._token(TokenType.LITERAL_INT, 10, 1, 9),
        ]
        parser = self._create_parser(tokens)
        with self.assertRaisesRegex(UnexpectedTokenException, "Expected SEMICOLON but found EOF"):
            parser._try_parse_variable_declaration()

    def test_var_decl_missing_identifier(self):
        # int = 10;
        tokens = [
            self._token(TokenType.KEYWORD_INT, "int", 1, 1),
            self._token(TokenType.OP_ASSIGN, "=", 1, 5), self._token(TokenType.LITERAL_INT, 10, 1, 7),
            self._token(TokenType.SEMICOLON, ";", 1, 9),
        ]
        parser = self._create_parser(tokens)
        with self.assertRaisesRegex(UnexpectedTokenException, "Expected IDENTIFIER but found OP_ASSIGN"):
            parser._try_parse_variable_declaration()

    def test_var_decl_missing_value(self):
        # int x =;
        tokens = [
            self._token(TokenType.KEYWORD_INT, "int", 1, 1), self._token(TokenType.IDENTIFIER, "x", 1, 5),
            self._token(TokenType.OP_ASSIGN, "=", 1, 7), self._token(TokenType.SEMICOLON, ";", 1, 8),
        ]
        parser = self._create_parser(tokens)
        with self.assertRaisesRegex(UnexpectedTokenException, "Expected start of a factor but found SEMICOLON"):
            parser._try_parse_variable_declaration()

    # --- ASSIGNMENT ---
    def test_assignment_statement(self):
        # count = 0;
        ident_count = self._token(TokenType.IDENTIFIER, "count", 1, 1)
        op_assign = self._token(TokenType.OP_ASSIGN, "=", 1, 7)
        literal_0 = self._token(TokenType.LITERAL_INT, 0, 1, 9)
        semicolon = self._token(TokenType.SEMICOLON, ";", 1, 10)

        tokens = [ident_count, op_assign, literal_0, semicolon]
        parser = self._create_parser(tokens)
        node = parser._parse_statement()

        expected_identifier_node = IdentifierNode(Position(0,0), Position(0,0), "count")
        expected_value_node = LiteralNode(Position(0,0), Position(0,0), 0)
        expected_node = AssignmentNode(
            start_position=Position(0,0), end_position=Position(0,0),
            identifier=expected_identifier_node,
            value=expected_value_node
        )
        self.assertNodesEqual(node, expected_node)

    def test_assignment_to_member_access(self):
        # obj.property = 10;
        ident_obj = self._token(TokenType.IDENTIFIER, "obj", 1, 1)
        dot = self._token(TokenType.DOT, ".", 1, 4)
        ident_prop = self._token(TokenType.IDENTIFIER, "property", 1, 5)
        op_assign = self._token(TokenType.OP_ASSIGN, "=", 1, 14)
        literal_10 = self._token(TokenType.LITERAL_INT, 10, 1, 16)
        semicolon = self._token(TokenType.SEMICOLON, ";", 1, 18)

        tokens = [ident_obj, dot, ident_prop, op_assign, literal_10, semicolon]
        parser = self._create_parser(tokens)
        node = parser._parse_statement()

        expected_obj_node = IdentifierNode(Position(0,0), Position(0,0), "obj")
        expected_lhs = MemberAccessNode(
            start_position=Position(0,0), end_position=Position(0,0),
            object_expr=expected_obj_node,
            member_name="property"
        )
        expected_value = LiteralNode(Position(0,0), Position(0,0), 10)
        expected_node = AssignmentNode(
            start_position=Position(0,0), end_position=Position(0,0),
            identifier=expected_lhs,
            value=expected_value
        )
        self.assertNodesEqual(node, expected_node)

    # ERROR
    def test_assignment_missing_semicolon(self):
        tokens = [
            self._token(TokenType.IDENTIFIER, "count", 1, 1), self._token(TokenType.OP_ASSIGN, "=", 1, 7),
            self._token(TokenType.LITERAL_INT, 0, 1, 9),
        ]
        parser = self._create_parser(tokens)
        with self.assertRaisesRegex(UnexpectedTokenException, "Expected SEMICOLON but found EOF"):
            parser._try_parse_identifier_driven_statement()

    # FUNCTION CALLS
    def test_function_call_statement(self):
        # print("hello");
        ident_print = self._token(TokenType.IDENTIFIER, "print", 1, 1)
        lparen = self._token(TokenType.LPAREN, "(", 1, 6)
        literal_hello = self._token(TokenType.LITERAL_STRING, "hello", 1, 7)
        rparen = self._token(TokenType.RPAREN, ")", 1, 14)
        semicolon = self._token(TokenType.SEMICOLON, ";", 1, 15)

        tokens = [ident_print, lparen, literal_hello, rparen, semicolon]
        parser = self._create_parser(tokens)
        node = parser._parse_statement()

        expected_function_name = IdentifierNode(Position(0,0), Position(0,0), "print")
        expected_argument = LiteralNode(Position(0,0), Position(0,0), "hello")
        expected_call_expr = FunctionCallNode(
            start_position=Position(0,0), end_position=Position(0,0),
            function_name=expected_function_name,
            arguments=[expected_argument]
        )
        expected_node = FunctionCallStatementNode(
            start_position=Position(0,0), end_position=Position(0,0),
            call_expression=expected_call_expr
        )
        self.assertNodesEqual(node, expected_node)

    def test_function_call_multiple_args_expression(self):
        # add(1, 2)
        ident_add = self._token(TokenType.IDENTIFIER, "add", 1, 1)
        lparen = self._token(TokenType.LPAREN, "(", 1, 4)
        literal_1 = self._token(TokenType.LITERAL_INT, 1, 1, 5)
        comma = self._token(TokenType.COMMA, ",", 1, 6)
        literal_2 = self._token(TokenType.LITERAL_INT, 2, 1, 8)
        rparen = self._token(TokenType.RPAREN, ")", 1, 9)

        tokens = [ident_add, lparen, literal_1, comma, literal_2, rparen]
        parser = self._create_parser(tokens)
        node = parser._parse_expression()

        expected_function_name = IdentifierNode(Position(0,0), Position(0,0), "add")
        expected_arg1 = LiteralNode(Position(0,0), Position(0,0), 1)
        expected_arg2 = LiteralNode(Position(0,0), Position(0,0), 2)
        expected_node = FunctionCallNode(
            start_position=Position(0,0), end_position=Position(0,0),
            function_name=expected_function_name,
            arguments=[expected_arg1, expected_arg2]
        )
        self.assertNodesEqual(node, expected_node)

    # ERRORS
    def test_function_call_missing_rparen(self):
        #print("hello";
        tokens = [
            self._token(TokenType.IDENTIFIER, "print", 1, 1), self._token(TokenType.LPAREN, "(", 1, 6),
            self._token(TokenType.LITERAL_STRING, "hello", 1, 7),
            self._token(TokenType.SEMICOLON, ";", 1, 14),
        ]
        parser = self._create_parser(tokens)
        with self.assertRaisesRegex(UnexpectedTokenException, "Expected RPAREN but found SEMICOLON"):
            parser._parse_statement()

    def test_function_call_missing_comma_in_args(self):
        # add(1 2);
        tokens = [
            self._token(TokenType.IDENTIFIER, "add", 1, 1), self._token(TokenType.LPAREN, "(", 1, 4),
            self._token(TokenType.LITERAL_INT, 1, 1, 5),
            self._token(TokenType.LITERAL_INT, 2, 1, 7),
            self._token(TokenType.RPAREN, ")", 1, 8), self._token(TokenType.SEMICOLON, ";", 1, 9),
        ]
        parser = self._create_parser(tokens)
        with self.assertRaisesRegex(UnexpectedTokenException, "Expected RPAREN but found LITERAL_INT"):
            parser._parse_statement()

    # --- EXPRESSIONS ---
    def test_expression_statement(self):
        # 1 + 2;
        literal_1 = self._token(TokenType.LITERAL_INT, 1, 1, 1)
        op_plus = self._token(TokenType.OP_PLUS, "+", 1, 3)
        literal_2 = self._token(TokenType.LITERAL_INT, 2, 1, 5)
        semicolon = self._token(TokenType.SEMICOLON, ";", 1, 6)

        tokens = [literal_1, op_plus, literal_2, semicolon]
        parser = self._create_parser(tokens)
        node = parser._parse_statement()

        expected_left = LiteralNode(Position(0,0), Position(0,0), 1)
        expected_right = LiteralNode(Position(0,0), Position(0,0), 2)
        expected_expression = AddNode(
            start_position=Position(0,0), end_position=Position(0,0),
            left=expected_left,
            right=expected_right
        )
        expected_node = ExpressionStatementNode(
            start_position=Position(0,0), end_position=Position(0,0),
            expression=expected_expression
        )
        self.assertNodesEqual(node, expected_node)

    def test_complex_expression_precedence(self):
        # 2 + 3 * 4;
        literal_2 = self._token(TokenType.LITERAL_INT, 2, 1, 1)
        op_plus = self._token(TokenType.OP_PLUS, "+", 1, 3)
        literal_3 = self._token(TokenType.LITERAL_INT, 3, 1, 5)
        op_multiply = self._token(TokenType.OP_MULTIPLY, "*", 1, 7)
        literal_4 = self._token(TokenType.LITERAL_INT, 4, 1, 9)
        semicolon = self._token(TokenType.SEMICOLON, ";", 1, 10)

        tokens = [literal_2, op_plus, literal_3, op_multiply, literal_4, semicolon]
        parser = self._create_parser(tokens)
        node = parser._parse_statement()

        expected_left_add = LiteralNode(Position(0,0), Position(0,0), 2)
        expected_left_multiply = LiteralNode(Position(0,0), Position(0,0), 3)
        expected_right_multiply = LiteralNode(Position(0,0), Position(0,0), 4)

        expected_multiply_node = MultiplyNode(
            start_position=Position(0,0), end_position=Position(0,0),
            left=expected_left_multiply,
            right=expected_right_multiply
        )
        expected_add_node = AddNode(
            start_position=Position(0,0), end_position=Position(0,0),
            left=expected_left_add,
            right=expected_multiply_node
        )
        expected_node = ExpressionStatementNode(
            start_position=Position(0,0), end_position=Position(0,0),
            expression=expected_add_node
        )
        self.assertNodesEqual(node, expected_node)

    # --- FUNCTION DEFINITION ---
    def test_simple_function_definition_void_noreturn(self):
        # func void doNothing() { return; }
        func_kw = self._token(TokenType.KEYWORD_FUNC, "func", 1, 1)
        void_kw = self._token(TokenType.KEYWORD_VOID, "void", 1, 6)
        ident_doNothing = self._token(TokenType.IDENTIFIER, "doNothing", 1, 11)
        lparen = self._token(TokenType.LPAREN, "(", 1, 20)
        rparen = self._token(TokenType.RPAREN, ")", 1, 21)
        lbrace = self._token(TokenType.LBRACE, "{", 1, 23)
        return_kw = self._token(TokenType.KEYWORD_RETURN, "return", 1, 25)
        semicolon = self._token(TokenType.SEMICOLON, ";", 1, 31)
        rbrace = self._token(TokenType.RBRACE, "}", 1, 33)

        tokens = [func_kw, void_kw, ident_doNothing, lparen, rparen,
                  lbrace, return_kw, semicolon, rbrace]
        parser = self._create_parser(tokens)
        program_node = parser.parse()
        self.assertEqual(len(program_node.statements), 1)
        node = program_node.statements[0]

        expected_return_stmt = ReturnStatementNode(
            start_position=Position(0,0), end_position=Position(0,0),
            value=None
        )
        expected_body = CodeBlockNode(
            start_position=Position(0,0), end_position=Position(0,0),
            statements=[expected_return_stmt]
        )
        expected_return_type = TypeNode(Position(0,0), Position(0,0), "void")
        expected_node = FunctionDefinitionNode(
            start_position=Position(0,0), end_position=Position(0,0),
            return_type=expected_return_type,
            identifier_name="doNothing",
            parameters=[],
            body=expected_body
        )
        self.assertNodesEqual(node, expected_node)

    def test_function_definition_with_parameters(self):
        # func int add(int a, int b) { return a + b; }
        func_kw = self._token(TokenType.KEYWORD_FUNC, "func", 1, 1)
        int_ret_type = self._token(TokenType.KEYWORD_INT, "int", 1, 6)
        ident_add = self._token(TokenType.IDENTIFIER, "add", 1, 10)
        lparen1 = self._token(TokenType.LPAREN, "(", 1, 13)
        int_type1 = self._token(TokenType.KEYWORD_INT, "int", 1, 14)
        param_a = self._token(TokenType.IDENTIFIER, "a", 1, 18)
        comma = self._token(TokenType.COMMA, ",", 1, 19)
        int_type2 = self._token(TokenType.KEYWORD_INT, "int", 1, 21)
        param_b = self._token(TokenType.IDENTIFIER, "b", 1, 25)
        rparen1 = self._token(TokenType.RPAREN, ")", 1, 26)
        lbrace = self._token(TokenType.LBRACE, "{", 1, 28)
        return_kw = self._token(TokenType.KEYWORD_RETURN, "return", 1, 30)
        ident_a = self._token(TokenType.IDENTIFIER, "a", 1, 37)
        op_plus = self._token(TokenType.OP_PLUS, "+", 1, 39)
        ident_b = self._token(TokenType.IDENTIFIER, "b", 1, 41)
        semicolon = self._token(TokenType.SEMICOLON, ";", 1, 42)
        rbrace = self._token(TokenType.RBRACE, "}", 1, 44)

        tokens = [
            func_kw, int_ret_type, ident_add, lparen1,
            int_type1, param_a, comma, int_type2, param_b,
            rparen1, lbrace, return_kw, ident_a, op_plus, ident_b, semicolon, rbrace
        ]
        parser = self._create_parser(tokens)
        node = parser._try_parse_function_definition()

        expected_param_a_type = TypeNode(Position(0,0), Position(0,0), "int")
        expected_param_a = ParameterNode(Position(0,0), Position(0,0), expected_param_a_type, "a")
        expected_param_b_type = TypeNode(Position(0,0), Position(0,0), "int")
        expected_param_b = ParameterNode(Position(0,0), Position(0,0), expected_param_b_type, "b")

        expected_ident_a_expr = IdentifierNode(Position(0,0), Position(0,0), "a")
        expected_ident_b_expr = IdentifierNode(Position(0,0), Position(0,0), "b")
        expected_add_expr = AddNode(
            start_position=Position(0,0), end_position=Position(0,0),
            left=expected_ident_a_expr,
            right=expected_ident_b_expr
        )
        expected_return_stmt = ReturnStatementNode(
            start_position=Position(0,0), end_position=Position(0,0),
            value=expected_add_expr
        )
        expected_body = CodeBlockNode(
            start_position=Position(0,0), end_position=Position(0,0),
            statements=[expected_return_stmt]
        )
        expected_return_type = TypeNode(Position(0,0), Position(0,0), "int")
        expected_node = FunctionDefinitionNode(
            start_position=Position(0,0), end_position=Position(0,0),
            return_type=expected_return_type,
            identifier_name="add",
            parameters=[expected_param_a, expected_param_b],
            body=expected_body
        )
        self.assertNodesEqual(node, expected_node)

    def test_function_body_with_statements(self):
        # { int x = 5; return x; }
        lbrace = self._token(TokenType.LBRACE, "{", 1, 1)
        int_kw = self._token(TokenType.KEYWORD_INT, "int", 1, 3)
        ident_x1 = self._token(TokenType.IDENTIFIER, "x", 1, 7)
        op_assign = self._token(TokenType.OP_ASSIGN, "=", 1, 9)
        literal_5 = self._token(TokenType.LITERAL_INT, 5, 1, 11)
        semicolon1 = self._token(TokenType.SEMICOLON, ";", 1, 12)
        return_kw = self._token(TokenType.KEYWORD_RETURN, "return", 1, 14)
        ident_x2 = self._token(TokenType.IDENTIFIER, "x", 1, 21)
        semicolon2 = self._token(TokenType.SEMICOLON, ";", 1, 22)
        rbrace = self._token(TokenType.RBRACE, "}", 1, 24)

        tokens = [
            lbrace, int_kw, ident_x1, op_assign, literal_5, semicolon1,
            return_kw, ident_x2, semicolon2, rbrace
        ]
        parser = self._create_parser(tokens)
        node = parser._parse_code_block()

        expected_int_type = TypeNode(Position(0,0), Position(0,0), "int")
        expected_literal_5 = LiteralNode(Position(0,0), Position(0,0), 5)
        expected_var_decl = VariableDeclarationNode(
            start_position=Position(0,0), end_position=Position(0,0),
            var_type=expected_int_type,
            identifier_name="x",
            value=expected_literal_5
        )
        expected_ident_x2 = IdentifierNode(Position(0,0), Position(0,0), "x")
        expected_return_stmt = ReturnStatementNode(
            start_position=Position(0,0), end_position=Position(0,0),
            value=expected_ident_x2
        )
        expected_node = CodeBlockNode(
            start_position=Position(0,0), end_position=Position(0,0),
            statements=[expected_var_decl, expected_return_stmt]
        )
        self.assertNodesEqual(node, expected_node)

    def test_parameter_list_multiple(self):
        # string s, bool b
        self.maxDiff = None
        str_tok = self._token(TokenType.KEYWORD_STRING, "string", 1, 1)
        s_id = self._token(TokenType.IDENTIFIER, "s", 1, 8)
        comma = self._token(TokenType.COMMA, ",", 1, 9)
        bool_tok = self._token(TokenType.KEYWORD_BOOL, "bool", 1, 11)
        b_id = self._token(TokenType.IDENTIFIER, "b", 1, 16)
        
        parser = self._create_parser([
            str_tok, s_id, comma, bool_tok, b_id
        ])
        params = parser._parse_parameter_list()

        expected_str_type = TypeNode(Position(1,1), Position(1,1), "string")
        expected_param_s = ParameterNode(Position(1,1), Position(1,8), expected_str_type, "s")
        expected_bool_type = TypeNode(Position(1,11), Position(1,11), "bool")
        expected_param_b = ParameterNode(Position(1,11), Position(1,16), expected_bool_type, "b")

        self.assertNodesEqual(params, [expected_param_s, expected_param_b])

    def test_malformed_function_no_rbrace(self):
        # func void test() { return;
        tokens = [
            self._token(TokenType.KEYWORD_FUNC, "func", 1, 1), self._token(TokenType.KEYWORD_VOID, "void", 1, 6),
            self._token(TokenType.IDENTIFIER, "test", 1, 11),
            self._token(TokenType.LPAREN, "(", 1, 15), self._token(TokenType.RPAREN, ")", 1, 16),
            self._token(TokenType.LBRACE, "{", 1, 18),
            self._token(TokenType.KEYWORD_RETURN, "return", 1, 20), self._token(TokenType.SEMICOLON, ";", 1, 26),
        ]
        parser = self._create_parser(tokens)
        with self.assertRaisesRegex(UnexpectedTokenException, "Unexpected Token EOF"):
            parser.parse()

    def test_function_def_missing_return_type(self):
        # func myFunc
        tokens = [
            self._token(TokenType.KEYWORD_FUNC, "func", 1, 1),
            self._token(TokenType.IDENTIFIER, "myFunc", 1, 6),
        ]
        parser = self._create_parser(tokens)
        with self.assertRaisesRegex(UnexpectedTokenException, "Expected type keyword but found IDENTIFIER"):
            parser._try_parse_function_definition()

    # --- IF/WHILE STATEMENTS ---
    def test_if_statement(self):
        if_kw = self._token(TokenType.KEYWORD_IF, "if", 1, 1)
        lparen = self._token(TokenType.LPAREN, "(", 1, 4)
        true_kw = self._token(TokenType.KEYWORD_TRUE, "true", 1, 5)
        rparen = self._token(TokenType.RPAREN, ")", 1, 9)
        lbrace = self._token(TokenType.LBRACE, "{", 1, 11)
        ident_x = self._token(TokenType.IDENTIFIER, "x", 1, 13)
        op_assign = self._token(TokenType.OP_ASSIGN, "=", 1, 15)
        literal_1 = self._token(TokenType.LITERAL_INT, 1, 1, 17)
        semicolon = self._token(TokenType.SEMICOLON, ";", 1, 18)
        rbrace = self._token(TokenType.RBRACE, "}", 1, 20)

        tokens = [if_kw, lparen, true_kw, rparen, lbrace, ident_x, op_assign, literal_1, semicolon, rbrace]
        parser = self._create_parser(tokens)
        node = parser._try_parse_if_statement()
        
        expected_condition = LiteralNode(Position(0,0), Position(0,0), "true")
        expected_assign_ident = IdentifierNode(Position(0,0), Position(0,0), "x")
        expected_assign_value = LiteralNode(Position(0,0), Position(0,0), 1)
        expected_assign_stmt = AssignmentNode(
            start_position=Position(0,0), end_position=Position(0,0),
            identifier=expected_assign_ident,
            value=expected_assign_value
        )
        expected_if_block = CodeBlockNode(
            start_position=Position(0,0), end_position=Position(0,0),
            statements=[expected_assign_stmt]
        )
        expected_node = IfStatementNode(
            start_position=Position(0,0), end_position=Position(0,0),
            condition=expected_condition,
            if_block=expected_if_block,
            else_block=None
        )
        self.assertNodesEqual(node, expected_node)

    def test_if_else_statement(self):
        # if (false) {} else { y = 2; }
        if_kw = self._token(TokenType.KEYWORD_IF, "if", 1, 1)
        lparen1 = self._token(TokenType.LPAREN, "(", 1, 4)
        false_kw = self._token(TokenType.KEYWORD_FALSE, "false", 1, 5)
        rparen1 = self._token(TokenType.RPAREN, ")", 1, 10)
        lbrace1 = self._token(TokenType.LBRACE, "{", 1, 12)
        rbrace1 = self._token(TokenType.RBRACE, "}", 1, 13)
        else_kw = self._token(TokenType.KEYWORD_ELSE, "else", 1, 15)
        lbrace2 = self._token(TokenType.LBRACE, "{", 1, 20)
        ident_y = self._token(TokenType.IDENTIFIER, "y", 1, 22)
        op_assign = self._token(TokenType.OP_ASSIGN, "=", 1, 24)
        literal_2 = self._token(TokenType.LITERAL_INT, 2, 1, 26)
        semicolon = self._token(TokenType.SEMICOLON, ";", 1, 27)
        rbrace2 = self._token(TokenType.RBRACE, "}", 1, 29)

        tokens = [
            if_kw, lparen1, false_kw, rparen1, lbrace1, rbrace1,
            else_kw, lbrace2, ident_y, op_assign, literal_2, semicolon, rbrace2
        ]
        parser = self._create_parser(tokens)
        node = parser._try_parse_if_statement()

        expected_condition = LiteralNode(Position(0,0), Position(0,0), "false")
        expected_if_block = CodeBlockNode(Position(0,0), Position(0,0), [])
        
        expected_assign_ident = IdentifierNode(Position(0,0), Position(0,0), "y")
        expected_assign_value = LiteralNode(Position(0,0), Position(0,0), 2)
        expected_assign_stmt = AssignmentNode(
            start_position=Position(0,0), end_position=Position(0,0),
            identifier=expected_assign_ident,
            value=expected_assign_value
        )
        expected_else_block = CodeBlockNode(
            start_position=Position(0,0), end_position=Position(0,0),
            statements=[expected_assign_stmt]
        )
        expected_node = IfStatementNode(
            start_position=Position(0,0), end_position=Position(0,0),
            condition=expected_condition,
            if_block=expected_if_block,
            else_block=expected_else_block
        )
        self.assertNodesEqual(node, expected_node)

    def test_while_loop(self):
        # while (i < 10) { i = i + 1; }
        while_kw = self._token(TokenType.KEYWORD_WHILE, "while", 1, 1)
        lparen = self._token(TokenType.LPAREN, "(", 1, 7)
        ident_i1 = self._token(TokenType.IDENTIFIER, "i", 1, 8)
        op_lt = self._token(TokenType.OP_LT, "<", 1, 10)
        literal_10 = self._token(TokenType.LITERAL_INT, 10, 1, 12)
        rparen = self._token(TokenType.RPAREN, ")", 1, 14)
        lbrace = self._token(TokenType.LBRACE, "{", 1, 16)
        ident_i2 = self._token(TokenType.IDENTIFIER, "i", 1, 18)
        op_assign = self._token(TokenType.OP_ASSIGN, "=", 1, 20)
        ident_i3 = self._token(TokenType.IDENTIFIER, "i", 1, 22)
        op_plus = self._token(TokenType.OP_PLUS, "+", 1, 24)
        literal_1 = self._token(TokenType.LITERAL_INT, 1, 1, 26)
        semicolon = self._token(TokenType.SEMICOLON, ";", 1, 27)
        rbrace = self._token(TokenType.RBRACE, "}", 1, 29)

        tokens = [
            while_kw, lparen, ident_i1, op_lt, literal_10, rparen,
            lbrace, ident_i2, op_assign, ident_i3, op_plus, literal_1, semicolon, rbrace
        ]
        parser = self._create_parser(tokens)
        node = parser._try_parse_while_loop()

        expected_cond_left = IdentifierNode(Position(0,0), Position(0,0), "i")
        expected_cond_right = LiteralNode(Position(0,0), Position(0,0), 10)
        expected_condition = LessThanNode(
            start_position=Position(0,0), end_position=Position(0,0),
            left=expected_cond_left,
            right=expected_cond_right
        )

        expected_assign_ident = IdentifierNode(Position(0,0), Position(0,0), "i")
        expected_add_left = IdentifierNode(Position(0,0), Position(0,0), "i")
        expected_add_right = LiteralNode(Position(0,0), Position(0,0), 1)
        expected_add_expr = AddNode(
            start_position=Position(0,0), end_position=Position(0,0),
            left=expected_add_left,
            right=expected_add_right
        )
        expected_assign_stmt = AssignmentNode(
            start_position=Position(0,0), end_position=Position(0,0),
            identifier=expected_assign_ident,
            value=expected_add_expr
        )
        expected_body = CodeBlockNode(
            start_position=Position(0,0), end_position=Position(0,0),
            statements=[expected_assign_stmt]
        )
        expected_node = WhileLoopNode(
            start_position=Position(0,0), end_position=Position(0,0),
            condition=expected_condition,
            body=expected_body
        )
        self.assertNodesEqual(node, expected_node)

    # ERRORS
    def test_if_missing_condition_paren(self):
        # if true
        tokens = [
            self._token(TokenType.KEYWORD_IF, "if", 1, 1),
            self._token(TokenType.KEYWORD_TRUE, "true", 1, 4),
        ]
        parser = self._create_parser(tokens)
        with self.assertRaisesRegex(UnexpectedTokenException, "Expected LPAREN but found KEYWORD_TRUE"):
            parser._try_parse_if_statement()

    def test_if_missing_if_block(self):
        # if(true) else
        tokens = [
            self._token(TokenType.KEYWORD_IF, "if", 1, 1), self._token(TokenType.LPAREN, "(", 1, 4),
            self._token(TokenType.KEYWORD_TRUE, "true", 1, 5), self._token(TokenType.RPAREN, ")", 1, 9),
            self._token(TokenType.KEYWORD_ELSE, "else", 1, 11),
        ]
        parser = self._create_parser(tokens)
        with self.assertRaisesRegex(UnexpectedTokenException, "Expected LBRACE but found KEYWORD_ELSE"):
            parser._try_parse_if_statement()

    def test_while_missing_condition_paren(self):
        # while true
        tokens = [
            self._token(TokenType.KEYWORD_WHILE, "while", 1, 1),
            self._token(TokenType.KEYWORD_TRUE, "true", 1, 7),
        ]
        parser = self._create_parser(tokens)
        with self.assertRaisesRegex(UnexpectedTokenException, "Expected LPAREN but found KEYWORD_TRUE"):
            parser._try_parse_while_loop()

    def test_while_missing_body_lbrace(self):
        # while (true);
        tokens = [
            self._token(TokenType.KEYWORD_WHILE, "while", 1, 1), self._token(TokenType.LPAREN, "(", 1, 7),
            self._token(TokenType.KEYWORD_TRUE, "true", 1, 8), self._token(TokenType.RPAREN, ")", 1, 12),
            self._token(TokenType.SEMICOLON, ";", 1, 14),
        ]
        parser = self._create_parser(tokens)
        with self.assertRaisesRegex(UnexpectedTokenException, "Expected LBRACE but found SEMICOLON"):
            parser._try_parse_while_loop()


    # --- FACTORS ---
    def test_factor_literals(self):
        test_cases = [
            (TokenType.LITERAL_INT, 123),
            (TokenType.LITERAL_FLOAT, 1.23),
            (TokenType.LITERAL_STRING, "hello world"),
            (TokenType.KEYWORD_TRUE, True),
            (TokenType.KEYWORD_FALSE, False),
            (TokenType.KEYWORD_NULL, None),
        ]
        for token_type, node_value in test_cases:
            with self.subTest(literal=node_value):
                tok = self._token(token_type, node_value)
                parser = self._create_parser([tok])
                node = parser._parse_factor()
                
                expected_node = LiteralNode(
                    start_position=Position(0,0), end_position=Position(0,0),
                    value=node_value
                )
                self.assertNodesEqual(node, expected_node)

    def test_factor_list_literal_nested(self):
        # [[1], [2,3]]
        # (1,1) (1,2)(1,3) (1,4) (1,5) (1,6)(1,7)(1,8)(1,9) (1,10)
        lbracket1 = self._token(TokenType.LBRACKET, "[", 1, 1)
        lbracket2 = self._token(TokenType.LBRACKET, "[", 1, 2)
        literal1 = self._token(TokenType.LITERAL_INT, 1, 1, 3)
        rbracket2 = self._token(TokenType.RBRACKET, "]", 1, 4)
        comma1 = self._token(TokenType.COMMA, ",", 1, 5)
        lbracket3 = self._token(TokenType.LBRACKET, "[", 1, 6)
        literal2 = self._token(TokenType.LITERAL_INT, 2, 1, 7)
        comma2 = self._token(TokenType.COMMA, ",", 1, 8)
        literal3 = self._token(TokenType.LITERAL_INT, 3, 1, 9)
        rbracket3 = self._token(TokenType.RBRACKET, "]", 1, 10)
        rbracket1 = self._token(TokenType.RBRACKET, "]", 1, 11)

        tokens = [
            lbracket1, lbracket2, literal1, rbracket2, comma1,
            lbracket3, literal2, comma2, literal3, rbracket3, rbracket1
        ]
        parser = self._create_parser(tokens)
        node = parser._parse_factor()

        expected_literal1 = LiteralNode(Position(0,0), Position(0,0), 1)
        expected_list1 = ListLiteralNode(Position(0,0), Position(0,0), [expected_literal1])
        
        expected_literal2 = LiteralNode(Position(0,0), Position(0,0), 2)
        expected_literal3 = LiteralNode(Position(0,0), Position(0,0), 3)
        expected_list2 = ListLiteralNode(Position(0,0), Position(0,0), [expected_literal2, expected_literal3])

        expected_node = ListLiteralNode(
            start_position=Position(0,0), end_position=Position(0,0),
            elements=[expected_list1, expected_list2]
        )
        self.assertNodesEqual(node, expected_node)

    def test_factor_constructor_call(self):
        # File("config.txt")
        file_kw = self._token(TokenType.KEYWORD_FILE, "File", 1, 1)
        lparen = self._token(TokenType.LPAREN, "(", 1, 5)
        arg_tok = self._token(TokenType.LITERAL_STRING, "config.txt", 1, 6)
        rparen = self._token(TokenType.RPAREN, ")", 1, 18)

        tokens = [file_kw, lparen, arg_tok, rparen]
        parser = self._create_parser(tokens)
        node = parser._parse_factor()

        expected_arg = LiteralNode(Position(0,0), Position(0,0), "config.txt")
        expected_node = ConstructorCallNode(
            start_position=Position(0,0), end_position=Position(0,0),
            type_name="File",
            arguments=[expected_arg]
        )
        self.assertNodesEqual(node, expected_node)

    def test_factor_member_access_property(self):
        # myObject.property
        obj_id = self._token(TokenType.IDENTIFIER, "myObject", 1, 1)
        dot = self._token(TokenType.DOT, ".", 1, 9)
        prop_id = self._token(TokenType.IDENTIFIER, "property", 1, 10)
        tokens = [obj_id, dot, prop_id]
        parser = self._create_parser(tokens)
        node = parser._parse_factor()

        expected_obj_expr = IdentifierNode(Position(0,0), Position(0,0), "myObject")
        expected_node = MemberAccessNode(
            start_position=Position(0,0), end_position=Position(0,0),
            object_expr=expected_obj_expr,
            member_name="property"
        )
        self.assertNodesEqual(node, expected_node)

    def test_factor_member_access_method_call_no_args(self):
        # myObject.doSomething()
        obj_id = self._token(TokenType.IDENTIFIER, "myObject", 1, 1)
        dot = self._token(TokenType.DOT, ".", 1, 9)
        method_id = self._token(TokenType.IDENTIFIER, "doSomething", 1, 10)
        lparen = self._token(TokenType.LPAREN, "(", 1, 21)
        rparen = self._token(TokenType.RPAREN, ")", 1, 22)

        tokens = [obj_id, dot, method_id, lparen, rparen]
        parser = self._create_parser(tokens)
        node = parser._parse_factor()

        expected_obj_expr = IdentifierNode(Position(0,0), Position(0,0), "myObject")
        expected_member_access_expr = MemberAccessNode(
            start_position=Position(0,0), end_position=Position(0,0),
            object_expr=expected_obj_expr,
            member_name="doSomething"
        )
        expected_node = FunctionCallNode(
            start_position=Position(0,0), end_position=Position(0,0),
            function_name=expected_member_access_expr,
            arguments=[]
        )
        self.assertNodesEqual(node, expected_node)

    def test_chained_member_access(self):
        # obj.prop1.prop2
        obj_id = self._token(TokenType.IDENTIFIER, "obj", 1, 1)
        dot1 = self._token(TokenType.DOT, ".", 1, 4)
        prop1_id = self._token(TokenType.IDENTIFIER, "prop1", 1, 5)
        dot2 = self._token(TokenType.DOT, ".", 1, 10)
        prop2_id = self._token(TokenType.IDENTIFIER, "prop2", 1, 11)
        
        tokens = [obj_id, dot1, prop1_id, dot2, prop2_id]
        parser = self._create_parser(tokens)
        node = parser._parse_factor()

        expected_obj_expr = IdentifierNode(Position(0,0), Position(0,0), "obj")
        expected_prop1_expr = MemberAccessNode(
            start_position=Position(0,0), end_position=Position(0,0),
            object_expr=expected_obj_expr,
            member_name="prop1"
        )
        expected_node = MemberAccessNode(
            start_position=Position(0,0), end_position=Position(0,0),
            object_expr=expected_prop1_expr,
            member_name="prop2"
        )
        self.assertNodesEqual(node, expected_node)

    # ERRORS
    def test_member_access_missing_member_name(self):
        # obj.
        tokens = [
            self._token(TokenType.IDENTIFIER, "obj", 1, 1), self._token(TokenType.DOT, ".", 1, 4),
        ]
        parser = self._create_parser(tokens)
        with self.assertRaisesRegex(UnexpectedTokenException, "Expected IDENTIFIER but found EOF"):
            parser._parse_factor()

    def test_malformed_constructor_call_no_paren(self):
        # File "test.txt"; (missing parentheses)
        file_kw = self._token(TokenType.KEYWORD_FILE, "File", 1, 1)
        string_literal = self._token(TokenType.LITERAL_STRING, "test.txt", 1, 6)
        semicolon = self._token(TokenType.SEMICOLON, ";", 1, 16)
        tokens = [file_kw, string_literal, semicolon]
        parser = self._create_parser(tokens)
        with self.assertRaisesRegex(UnexpectedTokenException, "Expected '\\(' after constructor keyword but found LITERAL_STRING"):
            parser._parse_expression()


if __name__ == '__main__':
    unittest.main(argv=['first-arg-is-ignored'], exit=False)