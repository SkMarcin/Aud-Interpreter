import unittest
from typing import List, Any

from source.utils import ParserException, Position
from source.tokens import TokenType, Token
from source.parser import Parser
from source.nodes import *

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
        col = (last_token.code_position.column + (len(str(last_token.value)) if last_token and last_token.value is not None else 1)) if last_token else 1
        return Token(TokenType.EOF, None, Position(line, col))

# --- Test Class ---
class TestParser(unittest.TestCase):

    def _create_parser(self, token_list: List[Token]) -> Parser:
        if not token_list or token_list[-1].type != TokenType.EOF:
            line, col = (1,1)
            if token_list:
                last_t = token_list[-1]
                line = last_t.code_position.line
                col = last_t.code_position.column + (len(str(last_t.value)) if last_t.value is not None else 1)
            token_list.append(Token(TokenType.EOF, None, Position(line, col)))

        mock_lexer = MockLexer(token_list)
        return Parser(mock_lexer)

    # Helper to create tokens with default position if not specified
    def _token(self, type: TokenType, value: Any, line: int = 1, col: int = 1) -> Token:
        return Token(type, value, Position(line, col))

    def test_empty_program(self):
        parser = self._create_parser([])
        program_node = parser.parse()
        self.assertIsInstance(program_node, ProgramNode)
        self.assertEqual(len(program_node.statements), 0)

    # --- TYPE PARSING ---

    def test_parse_type_simple(self):
        types_to_test = [
            (TokenType.KEYWORD_INT, "int"), (TokenType.KEYWORD_VOID, "void"),
            (TokenType.KEYWORD_BOOL, "bool"), (TokenType.KEYWORD_STRING, "string"),
            (TokenType.KEYWORD_FOLDER, "Folder"), (TokenType.KEYWORD_FILE, "File"),
            (TokenType.KEYWORD_AUDIO, "Audio")
        ]
        for token_type, token_val in types_to_test:
            with self.subTest(type=token_val):
                type_token = self._token(token_type, token_val)
                parser = self._create_parser([type_token])
                node = parser._parse_type()
                self.assertIsInstance(node, TypeNode)
                self.assertEqual(node.type_token, type_token)

    def test_parse_type_list(self):
        # List<string>
        list_kw = self._token(TokenType.KEYWORD_LIST, "List")
        str_kw = self._token(TokenType.KEYWORD_STRING, "string")
        tokens = [
            list_kw, self._token(TokenType.OP_LT, "<"),
            str_kw, self._token(TokenType.OP_GT, ">")
        ]
        parser = self._create_parser(tokens)
        node = parser._parse_type()
        self.assertIsInstance(node, ListTypeNode)
        self.assertEqual(node.type_token, list_kw)
        self.assertIsInstance(node.child_type_node, TypeNode)
        self.assertEqual(node.child_type_node.type_token, str_kw)

    def test_parse_type_nested_list(self):
        # List<List<int>>
        list_kw1 = self._token(TokenType.KEYWORD_LIST, "List", 1, 1)
        list_kw2 = self._token(TokenType.KEYWORD_LIST, "List", 1, 7)
        int_kw = self._token(TokenType.KEYWORD_INT, "int", 1, 12)
        tokens = [
            list_kw1, self._token(TokenType.OP_LT, "<", 1, 5),
            list_kw2, self._token(TokenType.OP_LT, "<", 1, 11),
            int_kw, self._token(TokenType.OP_GT, ">", 1, 15),
            self._token(TokenType.OP_GT, ">", 1, 16)
        ]
        parser = self._create_parser(tokens)
        node = parser._parse_type()
        self.assertIsInstance(node, ListTypeNode)
        self.assertEqual(node.type_token, list_kw1)
        self.assertIsInstance(node.child_type_node, ListTypeNode)
        self.assertEqual(node.child_type_node.type_token, list_kw2)
        self.assertIsInstance(node.child_type_node.child_type_node, TypeNode)
        self.assertEqual(node.child_type_node.child_type_node.type_token, int_kw)

    # ERRORS
    def test_parse_type_list_missing_gt(self):
        # List<int
        tokens = [
            self._token(TokenType.KEYWORD_LIST, "List"), self._token(TokenType.OP_LT, "<"),
            self._token(TokenType.KEYWORD_INT, "int")
        ]
        parser = self._create_parser(tokens)
        with self.assertRaisesRegex(ParserException, "Expected OP_GT but found EOF"):
            parser._parse_type()

    def test_parse_type_list_missing_child_type(self):
        # List<>
        tokens = [
            self._token(TokenType.KEYWORD_LIST, "List"), self._token(TokenType.OP_LT, "<"),
            self._token(TokenType.OP_GT, ">")
        ]
        parser = self._create_parser(tokens)
        with self.assertRaisesRegex(ParserException, "Unexpected token OP_GT when expecting type keyword"):
            parser._parse_type()


    # --- VARIABLE DECLARATION ---
    def test_variable_declaration_int(self):
        # int x = 10;
        tokens = [
            self._token(TokenType.KEYWORD_INT, "int", 1, 1),
            self._token(TokenType.IDENTIFIER, "x", 1, 5),
            self._token(TokenType.OP_ASSIGN, "=", 1, 7),
            self._token(TokenType.LITERAL_INT, 10, 1, 9),
            self._token(TokenType.SEMICOLON, ";", 1, 11),
        ]
        parser = self._create_parser(tokens)
        node = parser._parse_block_statement()

        self.assertIsInstance(node, VariableDeclarationNode)
        self.assertIsInstance(node.var_type, TypeNode)
        self.assertEqual(node.var_type.type_token.type, TokenType.KEYWORD_INT)
        self.assertEqual(node.identifier.value, "x")
        self.assertIsInstance(node.value, LiteralNode)
        self.assertEqual(node.value.token.value, 10)

    def test_variable_declaration_constructor_types(self):
        # File f = File("a.txt");
        test_cases = [
            (TokenType.KEYWORD_FILE, "File"),
            (TokenType.KEYWORD_FOLDER, "Folder"),
            (TokenType.KEYWORD_AUDIO, "Audio"),
        ]
        for type_kw, type_val in test_cases:
            with self.subTest(type=type_val):
                type_token = self._token(type_kw, type_val, 1,1)
                ident_token = self._token(TokenType.IDENTIFIER, "obj", 1, 1 + len(type_val) + 1)
                constructor_type_token = self._token(type_kw, type_val, 1, 10)
                arg_token = self._token(TokenType.LITERAL_STRING, "path", 1, 15)

                tokens = [
                    type_token, ident_token,
                    self._token(TokenType.OP_ASSIGN, "=", 1, 8),
                    constructor_type_token, self._token(TokenType.LPAREN, "(", 1, 14),
                    arg_token, self._token(TokenType.RPAREN, ")", 1, 20),
                    self._token(TokenType.SEMICOLON, ";", 1, 21),
                ]
                parser = self._create_parser(tokens)
                node = parser._parse_variable_declaration()
                self.assertIsInstance(node, VariableDeclarationNode)
                self.assertIsInstance(node.var_type, TypeNode)
                self.assertEqual(node.var_type.type_token, type_token)
                self.assertEqual(node.identifier, ident_token)
                self.assertIsInstance(node.value, ConstructorCallNode)
                self.assertEqual(node.value.type_token, constructor_type_token)
                self.assertEqual(len(node.value.arguments), 1)
                self.assertEqual(node.value.arguments[0].token, arg_token)

    def test_list_type_declaration(self):
        # List<int> myList = [];
        list_kw_token = self._token(TokenType.KEYWORD_LIST, "List", 1, 1)
        int_kw_token = self._token(TokenType.KEYWORD_INT, "int", 1, 6)
        ident_token = self._token(TokenType.IDENTIFIER, "myList", 1, 11)

        tokens = [
            list_kw_token, self._token(TokenType.OP_LT, "<", 1, 5), int_kw_token, self._token(TokenType.OP_GT, ">", 1, 9),
            ident_token, self._token(TokenType.OP_ASSIGN, "=", 1, 18),
            self._token(TokenType.LBRACKET, "[", 1, 20), self._token(TokenType.RBRACKET, "]", 1, 21),
            self._token(TokenType.SEMICOLON, ";", 1, 22),
        ]
        parser = self._create_parser(tokens)
        node = parser._parse_block_statement() # Testing as a block statement

        self.assertIsInstance(node, VariableDeclarationNode)
        self.assertIsInstance(node.var_type, ListTypeNode)
        self.assertEqual(node.var_type.type_token, list_kw_token)
        self.assertIsInstance(node.var_type.child_type_node, TypeNode)
        self.assertEqual(node.var_type.child_type_node.type_token, int_kw_token)
        self.assertEqual(node.identifier, ident_token)
        self.assertIsInstance(node.value, ListLiteralNode)
        self.assertEqual(len(node.value.elements), 0)

    # ERRORS
    def test_missing_semicolon_after_var_decl(self):
        # int x =
        tokens = [
            self._token(TokenType.KEYWORD_INT, "int"), self._token(TokenType.IDENTIFIER, "x"),
            self._token(TokenType.OP_ASSIGN, "="), self._token(TokenType.LITERAL_INT, 10),
        ]
        parser = self._create_parser(tokens)
        with self.assertRaisesRegex(ParserException, "Expected SEMICOLON but found EOF"):
            parser._parse_variable_declaration()

    def test_var_decl_missing_identifier(self):
        # int = 10;
        tokens = [
            self._token(TokenType.KEYWORD_INT, "int"),
            self._token(TokenType.OP_ASSIGN, "="), self._token(TokenType.LITERAL_INT, 10),
            self._token(TokenType.SEMICOLON, ";"),
        ]
        parser = self._create_parser(tokens)
        with self.assertRaisesRegex(ParserException, "Expected IDENTIFIER but found OP_ASSIGN"):
            parser._parse_variable_declaration()

    def test_var_decl_missing_value(self):
        # int x =;
        tokens = [
            self._token(TokenType.KEYWORD_INT, "int"), self._token(TokenType.IDENTIFIER, "x"),
            self._token(TokenType.OP_ASSIGN, "="), self._token(TokenType.SEMICOLON, ";"),
        ]
        parser = self._create_parser(tokens)
        # Error message depends on what _parse_expression finds first with SEMICOLON
        with self.assertRaisesRegex(ParserException, "Unexpected token SEMICOLON .* when expecting the start of a factor"):
            parser._parse_variable_declaration()



    def test_simple_function_definition_void_noreturn(self):
        # func void doNothing() { return; }
        tokens = [
            self._token(TokenType.KEYWORD_FUNC, "func", 1, 1),
            self._token(TokenType.KEYWORD_VOID, "void", 1, 6),
            self._token(TokenType.IDENTIFIER, "doNothing", 1, 11),
            self._token(TokenType.LPAREN, "(", 1, 20), self._token(TokenType.RPAREN, ")", 1, 21),
            self._token(TokenType.LBRACE, "{", 1, 23),
            self._token(TokenType.KEYWORD_RETURN, "return", 1, 25), self._token(TokenType.SEMICOLON, ";", 1, 31),
            self._token(TokenType.RBRACE, "}", 1, 33),
        ]
        parser = self._create_parser(tokens)
        program_node = parser.parse()
        self.assertEqual(len(program_node.statements), 1)
        node = program_node.statements[0]

        self.assertIsInstance(node, FunctionDefinitionNode)
        self.assertEqual(node.return_type.type_token.type, TokenType.KEYWORD_VOID)
        self.assertEqual(node.identifier.value, "doNothing")
        self.assertEqual(len(node.parameters), 0)
        self.assertIsInstance(node.body, FunctionBodyNode)
        self.assertEqual(len(node.body.block_statements), 0)
        self.assertIsInstance(node.body.return_statement, ReturnStatementNode)
        self.assertIsNone(node.body.return_statement.value)

    def test_if_statement(self):
        # if (true) { x = 1; }
        tokens = [
            self._token(TokenType.KEYWORD_IF, "if", 1,1), self._token(TokenType.LPAREN, "(", 1,4),
            self._token(TokenType.KEYWORD_TRUE, "true", 1,5), self._token(TokenType.RPAREN, ")", 1,9),
            self._token(TokenType.LBRACE, "{", 1,11),
            self._token(TokenType.IDENTIFIER, "x", 1,13), self._token(TokenType.OP_ASSIGN, "=", 1,15),
            self._token(TokenType.LITERAL_INT, 1, 1,17), self._token(TokenType.SEMICOLON, ";", 1,18),
            self._token(TokenType.RBRACE, "}", 1,20),
        ]
        parser = self._create_parser(tokens)
        node = parser._parse_block_statement()

        self.assertIsInstance(node, IfStatementNode)
        self.assertIsInstance(node.condition, LiteralNode)
        self.assertEqual(node.condition.token.type, TokenType.KEYWORD_TRUE)
        self.assertIsInstance(node.if_block, CodeBlockNode)
        self.assertEqual(len(node.if_block.statements), 1)
        self.assertIsInstance(node.if_block.statements[0], AssignmentNode)
        self.assertIsNone(node.else_block)

    # --- ASSIGNMENT TESTS
    def test_assignment_statement(self):
        # count = 0;
        tokens = [
            self._token(TokenType.IDENTIFIER, "count", 1, 1),
            self._token(TokenType.OP_ASSIGN, "=", 1, 7),
            self._token(TokenType.LITERAL_INT, 0, 1, 9),
            self._token(TokenType.SEMICOLON, ";", 1, 10),
        ]
        parser = self._create_parser(tokens)
        node = parser._parse_block_statement()
        self.assertIsInstance(node, AssignmentNode)
        self.assertIsInstance(node.identifier, IdentifierNode)
        self.assertEqual(node.identifier.token.value, "count")
        self.assertIsInstance(node.value, LiteralNode)
        self.assertEqual(node.value.token.value, 0)

    def test_assignment_to_member_access(self):
        # obj.property = 10;
        tokens = [
            self._token(TokenType.IDENTIFIER, "obj",1,1), self._token(TokenType.DOT, ".",1,4),
            self._token(TokenType.IDENTIFIER, "property",1,5),
            self._token(TokenType.OP_ASSIGN, "=",1,14),
            self._token(TokenType.LITERAL_INT, 10,1,16), self._token(TokenType.SEMICOLON, ";",1,18),
        ]
        parser = self._create_parser(tokens)
        node = parser._parse_block_statement()
        self.assertIsInstance(node, AssignmentNode)
        self.assertIsInstance(node.identifier, MemberAccessNode)
        self.assertEqual(node.identifier.object_expr.token.value, "obj")
        self.assertEqual(node.identifier.member_name.value, "property")
        self.assertIsInstance(node.value, LiteralNode)
        self.assertEqual(node.value.token.value, 10)

    # ERROR
    def test_assignment_missing_semicolon(self):
        tokens = [
            self._token(TokenType.IDENTIFIER, "count"), self._token(TokenType.OP_ASSIGN, "="),
            self._token(TokenType.LITERAL_INT, 0),
        ]
        parser = self._create_parser(tokens)
        with self.assertRaisesRegex(ParserException, "Expected SEMICOLON but found EOF"):
            parser._parse_assignment()

    def test_function_call_statement(self):
        # print("hello");
        tokens = [
            self._token(TokenType.IDENTIFIER, "print", 1, 1),
            self._token(TokenType.LPAREN, "(", 1, 6),
            self._token(TokenType.LITERAL_STRING, "hello", 1, 7),
            self._token(TokenType.RPAREN, ")", 1, 14),
            self._token(TokenType.SEMICOLON, ";", 1, 15),
        ]
        parser = self._create_parser(tokens)
        node = parser._parse_block_statement()
        self.assertIsInstance(node, FunctionCallStatementNode)
        call_expr = node.call_expression
        self.assertIsInstance(call_expr, FunctionCallNode)
        self.assertIsInstance(call_expr.function_name, IdentifierNode)
        self.assertEqual(call_expr.function_name.token.value, "print")
        self.assertEqual(len(call_expr.arguments), 1)
        self.assertIsInstance(call_expr.arguments[0], LiteralNode)
        self.assertEqual(call_expr.arguments[0].token.value, "hello")

    def test_complex_expression_precedence(self):
        # 2 + 3 * 4; (should be 2 + (3*4))
        tokens = [
            self._token(TokenType.LITERAL_INT, 2, 1,1), self._token(TokenType.OP_PLUS, "+", 1,3),
            self._token(TokenType.LITERAL_INT, 3, 1,5), self._token(TokenType.OP_MULTIPLY, "*", 1,7),
            self._token(TokenType.LITERAL_INT, 4, 1,9),
            self._token(TokenType.SEMICOLON, ";", 1,10),
        ]
        parser = self._create_parser(tokens)
        node = parser._parse_block_statement()
        self.assertIsInstance(node, ExpressionStatementNode)
        expr = node.expression
        self.assertIsInstance(expr, BinaryOpNode) # 2 + (3*4)
        self.assertEqual(expr.operator.type, TokenType.OP_PLUS)
        self.assertIsInstance(expr.left, LiteralNode)
        self.assertEqual(expr.left.token.value, 2)
        self.assertIsInstance(expr.right, BinaryOpNode) # 3 * 4
        self.assertEqual(expr.right.operator.type, TokenType.OP_MULTIPLY)
        self.assertIsInstance(expr.right.left, LiteralNode) # was expr.right.left.token.value
        self.assertEqual(expr.right.left.token.value, 3)
        self.assertIsInstance(expr.right.right, LiteralNode) # was expr.right.right.token.value
        self.assertEqual(expr.right.right.token.value, 4)

    def test_malformed_constructor_call_no_paren(self):
        # File "test.txt"; (missing parentheses)
        tokens = [
            self._token(TokenType.KEYWORD_FILE, "File", 1, 1),
            self._token(TokenType.LITERAL_STRING, "test.txt", 1, 6),
            self._token(TokenType.SEMICOLON, ";", 1, 16),
        ]
        parser = self._create_parser(tokens)
        with self.assertRaisesRegex(ParserException, "Expected '\\(' after constructor keyword File"):
            parser._parse_expression()


    def test_missing_semicolon_after_var_decl(self):
        # int x = 10 (no semicolon)
        tokens = [
            self._token(TokenType.KEYWORD_INT, "int", 1,1),
            self._token(TokenType.IDENTIFIER, "x", 1,5),
            self._token(TokenType.OP_ASSIGN, "=", 1,7),
            self._token(TokenType.LITERAL_INT, 10, 1,9),
        ]
        parser = self._create_parser(tokens)
        with self.assertRaisesRegex(ParserException, "Expected SEMICOLON but found EOF"):
            parser._parse_variable_declaration()

    def test_malformed_function_no_rbrace(self):
        # func void test() { return; (missing closing brace)
        tokens = [
            self._token(TokenType.KEYWORD_FUNC, "func", 1,1), self._token(TokenType.KEYWORD_VOID, "void", 1,6),
            self._token(TokenType.IDENTIFIER, "test", 1,11),
            self._token(TokenType.LPAREN, "(", 1,15), self._token(TokenType.RPAREN, ")", 1,16),
            self._token(TokenType.LBRACE, "{", 1,18),
            self._token(TokenType.KEYWORD_RETURN, "return", 1,20), self._token(TokenType.SEMICOLON, ";", 1,26),
        ]
        parser = self._create_parser(tokens)
        with self.assertRaisesRegex(ParserException, "Expected RBRACE but found EOF"):
            parser.parse()


if __name__ == '__main__':
    unittest.main(argv=['first-arg-is-ignored'], exit=False)