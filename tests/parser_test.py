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
        list_kw1 = self._token(TokenType.KEYWORD_LIST, "List")
        list_kw2 = self._token(TokenType.KEYWORD_LIST, "List")
        int_kw = self._token(TokenType.KEYWORD_INT, "int")
        tokens = [
            list_kw1, self._token(TokenType.OP_LT, "<"),
            list_kw2, self._token(TokenType.OP_LT, "<"),
            int_kw, self._token(TokenType.OP_GT, ">"),
            self._token(TokenType.OP_GT, ">")
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
            self._token(TokenType.KEYWORD_INT, "int"),
            self._token(TokenType.IDENTIFIER, "x"),
            self._token(TokenType.OP_ASSIGN, "="),
            self._token(TokenType.LITERAL_INT, 10),
            self._token(TokenType.SEMICOLON, ";"),
        ]
        parser = self._create_parser(tokens)
        node = parser._parse_statement()

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
                type_token = self._token(type_kw, type_val)
                ident_token = self._token(TokenType.IDENTIFIER, "obj")
                constructor_type_token = self._token(type_kw, type_val)
                arg_token = self._token(TokenType.LITERAL_STRING, "path")

                tokens = [
                    type_token, ident_token,
                    self._token(TokenType.OP_ASSIGN, "="),
                    constructor_type_token, self._token(TokenType.LPAREN, "("),
                    arg_token, self._token(TokenType.RPAREN, ")"),
                    self._token(TokenType.SEMICOLON, ";"),
                ]
                parser = self._create_parser(tokens)
                node = parser._try_parse_variable_declaration()
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
        list_kw_token = self._token(TokenType.KEYWORD_LIST, "List")
        int_kw_token = self._token(TokenType.KEYWORD_INT, "int")
        ident_token = self._token(TokenType.IDENTIFIER, "myList")

        tokens = [
            list_kw_token, self._token(TokenType.OP_LT, "<"), int_kw_token, self._token(TokenType.OP_GT, ">"),
            ident_token, self._token(TokenType.OP_ASSIGN, "="),
            self._token(TokenType.LBRACKET, "["), self._token(TokenType.RBRACKET, "]"),
            self._token(TokenType.SEMICOLON, ";"),
        ]
        parser = self._create_parser(tokens)
        node = parser._parse_statement() # Testing as a block statement

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
            parser._try_parse_variable_declaration()

    def test_var_decl_missing_identifier(self):
        # int = 10;
        tokens = [
            self._token(TokenType.KEYWORD_INT, "int"),
            self._token(TokenType.OP_ASSIGN, "="), self._token(TokenType.LITERAL_INT, 10),
            self._token(TokenType.SEMICOLON, ";"),
        ]
        parser = self._create_parser(tokens)
        with self.assertRaisesRegex(ParserException, "Expected IDENTIFIER but found OP_ASSIGN"):
            parser._try_parse_variable_declaration()

    def test_var_decl_missing_value(self):
        # int x =;
        tokens = [
            self._token(TokenType.KEYWORD_INT, "int"), self._token(TokenType.IDENTIFIER, "x"),
            self._token(TokenType.OP_ASSIGN, "="), self._token(TokenType.SEMICOLON, ";"),
        ]
        parser = self._create_parser(tokens)
        # Error message depends on what _parse_expression finds first with SEMICOLON
        with self.assertRaisesRegex(ParserException, "Unexpected token SEMICOLON .* when expecting the start of a factor"):
            parser._try_parse_variable_declaration()

    # --- ASSIGNMENT ---
    def test_assignment_statement(self):
        # count = 0;
        tokens = [
            self._token(TokenType.IDENTIFIER, "count"),
            self._token(TokenType.OP_ASSIGN, "="),
            self._token(TokenType.LITERAL_INT, 0),
            self._token(TokenType.SEMICOLON, ";"),
        ]
        parser = self._create_parser(tokens)
        node = parser._parse_statement()
        self.assertIsInstance(node, AssignmentNode)
        self.assertIsInstance(node.identifier, IdentifierNode)
        self.assertEqual(node.identifier.token.value, "count")
        self.assertIsInstance(node.value, LiteralNode)
        self.assertEqual(node.value.token.value, 0)

    def test_assignment_to_member_access(self):
        # obj.property = 10;
        tokens = [
            self._token(TokenType.IDENTIFIER, "obj"), self._token(TokenType.DOT, "."),
            self._token(TokenType.IDENTIFIER, "property"),
            self._token(TokenType.OP_ASSIGN, "="),
            self._token(TokenType.LITERAL_INT, 10), self._token(TokenType.SEMICOLON, ";"),
        ]
        parser = self._create_parser(tokens)
        node = parser._parse_statement()
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


    # FUNCTION CALLS
    def test_function_call_statement(self):
        # print("hello");
        tokens = [
            self._token(TokenType.IDENTIFIER, "print"),
            self._token(TokenType.LPAREN, "("),
            self._token(TokenType.LITERAL_STRING, "hello"),
            self._token(TokenType.RPAREN, ")"),
            self._token(TokenType.SEMICOLON, ";"),
        ]
        parser = self._create_parser(tokens)
        node = parser._parse_statement()
        self.assertIsInstance(node, FunctionCallStatementNode)
        call_expr = node.call_expression
        self.assertIsInstance(call_expr, FunctionCallNode)
        self.assertIsInstance(call_expr.function_name, IdentifierNode)
        self.assertEqual(call_expr.function_name.token.value, "print")
        self.assertEqual(len(call_expr.arguments), 1)
        self.assertIsInstance(call_expr.arguments[0], LiteralNode)
        self.assertEqual(call_expr.arguments[0].token.value, "hello")

    def test_function_call_multiple_args_expression(self):
        # add(1, 2);
        tokens = [
            self._token(TokenType.IDENTIFIER, "add"), self._token(TokenType.LPAREN, "("),
            self._token(TokenType.LITERAL_INT, 1), self._token(TokenType.COMMA, ","),
            self._token(TokenType.LITERAL_INT, 2), self._token(TokenType.RPAREN, ")"),
        ]
        parser = self._create_parser(tokens)
        node = parser._parse_expression()
        self.assertIsInstance(node, FunctionCallNode)
        self.assertEqual(node.function_name.token.value, "add")
        self.assertEqual(len(node.arguments), 2)
        self.assertEqual(node.arguments[0].token.value, 1)
        self.assertEqual(node.arguments[1].token.value, 2)

    # ERRORS
    def test_function_call_missing_rparen(self):
        #print("hello";
        tokens = [
            self._token(TokenType.IDENTIFIER, "print"), self._token(TokenType.LPAREN, "("),
            self._token(TokenType.LITERAL_STRING, "hello"),
            self._token(TokenType.SEMICOLON, ";"),
        ]
        parser = self._create_parser(tokens)
        with self.assertRaisesRegex(ParserException, "Expected RPAREN but found SEMICOLON"):
            parser._parse_statement()

    def test_function_call_missing_comma_in_args(self):
        # add(1 2);
        tokens = [
            self._token(TokenType.IDENTIFIER, "add"), self._token(TokenType.LPAREN, "("),
            self._token(TokenType.LITERAL_INT, 1),
            self._token(TokenType.LITERAL_INT, 2),
            self._token(TokenType.RPAREN, ")"), self._token(TokenType.SEMICOLON, ";"),
        ]
        parser = self._create_parser(tokens)
        with self.assertRaisesRegex(ParserException, "Expected RPAREN but found LITERAL_INT"):
            parser._parse_statement()

    # --- EXPRESSIONS ---
    def test_expression_statement(self):
        # 1 + 2;
        tokens = [
            self._token(TokenType.LITERAL_INT, 1), self._token(TokenType.OP_PLUS, "+"),
            self._token(TokenType.LITERAL_INT, 2), self._token(TokenType.SEMICOLON, ";"),
        ]
        parser = self._create_parser(tokens)
        node = parser._parse_statement()
        self.assertIsInstance(node, ExpressionStatementNode)
        self.assertIsInstance(node.expression, BinaryOpNode)

    def test_complex_expression_precedence(self):
        # 2 + 3 * 4;
        tokens = [
            self._token(TokenType.LITERAL_INT, 2,), self._token(TokenType.OP_PLUS, "+"),
            self._token(TokenType.LITERAL_INT, 3), self._token(TokenType.OP_MULTIPLY, "*"),
            self._token(TokenType.LITERAL_INT, 4),
            self._token(TokenType.SEMICOLON, ";"),
        ]
        parser = self._create_parser(tokens)
        node = parser._parse_statement()
        self.assertIsInstance(node, ExpressionStatementNode)
        expr = node.expression
        self.assertIsInstance(expr, BinaryOpNode) # 2 + (3*4)
        self.assertEqual(expr.operator.type, TokenType.OP_PLUS)
        self.assertIsInstance(expr.left, LiteralNode)
        self.assertEqual(expr.left.token.value, 2)
        self.assertIsInstance(expr.right, BinaryOpNode) # 3 * 4
        self.assertEqual(expr.right.operator.type, TokenType.OP_MULTIPLY)
        self.assertIsInstance(expr.right.left, LiteralNode)
        self.assertEqual(expr.right.left.token.value, 3)
        self.assertIsInstance(expr.right.right, LiteralNode)
        self.assertEqual(expr.right.right.token.value, 4)

    # --- FUNCTION DEFINITION ---
    def test_simple_function_definition_void_noreturn(self):
        # func void doNothing() { return; }
        tokens = [
            self._token(TokenType.KEYWORD_FUNC, "func"),
            self._token(TokenType.KEYWORD_VOID, "void"),
            self._token(TokenType.IDENTIFIER, "doNothing"),
            self._token(TokenType.LPAREN, "("), self._token(TokenType.RPAREN, ")"),
            self._token(TokenType.LBRACE, "{"),
            self._token(TokenType.KEYWORD_RETURN, "return"), self._token(TokenType.SEMICOLON, ";"),
            self._token(TokenType.RBRACE, "}"),
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
        self.assertEqual(len(node.body.statements), 1)

    def test_function_definition_with_parameters(self):
        # func int add(int a, int b) { return a + b; }
        int_type1 = self._token(TokenType.KEYWORD_INT, "int")
        param_a = self._token(TokenType.IDENTIFIER, "a")
        int_type2 = self._token(TokenType.KEYWORD_INT, "int")
        param_b = self._token(TokenType.IDENTIFIER, "b")

        tokens = [
            self._token(TokenType.KEYWORD_FUNC, "func"), self._token(TokenType.KEYWORD_INT, "int"),
            self._token(TokenType.IDENTIFIER, "add"),
            self._token(TokenType.LPAREN, "("),
            int_type1, param_a, self._token(TokenType.COMMA, ","),
            int_type2, param_b,
            self._token(TokenType.RPAREN, ")"),
            self._token(TokenType.LBRACE, "{"),
            self._token(TokenType.KEYWORD_RETURN, "return"),
            self._token(TokenType.IDENTIFIER, "a"), self._token(TokenType.OP_PLUS, "+"),
            self._token(TokenType.IDENTIFIER, "b"), self._token(TokenType.SEMICOLON, ";"),
            self._token(TokenType.RBRACE, "}"),
        ]
        parser = self._create_parser(tokens)
        node = parser._try_parse_function_definition()
        self.assertIsInstance(node, FunctionDefinitionNode)
        self.assertEqual(len(node.parameters), 2)
        self.assertEqual(node.parameters[0].param_type.type_token, int_type1)
        self.assertEqual(node.parameters[0].param_name, param_a)
        self.assertEqual(node.parameters[1].param_type.type_token, int_type2)
        self.assertEqual(node.parameters[1].param_name, param_b)

    def test_function_body_with_statements(self):
        # { int x = 5; return x; }
        tokens = [
            self._token(TokenType.LBRACE, "{"),
            self._token(TokenType.KEYWORD_INT, "int"), self._token(TokenType.IDENTIFIER, "x"),
            self._token(TokenType.OP_ASSIGN, "="), self._token(TokenType.LITERAL_INT, 5),
            self._token(TokenType.SEMICOLON, ";"),
            self._token(TokenType.KEYWORD_RETURN, "return"), self._token(TokenType.IDENTIFIER, "x"),
            self._token(TokenType.SEMICOLON, ";"),
            self._token(TokenType.RBRACE, "}")
        ]
        parser = self._create_parser(tokens)
        node = parser._parse_function_body()
        self.assertIsInstance(node, FunctionBodyNode)
        self.assertEqual(len(node.statements), 2)
        self.assertIsInstance(node.statements[0], VariableDeclarationNode)

    def test_parameter_list_multiple(self):
        # string s, bool b
        str_tok = self._token(TokenType.KEYWORD_STRING, "string")
        s_id = self._token(TokenType.IDENTIFIER, "s")
        bool_tok = self._token(TokenType.KEYWORD_BOOL, "bool")
        b_id = self._token(TokenType.IDENTIFIER, "b")
        parser = self._create_parser([
            str_tok, s_id, self._token(TokenType.COMMA, ","), bool_tok, b_id
        ])
        params = parser._parse_parameter_list()
        self.assertEqual(len(params), 2)
        self.assertEqual(params[1].param_type.type_token, bool_tok)
        self.assertEqual(params[1].param_name, b_id)

    def test_malformed_function_no_rbrace(self):
        # func void test() { return;
        tokens = [
            self._token(TokenType.KEYWORD_FUNC, "func"), self._token(TokenType.KEYWORD_VOID, "void"),
            self._token(TokenType.IDENTIFIER, "test"),
            self._token(TokenType.LPAREN, "("), self._token(TokenType.RPAREN, ")"),
            self._token(TokenType.LBRACE, "{"),
            self._token(TokenType.KEYWORD_RETURN, "return"), self._token(TokenType.SEMICOLON, ";"),
        ]
        parser = self._create_parser(tokens)
        with self.assertRaisesRegex(ParserException, "Expected RBRACE but found EOF"):
            parser.parse()

    def test_function_def_missing_return_type(self):
        # func myFunc
        tokens = [
            self._token(TokenType.KEYWORD_FUNC, "func"),
            self._token(TokenType.IDENTIFIER, "myFunc"),
        ]
        parser = self._create_parser(tokens)
        with self.assertRaisesRegex(ParserException, "Unexpected token IDENTIFIER when expecting type keyword"):
            parser._try_parse_function_definition()

    # --- IF/WHILE STATEMENTS ---
    def test_if_statement(self): # Existing, verified for if-only
        tokens = [
            self._token(TokenType.KEYWORD_IF, "if"), self._token(TokenType.LPAREN, "("),
            self._token(TokenType.KEYWORD_TRUE, "true"), self._token(TokenType.RPAREN, ")"),
            self._token(TokenType.LBRACE, "{"),
            self._token(TokenType.IDENTIFIER, "x"), self._token(TokenType.OP_ASSIGN, "="),
            self._token(TokenType.LITERAL_INT, 1), self._token(TokenType.SEMICOLON, ";"),
            self._token(TokenType.RBRACE, "}"),
        ]
        parser = self._create_parser(tokens)
        node = parser._try_parse_if_statement()
        self.assertIsInstance(node, IfStatementNode)
        self.assertIsInstance(node.condition, LiteralNode)
        self.assertIsInstance(node.if_block, CodeBlockNode)
        self.assertEqual(len(node.if_block.statements), 1)
        self.assertIsNone(node.else_block)

    def test_if_else_statement(self):
        # if (false) {} else { y = 2; }
        tokens = [
            self._token(TokenType.KEYWORD_IF, "if"), self._token(TokenType.LPAREN, "("),
            self._token(TokenType.KEYWORD_FALSE, "false"), self._token(TokenType.RPAREN, ")"),
            self._token(TokenType.LBRACE, "{"), self._token(TokenType.RBRACE, "}"),
            self._token(TokenType.KEYWORD_ELSE, "else"),
            self._token(TokenType.LBRACE, "{"),
            self._token(TokenType.IDENTIFIER, "y"), self._token(TokenType.OP_ASSIGN, "="),
            self._token(TokenType.LITERAL_INT, 2), self._token(TokenType.SEMICOLON, ";"),
            self._token(TokenType.RBRACE, "}"),
        ]
        parser = self._create_parser(tokens)
        node = parser._try_parse_if_statement()
        self.assertIsInstance(node, IfStatementNode)
        self.assertIsInstance(node.condition, LiteralNode)
        self.assertEqual(node.condition.token.type, TokenType.KEYWORD_FALSE)
        self.assertIsInstance(node.if_block, CodeBlockNode)
        self.assertEqual(len(node.if_block.statements), 0)
        self.assertIsInstance(node.else_block, CodeBlockNode)
        self.assertEqual(len(node.else_block.statements), 1)
        self.assertIsInstance(node.else_block.statements[0], AssignmentNode)

    def test_while_loop(self):
        # while (i < 10) { i = i + 1; }
        tokens = [
            self._token(TokenType.KEYWORD_WHILE, "while"), self._token(TokenType.LPAREN, "("),
            self._token(TokenType.IDENTIFIER, "i"), self._token(TokenType.OP_LT, "<"),
            self._token(TokenType.LITERAL_INT, 10), self._token(TokenType.RPAREN, ")"),
            self._token(TokenType.LBRACE, "{"),
            self._token(TokenType.IDENTIFIER, "i"), self._token(TokenType.OP_ASSIGN, "="),
            self._token(TokenType.IDENTIFIER, "i"), self._token(TokenType.OP_PLUS, "+"),
            self._token(TokenType.LITERAL_INT, 1), self._token(TokenType.SEMICOLON, ";"),
            self._token(TokenType.RBRACE, "}"),
        ]
        parser = self._create_parser(tokens)
        node = parser._try_parse_while_loop()
        self.assertIsInstance(node, WhileLoopNode)
        self.assertIsInstance(node.condition, BinaryOpNode)
        self.assertIsInstance(node.body, CodeBlockNode)
        self.assertEqual(len(node.body.statements), 1)

    # ERRORS
    def test_if_missing_condition_paren(self):
        # if true
        tokens = [
            self._token(TokenType.KEYWORD_IF, "if"),
            self._token(TokenType.KEYWORD_TRUE, "true"),
        ]
        parser = self._create_parser(tokens)
        with self.assertRaisesRegex(ParserException, "Expected LPAREN but found KEYWORD_TRUE"):
            parser._try_parse_if_statement()

    def test_if_missing_if_block(self):
        # if(true) else
        tokens = [
            self._token(TokenType.KEYWORD_IF, "if"), self._token(TokenType.LPAREN, "("),
            self._token(TokenType.KEYWORD_TRUE, "true"), self._token(TokenType.RPAREN, ")"),
            self._token(TokenType.KEYWORD_ELSE, "else"),
        ]
        parser = self._create_parser(tokens)
        with self.assertRaisesRegex(ParserException, "Expected LBRACE but found KEYWORD_ELSE"):
            parser._try_parse_if_statement()

    def test_while_missing_condition_paren(self):
        tokens = [
            self._token(TokenType.KEYWORD_WHILE, "while"),
            self._token(TokenType.KEYWORD_TRUE, "true"), # Missing LPAREN
        ]
        parser = self._create_parser(tokens)
        with self.assertRaisesRegex(ParserException, "Expected LPAREN but found KEYWORD_TRUE"):
            parser._try_parse_while_loop()

    def test_while_missing_body_lbrace(self):
        tokens = [
            self._token(TokenType.KEYWORD_WHILE, "while"), self._token(TokenType.LPAREN, "("),
            self._token(TokenType.KEYWORD_TRUE, "true"), self._token(TokenType.RPAREN, ")"),
            self._token(TokenType.SEMICOLON, ";"), # Missing LBRACE
        ]
        parser = self._create_parser(tokens)
        with self.assertRaisesRegex(ParserException, "Expected LBRACE but found SEMICOLON"):
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
        for token_type, token_val in test_cases:
            with self.subTest(literal=token_val):
                tok = self._token(token_type, token_val)
                parser = self._create_parser([tok])
                node = parser._parse_factor()
                self.assertIsInstance(node, LiteralNode)
                self.assertEqual(node.token, tok)

    def test_factor_list_literal_nested(self):
        # [[1], [2,3]]
        tokens = [
            self._token(TokenType.LBRACKET, "["), # Outer [
                self._token(TokenType.LBRACKET, "["), self._token(TokenType.LITERAL_INT, 1), self._token(TokenType.RBRACKET, "]"), # [1]
            self._token(TokenType.COMMA, ","),
                self._token(TokenType.LBRACKET, "["), self._token(TokenType.LITERAL_INT, 2), self._token(TokenType.COMMA, ","),
                self._token(TokenType.LITERAL_INT, 3), self._token(TokenType.RBRACKET, "]"), # [2,3]
            self._token(TokenType.RBRACKET, "]")  # Outer ]
        ]
        parser = self._create_parser(tokens)
        node = parser._parse_factor()
        self.assertIsInstance(node, ListLiteralNode)
        self.assertEqual(len(node.elements), 2)
        self.assertIsInstance(node.elements[0], ListLiteralNode)
        self.assertEqual(len(node.elements[0].elements), 1)
        self.assertEqual(node.elements[0].elements[0].token.value, 1)
        self.assertIsInstance(node.elements[1], ListLiteralNode)
        self.assertEqual(len(node.elements[1].elements), 2)
        self.assertEqual(node.elements[1].elements[0].token.value, 2)
        self.assertEqual(node.elements[1].elements[1].token.value, 3)

    def test_factor_constructor_call(self):
        # File("config.txt")
        file_kw = self._token(TokenType.KEYWORD_FILE, "File")
        arg_tok = self._token(TokenType.LITERAL_STRING, "config.txt")
        tokens = [
            file_kw, self._token(TokenType.LPAREN, "("),
            arg_tok, self._token(TokenType.RPAREN, ")")
        ]
        parser = self._create_parser(tokens)
        node = parser._parse_factor()
        self.assertIsInstance(node, ConstructorCallNode)
        self.assertEqual(node.type_token, file_kw)
        self.assertEqual(len(node.arguments), 1)
        self.assertEqual(node.arguments[0].token, arg_tok)

    def test_factor_member_access_property(self):
        # myObject.property
        obj_id = self._token(TokenType.IDENTIFIER, "myObject")
        prop_id = self._token(TokenType.IDENTIFIER, "property")
        tokens = [
            obj_id, self._token(TokenType.DOT, "."), prop_id
        ]
        parser = self._create_parser(tokens)
        node = parser._parse_factor()
        self.assertIsInstance(node, MemberAccessNode)
        self.assertIsInstance(node.object_expr, IdentifierNode)
        self.assertEqual(node.object_expr.token, obj_id)
        self.assertEqual(node.member_name, prop_id)

    def test_factor_member_access_method_call_no_args(self):
        # myObject.doSomething()
        obj_id = self._token(TokenType.IDENTIFIER, "myObject")
        method_id = self._token(TokenType.IDENTIFIER, "doSomething")
        tokens = [
            obj_id, self._token(TokenType.DOT, "."), method_id,
            self._token(TokenType.LPAREN, "("), self._token(TokenType.RPAREN, ")")
        ]
        parser = self._create_parser(tokens)
        node = parser._parse_factor()
        self.assertIsInstance(node, FunctionCallNode)
        self.assertIsInstance(node.function_name, MemberAccessNode)
        member_access_expr = node.function_name
        self.assertIsInstance(member_access_expr.object_expr, IdentifierNode)
        self.assertEqual(member_access_expr.object_expr.token, obj_id)
        self.assertEqual(member_access_expr.member_name, method_id)
        self.assertEqual(len(node.arguments), 0)

    def test_chained_member_access(self):
        # obj.prop1.prop2
        tokens = [
            self._token(TokenType.IDENTIFIER, "obj"), self._token(TokenType.DOT, "."),
            self._token(TokenType.IDENTIFIER, "prop1"), self._token(TokenType.DOT, "."),
            self._token(TokenType.IDENTIFIER, "prop2")
        ]
        parser = self._create_parser(tokens)
        node = parser._parse_factor()
        self.assertIsInstance(node, MemberAccessNode) # obj.prop1.prop2
        self.assertEqual(node.member_name.value, "prop2")
        self.assertIsInstance(node.object_expr, MemberAccessNode) # obj.prop1
        self.assertEqual(node.object_expr.member_name.value, "prop1")
        self.assertIsInstance(node.object_expr.object_expr, IdentifierNode) # obj
        self.assertEqual(node.object_expr.object_expr.token.value, "obj")

    # ERRORS
    def test_member_access_missing_member_name(self):
        # obj.
        tokens = [
            self._token(TokenType.IDENTIFIER, "obj"), self._token(TokenType.DOT, "."),
        ]
        parser = self._create_parser(tokens)
        with self.assertRaisesRegex(ParserException, "Expected IDENTIFIER but found EOF"):
            parser._parse_factor()

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




if __name__ == '__main__':
    unittest.main(argv=['first-arg-is-ignored'], exit=False)