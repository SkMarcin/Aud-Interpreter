import unittest
import io
import os
from unittest.mock import patch
from source.lexer import Lexer
from source.reader import SourceReader
from source.cleaner import Cleaner
from source.parser import Parser
from source.type_checker.type_checker import TypeChecker
from source.utils import Config

class TestTypeChecking(unittest.TestCase):

    def setUp(self):
        self.config = Config()

    def _run_code(self, code_string, config=None):
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

    def test_atof_ftoa_conversions_mocked(self):
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
        output, error = self._run_code(code)
        print(output)
        self.assertEqual(output.strip(), "")
        self.assertEqual(error.strip(), "")

    # --- Failure ---

    def test_invalid_condition_type(self):
        code = 'if (2 + 5) { print("error"); }'
        output, error = self._run_code(code)
        self.assertIn("[1, 5] ERROR Type checking: If statement condition must be of type 'bool', got 'int'.", output)
        self.assertEqual(error.strip(), "")


    def test_undeclared_variable(self):
        code = 'int x = 5; y = 3; print(itos(y));'
        output, error = self._run_code(code)
        self.assertIn("[1, 12] ERROR Type checking: Undeclared variable 'y' referenced.", output)
        self.assertEqual(error.strip(), "")


    def test_invalid_type_assignment(self):
        code = 'int x = "abc";'
        output, error = self._run_code(code)
        self.assertIn("[1, 9] ERROR Type checking: Cannot assign expression of type 'string' to variable 'x' of type 'int'.", output)
        self.assertEqual(error.strip(), "")

    def test_invalid_argument_type_for_function(self):
        code = """
        func int add(int a, int b) { return a + b; }
        int result = add("hello", 5);
        """
        output, error = self._run_code(code)
        self.assertIn("[3, 26] ERROR Type checking: Argument 1 for function/method 'add': expected type 'int', got 'string'.", output)
        self.assertEqual(error.strip(), "")

    def test_calling_non_callable_member(self):
        with open("tests/doc.txt", "w") as file:
            file.write("test")

        code = """
        File my_file = File("tests/doc.txt");
        my_file.filename(); /* filename is a property, not a method */
        """
        output, error = self._run_code(code)
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
        output, error = self._run_code(code)
        self.assertIn("[3, 23] ERROR Type checking: Type 'File' has no accessible property 'get_filename'.", output)
        self.assertEqual(error.strip(), "")

        if os.path.exists("tests/doc.txt"):
            os.remove("tests/doc.txt")