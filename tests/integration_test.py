import unittest
import io
from dataclasses import fields, is_dataclass

from source.reader import SourceReader
from source.cleaner import Cleaner
from source.lexer import Lexer
from source.parser import Parser
from source.nodes import *
from source.utils import (
    UnexpectedTokenException,
    UnterminatedStringException,
    InvalidEscapeSequenceException,
    Config, 
    Position,
)

class TestLexerParserIntegration(unittest.TestCase):
    def assertNodesEqual(self, actual, expected, msg=None):
        if type(actual) != type(expected):
            self.fail(self._formatMessage(msg, f"Node types differ: {type(actual).__name__} vs {type(expected).__name__}"))

        if is_dataclass(actual):
            for f in fields(actual):
                if f.name in ('start_position', 'end_position'):
                    continue

                actual_value = getattr(actual, f.name)
                expected_value = getattr(expected, f.name)

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
                    # For non-Node values
                    self.assertEqual(actual_value, expected_value,
                                     self._formatMessage(msg, f"Field '{f.name}' mismatch in {type(actual).__name__}: {actual_value!r} != {expected_value!r}"))
        else:
            # For non-dataclass types (e.g., int, str, bool, None)
            self.assertEqual(actual, expected, msg)


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
        
        expected_node = ProgramNode(
            start_position=Position(0,0), 
            end_position=Position(0,0),
            statements=[]
        )
        self.assertNodesEqual(program_node, expected_node)

    def test_variable_declaration_int_integration(self):
        code = "int x = 10;"
        parser = self._create_parser_from_string(code)
        program_node = parser.parse()
        
        expected_type_node = TypeNode(Position(0,0), Position(0,0), "int")
        expected_value_node = LiteralNode(Position(0,0), Position(0,0), 10)
        expected_stmt = VariableDeclarationNode(
            start_position=Position(0,0), end_position=Position(0,0),
            var_type=expected_type_node,
            identifier_name="x",
            value=expected_value_node
        )
        expected_program = ProgramNode(
            start_position=Position(0,0), end_position=Position(0,0),
            statements=[expected_stmt]
        )
        self.assertNodesEqual(program_node, expected_program)

    def test_variable_declaration_float_integration(self):
        code = "float pi = 3.14;"
        parser = self._create_parser_from_string(code)
        program_node = parser.parse()
        
        expected_type_node = TypeNode(Position(0,0), Position(0,0), "float")
        expected_value_node = LiteralNode(Position(0,0), Position(0,0), 3.14)
        expected_stmt = VariableDeclarationNode(
            start_position=Position(0,0), end_position=Position(0,0),
            var_type=expected_type_node,
            identifier_name="pi",
            value=expected_value_node
        )
        expected_program = ProgramNode(
            start_position=Position(0,0), end_position=Position(0,0),
            statements=[expected_stmt]
        )
        self.assertNodesEqual(program_node, expected_program)

    def test_variable_declaration_string_with_escapes_integration(self):
        code = 'string path = "C:\\\\new\\\\folder\\\\file.txt\\n";'
        parser = self._create_parser_from_string(code)
        program_node = parser.parse()
        
        expected_type_node = TypeNode(Position(0,0), Position(0,0), "string")
        expected_value_node = LiteralNode(Position(0,0), Position(0,0), "C:\\new\\folder\\file.txt\n")
        expected_stmt = VariableDeclarationNode(
            start_position=Position(0,0), end_position=Position(0,0),
            var_type=expected_type_node,
            identifier_name="path",
            value=expected_value_node
        )
        expected_program = ProgramNode(
            start_position=Position(0,0), end_position=Position(0,0),
            statements=[expected_stmt]
        )
        self.assertNodesEqual(program_node, expected_program)

    def test_variable_declaration_bool_false_integration(self):
        code = "bool isDone = false;"
        parser = self._create_parser_from_string(code)
        program_node = parser.parse()
        
        expected_type_node = TypeNode(Position(0,0), Position(0,0), "bool")
        expected_value_node = LiteralNode(Position(0,0), Position(0,0), "false")
        expected_stmt = VariableDeclarationNode(
            start_position=Position(0,0), end_position=Position(0,0),
            var_type=expected_type_node,
            identifier_name="isDone",
            value=expected_value_node
        )
        expected_program = ProgramNode(
            start_position=Position(0,0), end_position=Position(0,0),
            statements=[expected_stmt]
        )
        self.assertNodesEqual(program_node, expected_program)

    def test_variable_declaration_list_of_strings_integration(self):
        code = 'List<string> names = ["Alice", "Bob", "Charlie"];'
        parser = self._create_parser_from_string(code)
        program_node = parser.parse()
        
        expected_child_type = TypeNode(Position(0,0), Position(0,0), "string")
        expected_list_type = ListTypeNode(Position(0,0), Position(0,0), "List", expected_child_type)

        expected_alice = LiteralNode(Position(0,0), Position(0,0), "Alice")
        expected_bob = LiteralNode(Position(0,0), Position(0,0), "Bob")
        expected_charlie = LiteralNode(Position(0,0), Position(0,0), "Charlie")
        expected_list_literal = ListLiteralNode(
            start_position=Position(0,0), end_position=Position(0,0),
            elements=[expected_alice, expected_bob, expected_charlie]
        )

        expected_stmt = VariableDeclarationNode(
            start_position=Position(0,0), end_position=Position(0,0),
            var_type=expected_list_type,
            identifier_name="names",
            value=expected_list_literal
        )
        expected_program = ProgramNode(
            start_position=Position(0,0), end_position=Position(0,0),
            statements=[expected_stmt]
        )
        self.assertNodesEqual(program_node, expected_program)

    def test_assignment_to_member_access_integration(self):
        code = "myObject.property.value = 100;"
        parser = self._create_parser_from_string(code)
        program_node = parser.parse()
        
        expected_obj = IdentifierNode(Position(0,0), Position(0,0), "myObject")
        expected_prop = MemberAccessNode(Position(0,0), Position(0,0), expected_obj, "property")
        expected_lhs = MemberAccessNode(Position(0,0), Position(0,0), expected_prop, "value")
        expected_value = LiteralNode(Position(0,0), Position(0,0), 100)
        expected_stmt = AssignmentNode(
            start_position=Position(0,0), end_position=Position(0,0),
            identifier=expected_lhs,
            value=expected_value
        )
        expected_program = ProgramNode(
            start_position=Position(0,0), end_position=Position(0,0),
            statements=[expected_stmt]
        )
        self.assertNodesEqual(program_node, expected_program)

    def test_function_call_with_expression_argument_integration(self):
        code = 'calculate(value1 + value2, 10 * 2);'
        parser = self._create_parser_from_string(code)
        program_node = parser.parse()
        
        expected_func_name = IdentifierNode(Position(0,0), Position(0,0), "calculate")
        
        expected_arg0_left = IdentifierNode(Position(0,0), Position(0,0), "value1")
        expected_arg0_right = IdentifierNode(Position(0,0), Position(0,0), "value2")
        expected_arg0 = AddNode(Position(0,0), Position(0,0), expected_arg0_left, expected_arg0_right)

        expected_arg1_left = LiteralNode(Position(0,0), Position(0,0), 10)
        expected_arg1_right = LiteralNode(Position(0,0), Position(0,0), 2)
        expected_arg1 = MultiplyNode(Position(0,0), Position(0,0), expected_arg1_left, expected_arg1_right)

        expected_call_expr = FunctionCallNode(
            start_position=Position(0,0), end_position=Position(0,0),
            function_name=expected_func_name,
            arguments=[expected_arg0, expected_arg1]
        )
        expected_stmt = FunctionCallStatementNode(
            start_position=Position(0,0), end_position=Position(0,0),
            call_expression=expected_call_expr
        )
        expected_program = ProgramNode(
            start_position=Position(0,0), end_position=Position(0,0),
            statements=[expected_stmt]
        )
        self.assertNodesEqual(program_node, expected_program)

    def test_if_else_integration(self):
        code = """
        if (score > 90) {
            grade = "A";
        } else {
            grade = "B";
        }
        """
        parser = self._create_parser_from_string(code)
        program_node = parser.parse()
        
        expected_if_cond_left = IdentifierNode(Position(0,0), Position(0,0), "score")
        expected_if_cond_right = LiteralNode(Position(0,0), Position(0,0), 90)
        expected_if_cond = GreaterThanNode(Position(0,0), Position(0,0), expected_if_cond_left, expected_if_cond_right)

        expected_if_assign_ident = IdentifierNode(Position(0,0), Position(0,0), "grade")
        expected_if_assign_value = LiteralNode(Position(0,0), Position(0,0), "A")
        expected_if_assign_stmt = AssignmentNode(Position(0,0), Position(0,0), expected_if_assign_ident, expected_if_assign_value)
        
        expected_if_block = CodeBlockNode(Position(0,0), Position(0,0), [expected_if_assign_stmt])

        expected_else_assign_ident = IdentifierNode(Position(0,0), Position(0,0), "grade")
        expected_else_assign_value = LiteralNode(Position(0,0), Position(0,0), "B")
        expected_else_assign_stmt = AssignmentNode(Position(0,0), Position(0,0), expected_else_assign_ident, expected_else_assign_value)
        
        expected_else_block = CodeBlockNode(Position(0,0), Position(0,0), [expected_else_assign_stmt])
        
        expected_if_stmt = IfStatementNode(
            start_position=Position(0,0), end_position=Position(0,0),
            condition=expected_if_cond,
            if_block=expected_if_block,
            else_block=expected_else_block
        )
        expected_program = ProgramNode(
            start_position=Position(0,0), end_position=Position(0,0),
            statements=[expected_if_stmt]
        )
        self.assertNodesEqual(program_node, expected_program)

    def test_while_loop_with_break_like_construct_integration(self):
        code = """
        while (isRunning && count < max_count) {
            process();
            count = count + 1;
        }
        """
        parser = self._create_parser_from_string(code)
        program_node = parser.parse()

        expected_cond_left = IdentifierNode(Position(0,0), Position(0,0), "isRunning")
        expected_cond_inner_left = IdentifierNode(Position(0,0), Position(0,0), "count")
        expected_cond_inner_right = IdentifierNode(Position(0,0), Position(0,0), "max_count")
        expected_cond_inner = LessThanNode(Position(0,0), Position(0,0), expected_cond_inner_left, expected_cond_inner_right)
        expected_condition = LogicalAndNode(Position(0,0), Position(0,0), expected_cond_left, expected_cond_inner)

        expected_process_func_name = IdentifierNode(Position(0,0), Position(0,0), "process")
        expected_process_call = FunctionCallNode(Position(0,0), Position(0,0), expected_process_func_name, [])
        expected_process_stmt = FunctionCallStatementNode(Position(0,0), Position(0,0), expected_process_call)

        expected_assign_ident = IdentifierNode(Position(0,0), Position(0,0), "count")
        expected_add_left = IdentifierNode(Position(0,0), Position(0,0), "count")
        expected_add_right = LiteralNode(Position(0,0), Position(0,0), 1)
        expected_add_expr = AddNode(Position(0,0), Position(0,0), expected_add_left, expected_add_right)
        expected_assign_stmt = AssignmentNode(Position(0,0), Position(0,0), expected_assign_ident, expected_add_expr)

        expected_body = CodeBlockNode(
            start_position=Position(0,0), end_position=Position(0,0),
            statements=[expected_process_stmt, expected_assign_stmt]
        )

        expected_while_stmt = WhileLoopNode(
            start_position=Position(0,0), end_position=Position(0,0),
            condition=expected_condition,
            body=expected_body
        )
        expected_program = ProgramNode(
            start_position=Position(0,0), end_position=Position(0,0),
            statements=[expected_while_stmt]
        )
        self.assertNodesEqual(program_node, expected_program)

    def test_function_definition_list_param_and_constructor_return_integration(self):
        code = """
        func File createFile(List<string> parts) {
            string path = parts.join("/"); /* Assume List has join method */
            return File(path);
        }
        """
        parser = self._create_parser_from_string(code)
        program_node = parser.parse()
        
        expected_return_type = TypeNode(Position(0,0), Position(0,0), "File")
        expected_param_child_type = TypeNode(Position(0,0), Position(0,0), "string")
        expected_param_type = ListTypeNode(Position(0,0), Position(0,0), "List", expected_param_child_type)
        expected_param = ParameterNode(Position(0,0), Position(0,0), expected_param_type, "parts")

        expected_var_type = TypeNode(Position(0,0), Position(0,0), "string")
        expected_join_obj = IdentifierNode(Position(0,0), Position(0,0), "parts")
        expected_join_arg = LiteralNode(Position(0,0), Position(0,0), "/")
        expected_join_call_func_name = MemberAccessNode(Position(0,0), Position(0,0), expected_join_obj, "join")
        expected_join_call = FunctionCallNode(Position(0,0), Position(0,0), expected_join_call_func_name, [expected_join_arg])
        expected_var_decl = VariableDeclarationNode(
            start_position=Position(0,0), end_position=Position(0,0),
            var_type=expected_var_type, identifier_name="path", value=expected_join_call
        )

        expected_file_ctor_arg = IdentifierNode(Position(0,0), Position(0,0), "path")
        expected_file_ctor = ConstructorCallNode(Position(0,0), Position(0,0), "File", [expected_file_ctor_arg])
        expected_return_stmt = ReturnStatementNode(Position(0,0), Position(0,0), expected_file_ctor)
        
        expected_body = CodeBlockNode(
            start_position=Position(0,0), end_position=Position(0,0),
            statements=[expected_var_decl, expected_return_stmt]
        )
        
        expected_func_def = FunctionDefinitionNode(
            start_position=Position(0,0), end_position=Position(0,0),
            return_type=expected_return_type,
            identifier_name="createFile",
            parameters=[expected_param],
            body=expected_body
        )
        expected_program = ProgramNode(
            start_position=Position(0,0), end_position=Position(0,0),
            statements=[expected_func_def]
        )
        self.assertNodesEqual(program_node, expected_program)

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
        
        expected_func_def_ret_type = TypeNode(Position(0,0), Position(0,0), "void")
        expected_func_def_body_stmt1_type = TypeNode(Position(0,0), Position(0,0), "int")
        expected_func_def_body_stmt1_value = LiteralNode(Position(0,0), Position(0,0), 1)
        expected_func_def_body_stmt1 = VariableDeclarationNode(
            start_position=Position(0,0), end_position=Position(0,0),
            var_type=expected_func_def_body_stmt1_type,
            identifier_name="a", value=expected_func_def_body_stmt1_value
        )
        
        expected_func_def_body_stmt2_type = TypeNode(Position(0,0), Position(0,0), "int")
        expected_func_def_body_stmt2_value = LiteralNode(Position(0,0), Position(0,0), 3)
        expected_func_def_body_stmt2 = VariableDeclarationNode(
            start_position=Position(0,0), end_position=Position(0,0),
            var_type=expected_func_def_body_stmt2_type,
            identifier_name="c", value=expected_func_def_body_stmt2_value
        )

        expected_print_call_func_name = IdentifierNode(Position(0,0), Position(0,0), "print")
        expected_print_call_arg_left = IdentifierNode(Position(0,0), Position(0,0), "a")
        expected_print_call_arg_right = IdentifierNode(Position(0,0), Position(0,0), "c")
        expected_print_call_arg = AddNode(Position(0,0), Position(0,0), expected_print_call_arg_left, expected_print_call_arg_right)
        expected_print_call = FunctionCallNode(
            start_position=Position(0,0), end_position=Position(0,0),
            function_name=expected_print_call_func_name, arguments=[expected_print_call_arg]
        )
        expected_print_stmt = FunctionCallStatementNode(
            start_position=Position(0,0), end_position=Position(0,0),
            call_expression=expected_print_call
        )
        
        expected_return_stmt = ReturnStatementNode(
            start_position=Position(0,0), end_position=Position(0,0), value=None
        )

        expected_func_def_body = CodeBlockNode(
            start_position=Position(0,0), end_position=Position(0,0),
            statements=[
                expected_func_def_body_stmt1,
                expected_func_def_body_stmt2,
                expected_print_stmt,
                expected_return_stmt
            ]
        )
        
        expected_func_def = FunctionDefinitionNode(
            start_position=Position(0,0), end_position=Position(0,0),
            return_type=expected_func_def_ret_type,
            identifier_name="main",
            parameters=[],
            body=expected_func_def_body
        )
        expected_program = ProgramNode(
            start_position=Position(0,0), end_position=Position(0,0),
            statements=[expected_func_def]
        )
        self.assertNodesEqual(program_node, expected_program)


    def test_lexer_parser_error_unterminated_string(self):
        code = 'string error = "this is not closed;'
        parser = self._create_parser_from_string(code)
        with self.assertRaises(UnterminatedStringException):
            parser.parse()

    def test_lexer_parser_error_invalid_escape(self):
        code = 'string error = "this has invalid escape \\x";'
        parser = self._create_parser_from_string(code)
        with self.assertRaises(InvalidEscapeSequenceException):
            parser.parse()

    def test_parser_error_unexpected_eof_in_expression(self):
        code = "int x = 10 + "
        parser = self._create_parser_from_string(code)
        with self.assertRaisesRegex(UnexpectedTokenException, "Expected start of a factor but found EOF"):
            parser.parse()

    def test_parser_error_missing_function_body_brace(self):
        code = "func void test() return;"
        parser = self._create_parser_from_string(code)
        with self.assertRaisesRegex(UnexpectedTokenException, "Expected LBRACE but found KEYWORD_RETURN"):
            parser.parse()

    def test_all_literal_types_in_list_integration(self):
        code = "List<void> mixed = [10, 3.14, \"text\", true, false, null];"
        parser = self._create_parser_from_string(code)
        program_node = parser.parse()
        
        expected_child_type = TypeNode(Position(0,0), Position(0,0), "void")
        expected_list_type = ListTypeNode(Position(0,0), Position(0,0), "List", expected_child_type)

        expected_elements = [
            LiteralNode(Position(0,0), Position(0,0), 10),
            LiteralNode(Position(0,0), Position(0,0), 3.14),
            LiteralNode(Position(0,0), Position(0,0), "text"),
            LiteralNode(Position(0,0), Position(0,0), "true"),
            LiteralNode(Position(0,0), Position(0,0), "false"),
            LiteralNode(Position(0,0), Position(0,0), "null"),
        ]
        expected_list_literal = ListLiteralNode(
            start_position=Position(0,0), end_position=Position(0,0),
            elements=expected_elements
        )

        expected_stmt = VariableDeclarationNode(
            start_position=Position(0,0), end_position=Position(0,0),
            var_type=expected_list_type,
            identifier_name="mixed",
            value=expected_list_literal
        )
        expected_program = ProgramNode(
            start_position=Position(0,0), end_position=Position(0,0),
            statements=[expected_stmt]
        )
        self.assertNodesEqual(program_node, expected_program)


if __name__ == '__main__':
    unittest.main(argv=['first-arg-is-ignored'], exit=False)