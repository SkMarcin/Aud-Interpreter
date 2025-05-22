import unittest
import io

from source.reader import SourceReader
from source.cleaner import Cleaner
from source.lexer import Lexer
from source.parser import Parser
from source.nodes import *
from source.utils import ParserException, Config
from source.utils import (
    UnterminatedStringException,
    InvalidEscapeSequenceException,
)
from source.tokens import TokenType

class TestLexerParserIntegration(unittest.TestCase):

    def _create_parser_from_string(self, code_string: str, config: Config = None) -> Parser:
        if config is None:
            config = Config()
        string_io = io.StringIO(code_string)
        reader = SourceReader(string_io)
        cleaner = Cleaner(reader, config)
        lexer = Lexer(reader, cleaner, config)
        parser = Parser(lexer)
        return parser

    def test_empty_program_integration(self):
        code = ""
        parser = self._create_parser_from_string(code)
        program_node = parser.parse()
        self.assertIsInstance(program_node, ProgramNode)
        self.assertEqual(len(program_node.statements), 0)

    def test_variable_declaration_int_integration(self):
        code = "int x = 10;"
        parser = self._create_parser_from_string(code)
        program_node = parser.parse()
        self.assertEqual(len(program_node.statements), 1)
        stmt = program_node.statements[0]
        self.assertIsInstance(stmt, VariableDeclarationNode)
        self.assertIsInstance(stmt.var_type, TypeNode)
        self.assertEqual(stmt.var_type.type_token.type, TokenType.KEYWORD_INT)
        self.assertEqual(stmt.identifier.value, "x")
        self.assertIsInstance(stmt.value, LiteralNode)
        self.assertEqual(stmt.value.token.type, TokenType.LITERAL_INT)
        self.assertEqual(stmt.value.token.value, 10)

    def test_variable_declaration_float_integration(self):
        code = "float pi = 3.14;"
        parser = self._create_parser_from_string(code)
        program_node = parser.parse()
        self.assertEqual(len(program_node.statements), 1)
        stmt = program_node.statements[0]
        self.assertIsInstance(stmt, VariableDeclarationNode)
        self.assertEqual(stmt.var_type.type_token.type, TokenType.KEYWORD_FLOAT)
        self.assertEqual(stmt.identifier.value, "pi")
        self.assertIsInstance(stmt.value, LiteralNode)
        self.assertEqual(stmt.value.token.type, TokenType.LITERAL_FLOAT)

        # Comparing floats
        self.assertAlmostEqual(stmt.value.token.value, 3.14)

    def test_variable_declaration_string_with_escapes_integration(self):
        code = 'string path = "C:\\\\new\\\\folder\\\\file.txt\\n";'
        parser = self._create_parser_from_string(code)
        program_node = parser.parse()
        stmt = program_node.statements[0]
        self.assertIsInstance(stmt, VariableDeclarationNode)
        self.assertEqual(stmt.var_type.type_token.type, TokenType.KEYWORD_STRING)
        self.assertEqual(stmt.value.token.type, TokenType.LITERAL_STRING)
        self.assertEqual(stmt.value.token.value, "C:\\new\\folder\\file.txt\n")

    def test_variable_declaration_bool_false_integration(self):
        code = "bool isDone = false;"
        parser = self._create_parser_from_string(code)
        program_node = parser.parse()
        stmt = program_node.statements[0]
        self.assertIsInstance(stmt, VariableDeclarationNode)
        self.assertEqual(stmt.var_type.type_token.type, TokenType.KEYWORD_BOOL)
        self.assertEqual(stmt.value.token.type, TokenType.KEYWORD_FALSE)
        self.assertEqual(stmt.value.token.value, "false")

    def test_variable_declaration_list_of_strings_integration(self):
        code = 'List<string> names = ["Alice", "Bob", "Charlie"];'
        parser = self._create_parser_from_string(code)
        program_node = parser.parse()
        stmt = program_node.statements[0]
        self.assertIsInstance(stmt, VariableDeclarationNode)
        self.assertIsInstance(stmt.var_type, ListTypeNode)
        self.assertEqual(stmt.var_type.child_type_node.type_token.type, TokenType.KEYWORD_STRING)
        self.assertIsInstance(stmt.value, ListLiteralNode)
        self.assertEqual(len(stmt.value.elements), 3)
        self.assertEqual(stmt.value.elements[0].token.value, "Alice")
        self.assertEqual(stmt.value.elements[2].token.value, "Charlie")

    def test_assignment_to_member_access_integration(self):
        code = "myObject.property.value = 100;"
        parser = self._create_parser_from_string(code)
        program_node = parser.parse()
        self.assertEqual(len(program_node.statements), 1)
        stmt = program_node.statements[0]
        self.assertIsInstance(stmt, AssignmentNode)

        self.assertIsInstance(stmt.identifier, MemberAccessNode)
        self.assertEqual(stmt.identifier.member_name.value, "value")
        self.assertIsInstance(stmt.identifier.object_expr, MemberAccessNode)
        self.assertEqual(stmt.identifier.object_expr.member_name.value, "property")
        self.assertIsInstance(stmt.identifier.object_expr.object_expr, IdentifierNode)
        self.assertEqual(stmt.identifier.object_expr.object_expr.token.value, "myObject")
        self.assertEqual(stmt.value.token.value, 100)

    def test_function_call_with_expression_argument_integration(self):
        code = 'calculate(value1 + value2, 10 * 2);'
        parser = self._create_parser_from_string(code)
        program_node = parser.parse()
        stmt = program_node.statements[0]
        self.assertIsInstance(stmt, FunctionCallStatementNode)
        call_expr = stmt.call_expression
        self.assertEqual(len(call_expr.arguments), 2)
        self.assertIsInstance(call_expr.arguments[0], BinaryOpNode)
        self.assertEqual(call_expr.arguments[0].operator.type, TokenType.OP_PLUS)
        self.assertIsInstance(call_expr.arguments[1], BinaryOpNode)
        self.assertEqual(call_expr.arguments[1].operator.type, TokenType.OP_MULTIPLY)

    def test_if_else_integration(self):
        code = """
        if (score > 90) {
            grade = "A";
        } else { /* This is 'else { if (score > 80) ... }' */
            grade = "B";
        }
        """
        parser = self._create_parser_from_string(code)
        program_node = parser.parse()
        stmt = program_node.statements[0]
        self.assertIsInstance(stmt, IfStatementNode)
        self.assertEqual(stmt.condition.left.token.value, "score")
        self.assertIsNotNone(stmt.else_block)
        self.assertIsInstance(stmt.else_block, CodeBlockNode)
        self.assertEqual(len(stmt.else_block.statements), 1)

        else_stmt = stmt.else_block.statements[0]
        self.assertIsInstance(else_stmt, AssignmentNode)
        self.assertEqual(else_stmt.identifier.token.value, "grade")
        self.assertEqual(else_stmt.value.token.value, "B")

    def test_while_loop_with_break_like_construct_integration(self):
        code = """
        while (isRunning && count < max_count) {
            process();
            count = count + 1;
        }
        """
        parser = self._create_parser_from_string(code)
        program_node = parser.parse()
        stmt = program_node.statements[0]
        self.assertIsInstance(stmt, WhileLoopNode)
        self.assertIsInstance(stmt.condition, BinaryOpNode) # isRunning && (count < max_count)
        self.assertEqual(stmt.condition.operator.type, TokenType.OP_AND)
        self.assertIsInstance(stmt.body, CodeBlockNode)
        self.assertEqual(len(stmt.body.statements), 2)

    def test_function_definition_list_param_and_constructor_return_integration(self):
        code = """
        func File createFile(List<string> parts) {
            string path = parts.join("/"); /* Assume List has join method */
            return File(path);
        }
        """
        parser = self._create_parser_from_string(code)
        program_node = parser.parse()
        stmt = program_node.statements[0]
        self.assertIsInstance(stmt, FunctionDefinitionNode)
        self.assertEqual(stmt.return_type.type_token.type, TokenType.KEYWORD_FILE)
        self.assertEqual(len(stmt.parameters), 1)
        self.assertIsInstance(stmt.parameters[0].param_type, ListTypeNode)
        self.assertEqual(stmt.parameters[0].param_type.child_type_node.type_token.type, TokenType.KEYWORD_STRING)

    def test_comments_and_whitespace_integration(self):
        code = """
        /* Start of program */
        func void main ( ) { /* Function body starts */
            int  a = 1 ;
            /*
                int b = 2;
                This is commented out
            */
            int c =3;print ( a+c ) ; /* Print sum */
            return;
        }
        """
        parser = self._create_parser_from_string(code)
        program_node = parser.parse()
        self.assertEqual(len(program_node.statements), 1)
        func_def = program_node.statements[0]
        self.assertIsInstance(func_def, FunctionDefinitionNode)
        self.assertEqual(func_def.identifier.value, "main")
        self.assertEqual(len(func_def.body.statements), 4)

        var_decl_a = func_def.body.statements[0]
        self.assertEqual(var_decl_a.identifier.value, "a")
        self.assertEqual(var_decl_a.value.token.value, 1)

        var_decl_c = func_def.body.statements[1]
        self.assertEqual(var_decl_c.identifier.value, "c")
        self.assertEqual(var_decl_c.value.token.value, 3)

        print_call = func_def.body.statements[2]
        self.assertIsInstance(print_call, FunctionCallStatementNode)
        self.assertEqual(print_call.call_expression.function_name.token.value, "print")
        self.assertIsInstance(print_call.call_expression.arguments[0], BinaryOpNode)


    def test_lexer_parser_error_unterminated_string(self):
        code = 'string error = "this is not closed;'
        parser = self._create_parser_from_string(code)
        with self.assertRaises(UnterminatedStringException): # Error from Lexer
            parser.parse()

    def test_lexer_parser_error_invalid_escape(self):
        code = 'string error = "this has invalid escape \\x";'
        parser = self._create_parser_from_string(code)
        with self.assertRaises(InvalidEscapeSequenceException): # Error from Lexer
            parser.parse()

    def test_parser_error_unexpected_eof_in_expression(self):
        code = "int x = 10 + " # Expression not finished
        parser = self._create_parser_from_string(code)
        with self.assertRaisesRegex(ParserException, "Unexpected token EOF .* expecting the start of a factor"):
            parser.parse()

    def test_parser_error_missing_function_body_brace(self):
        code = "func void test() return;" # Missing { and }
        parser = self._create_parser_from_string(code)
        with self.assertRaisesRegex(ParserException, "Expected LBRACE but found KEYWORD_RETURN"):
            parser.parse()

    def test_all_literal_types_in_list_integration(self):
        code = "List<void> mixed = [10, 3.14, \"text\", true, false, null];"
        parser = self._create_parser_from_string(code)
        program_node = parser.parse()
        stmt = program_node.statements[0]
        self.assertIsInstance(stmt, VariableDeclarationNode)
        self.assertIsInstance(stmt.value, ListLiteralNode)
        elements = stmt.value.elements
        self.assertEqual(len(elements), 6)
        self.assertEqual(elements[0].token.type, TokenType.LITERAL_INT)
        self.assertEqual(elements[0].token.value, 10)
        self.assertEqual(elements[1].token.type, TokenType.LITERAL_FLOAT)
        self.assertAlmostEqual(elements[1].token.value, 3.14)
        self.assertEqual(elements[2].token.type, TokenType.LITERAL_STRING)
        self.assertEqual(elements[2].token.value, "text")
        self.assertEqual(elements[3].token.type, TokenType.KEYWORD_TRUE)
        self.assertEqual(elements[4].token.type, TokenType.KEYWORD_FALSE)
        self.assertEqual(elements[5].token.type, TokenType.KEYWORD_NULL)


if __name__ == '__main__':
    unittest.main(argv=['first-arg-is-ignored'], exit=False)