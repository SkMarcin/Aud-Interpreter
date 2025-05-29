import unittest
import io
import os
from unittest.mock import patch
from source.lexer.lexer import Lexer
from source.lexer.reader import SourceReader
from source.lexer.cleaner import Cleaner
from source.parser.parser import Parser
from source.type_checker.type_checker import TypeChecker
from source.utils import Config

class TestTypeChecking(unittest.TestCase):

    def setUp(self):
        self.config = Config()

    def _run_type_check(self, code_string, config=None):
        current_config = config if config is not None else self.config

        reader = SourceReader(io.StringIO(code_string))
        cleaner = Cleaner(reader, current_config)
        lexer = Lexer(reader, cleaner, current_config)
        parser = Parser(lexer)
        program = parser.parse()
        type_checker = TypeChecker()

        with patch('sys.stdout', new_callable=io.StringIO) as mock_stdout, \
             patch('sys.stderr', new_callable=io.StringIO) as mock_stderr:

            type_checker.check(program)

            captured_stdout = mock_stdout.getvalue()
            captured_stderr = mock_stderr.getvalue()

        return captured_stdout, captured_stderr

    # --- Success Tests ---

    def test_correct_variable_declaration_and_usage(self):
        code = """
        int x = 10;
        string s = "hello";
        bool b = true;
        float f = 1.0;
        print(itos(x));
        print(s);
        print(btos(b));
        print(ftos(f));
        """
        output, errors = self._run_type_check(code)
        self.assertEqual(output, "")

    def test_correct_function_definition_and_call(self):
        code = f"""
        func int add(int a, int b) {{ return a + b; }}
        int result = add(1, 2);

        func void process_file(File f) {{
            print(f.get_filename());
            return;
        }}
        File my_file = File("path");
        process_file(my_file);
        """
        output, errors = self._run_type_check(code)
        self.assertEqual(errors, "")

    def test_list_operations_correct_types(self):
        code = f"""
        List<int> numbers = [1, 2, 3];
        int len = numbers.len();
        int first = numbers.get(0);

        List<File> files = [];
        File f = File("path");
        List<File> files_with_one = [f];
        File f_retrieved = files_with_one.get(0);
        """
        output, errors = self._run_type_check(code)
        self.assertEqual(errors, "")

    def test_null_assignment_to_nullable_types(self):
        code = f"""
        File f = null;
        Folder fol = null;
        Audio aud = null;
        string s = null;
        List<int> li = null;

        f = File("path");
        if (f != null) {{ print("f not null"); }}
        """
        output, errors = self._run_type_check(code)
        self.assertEqual(errors, "")

    def test_shadowing_type_resolution_correct(self):
        code = """
        int x = 10;
        if (true) {
            string x = "hello";
            print(x); /* x is string here */
        }
        print(itos(x)); /* x is int here */
        """
        output, errors = self._run_type_check(code)
        self.assertEqual(errors, "")

    def test_audio_inherits_file_methods_tc(self):
        code = f"""
        Audio aud = Audio("path");
        string fname = aud.get_filename();
        Folder p = aud.parent;
        aud.change_title("new title");
        """
        output, errors = self._run_type_check(code)
        self.assertEqual(errors, "")

    def test_atof_ftoa_type_checking_correct(self):
        code = f"""
        Audio a = Audio("path");
        File f_from_a = atof(a);

        File f = File("path");
        Audio a_from_f = ftoa(f);
        """
        output, errors = self._run_type_check(code)
        self.assertEqual(errors, "")

    def test_atof_ftoa_conversions(self):
        code = """
        Audio audio_file =  Audio("tests/files/my_track.mp3");
        File generic_file = atof(audio_file);
        print("Generic filename: " + generic_file.get_filename());

        Audio converted_audio = ftoa(generic_file);
        if (converted_audio != null) {
            print("Converted audio title: " + converted_audio.title);
        } else {
            print("Conversion to audio failed.");
        }

        File non_audio_file = File("tests/files/image.jpg");
        Audio failed_conversion = ftoa(non_audio_file);
        """
        output, error = self._run_type_check(code)
        print(output)
        self.assertEqual(output.strip(), "")
        self.assertEqual(error.strip(), "")

    # --- Failure ---

    def test_return_type_mismatch(self):
        code = """
        func int get_string() {
            return "hello"; /* Error: expected int, got string */
        }
        """
        output, errors = self._run_type_check(code)
        self.assertIn("ERROR Type checking: Function declared to return 'int', but attempting to return 'string'.", output)

    def test_return_with_value_in_void_function(self):
        code = """
        func void do_stuff() {
            return 123; /* Error: void function returning value */
        }
        """
        output, errors = self._run_type_check(code)
        self.assertIn("ERROR Type checking: Function declared to return 'void', but attempting to return 'int'.", output)

    def test_return_without_value_in_non_void_function(self):
        code = """
        func int get_num() {
            return; /* Error: non-void function returning void/null */
        }
        """
        output, errors = self._run_type_check(code)
        self.assertIn("ERROR Type checking: Function declared to return 'int', but attempting to return 'void'.", output)

    def test_invalid_condition_type(self):
        code = 'if (2 + 5) { print("error"); }'
        output, error = self._run_type_check(code)
        self.assertIn("[1, 5] ERROR Type checking: If statement condition must be of type 'bool', got 'int'.", output)
        self.assertEqual(error.strip(), "")

    def test_operator_type_mismatch_addition(self):
        code = 'int x = 1 + "error";'
        output, errors = self._run_type_check(code)
        self.assertIn("ERROR Type checking: Operator '+' not defined for types 'int' and 'string'.", output)

    def test_operator_type_mismatch_comparison(self):
        code = 'bool b = 1 < "error";'
        output, errors = self._run_type_check(code)
        self.assertIn("ERROR Type checking: Operator '<' not defined for types 'int' and 'string'.", output)

    def test_undeclared_variable(self):
        code = 'int x = 5; y = 3; print(itos(y));'
        output, error = self._run_type_check(code)
        self.assertIn("[1, 12] ERROR Type checking: Undeclared variable 'y' referenced.", output)
        self.assertEqual(error.strip(), "")

    def test_function_redeclaration_tc(self):
        code = """
        func void f() {}
        func int f() { return 1; } /* Error: function f already defined */
        """
        output,errors = self._run_type_check(code)
        self.assertIn("ERROR Type checking: Function 'f' already defined.", output)

    def test_undefined_function_call_tc(self):
        code = 'undefined_func();'
        output, errors = self._run_type_check(code)
        self.assertIn("ERROR Type checking: Undefined function 'undefined_func' called.", output)


    def test_invalid_type_assignment(self):
        code = 'int x = "abc";'
        output, error = self._run_type_check(code)
        self.assertIn("[1, 9] ERROR Type checking: Cannot assign expression of type 'string' to variable 'x' of type 'int'.", output)
        self.assertEqual(error.strip(), "")

    def test_invalid_argument_type_for_function(self):
        code = """
        func int add(int a, int b) { return a + b; }
        int result = add("hello", 5);
        """
        output, error = self._run_type_check(code)
        self.assertIn("[3, 26] ERROR Type checking: Argument 1 for function/method 'add': expected type 'int', got 'string'.", output)
        self.assertEqual(error.strip(), "")

    def test_incorrect_argument_count_user_function(self):
        code = """
        func void takes_one(int a) {}
        takes_one(1, 2); /* Error: too many arguments */
        """
        output, errors = self._run_type_check(code)
        self.assertIn("ERROR Type checking: Function/method 'takes_one' expected 1 arguments, but got 2.", output)

    def test_access_non_existent_property(self):
        code = f"""
        File f = File("path");
        int bad = f.non_existent_property;
        """
        output, errors = self._run_type_check(code)
        self.assertIn("ERROR Type checking: Type 'File' has no accessible property 'non_existent_property'.", output)

    def test_call_non_existent_method(self):
        code = f"""
        File f = File("path");
        f.non_existent_method();
        """
        output, errors = self._run_type_check(code)
        self.assertIn("ERROR Type checking: Type 'File' has no method 'non_existent_method'.", output)

    def test_list_type_mismatch_declaration(self):
        code = 'List<int> numbers = ["a", "b"];'
        output, errors = self._run_type_check(code)
        self.assertIn("ERROR Type checking: Cannot assign expression of type 'List<string>' to variable 'numbers' of type 'List<int>'.", output)

    def test_list_element_type_inconsistency(self):
        code = 'List<int> mixed_list = [1, "error", 3];'
        output, errors = self._run_type_check(code)
        self.assertIn("ERROR Type checking: List literal elements must be of compatible types. Element 2 has type 'string', expected compatible with 'int'.", output)

    def test_constructor_invalid_argument_type(self):
        code = 'File f = File(123); /* Error: File constructor expects string path */'
        output, errors = self._run_type_check(code)
        self.assertIn("ERROR Type checking: Constructor 'File' expects a 'string' argument, got 'int'.", output)

    def test_null_assignment_to_non_nullable_type(self):
        code = 'int x = null;'
        output, errors = self._run_type_check(code)
        self.assertIn("ERROR Type checking: Cannot assign expression of type 'null' to variable 'x' of type 'int'.", output)

    def test_file_method_not_on_folder(self):
        code = """
        Folder fol = Folder(".");
        fol.get_filename(); /* get_filename is on File/Audio, not Folder */
        """
        output, errors = self._run_type_check(code)
        self.assertIn("ERROR Type checking: Type 'Folder' has no method 'get_filename'.", output)

    def test_calling_non_callable_member(self):
        with open("tests/doc.txt", "w") as file:
            file.write("test")

        code = """
        File my_file = File("tests/doc.txt");
        my_file.filename(); /* filename is a property, not a method */
        """
        output, error = self._run_type_check(code)
        self.assertIn("[3, 9] ERROR Type checking: Type 'File' has no method 'filename'.", output)
        self.assertEqual(error.strip(), "")

        if os.path.exists("tests/doc.txt"):
            os.remove("tests/doc.txt")

    def test_accessing_method_as_property(self):
        with open("tests/doc.txt", "w") as file:
            file.write("test")

        code = """
        File my_file = File("tests/doc.txt");
        string name = my_file.get_filename; /* get_filename is a method, not a property */
        """
        output, error = self._run_type_check(code)
        self.assertIn("[3, 23] ERROR Type checking: Type 'File' has no accessible property 'get_filename'.", output)
        self.assertEqual(error.strip(), "")

        if os.path.exists("tests/doc.txt"):
            os.remove("tests/doc.txt")