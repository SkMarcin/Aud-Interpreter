import unittest
import io
import os
import shutil
from unittest.mock import patch
from source.lexer import Lexer
from source.reader import SourceReader
from source.cleaner import Cleaner
from source.parser import Parser
from source.interpreter.interpreter import Interpreter
from source.utils import Config


class TestInterpreter(unittest.TestCase):

    def setUp(self):
        self.config = Config()

    def _run_code(self, code_string, input_data=None, config=None):
        current_config = config if config is not None else self.config

        reader = SourceReader(io.StringIO(code_string))
        cleaner = Cleaner(reader, current_config)
        lexer = Lexer(reader, cleaner, current_config)
        parser = Parser(lexer)
        program = parser.parse()

        interpreter = Interpreter(config=current_config)
        if input_data:
            interpreter.set_input_data(input_data)

        with patch('sys.stdout', new_callable=io.StringIO) as mock_stdout, \
             patch('sys.stderr', new_callable=io.StringIO) as mock_stderr:

            interpreter.interpret_program(program)

            captured_stdout = mock_stdout.getvalue()
            captured_stderr = mock_stderr.getvalue()

        return captured_stdout, captured_stderr

    # --- Success Tests ---

    def test_print_string(self):
        output, error = self._run_code('print("Hello World");')
        self.assertEqual(output.strip(), "Hello World")
        self.assertEqual(error.strip(), "")

    def test_variable_declaration_and_print(self):
        output, error = self._run_code('int x = 10; print(itos(x));')
        self.assertEqual(output.strip(), "10")
        self.assertEqual(error.strip(), "")

    def test_arithmetic_operations(self):
        output, error = self._run_code('int x = 5 + 3 * 2 - 1; print(itos(x));')
        self.assertEqual(output.strip(), "10")
        self.assertEqual(error.strip(), "")

    def test_string_concatenation(self):
        output, error = self._run_code('string s = "Hello" + " " + "World"; print(s);')
        self.assertEqual(output.strip(), "Hello World")
        self.assertEqual(error.strip(), "")

    def test_if_else_statement(self):
        output, error = self._run_code('int x = 10; if (x > 5) { print("Greater"); } else { print("Not Greater"); }')
        self.assertEqual(output.strip(), "Greater")
        self.assertEqual(error.strip(), "")

        output, error = self._run_code('int x = 3; if (x > 5) { print("Greater"); } else { print("Not Greater"); }')
        self.assertEqual(output.strip(), "Not Greater")
        self.assertEqual(error.strip(), "")

    def test_while_loop(self):
        code = """
        int i = 0;
        while (i < 3) {
            print(itos(i));
            i = i + 1;
        }
        """
        output, error = self._run_code(code)
        self.assertEqual(output.strip(), "0\n1\n2")
        self.assertEqual(error.strip(), "")

    def test_function_call_and_return(self):
        code = """
        func int add(int a, int b) {
            return a + b;
        }
        int result = add(5, 7);
        print(itos(result));
        """
        output, error = self._run_code(code)
        self.assertEqual(output.strip(), "12")
        self.assertEqual(error.strip(), "")

    def test_function_pass_by_reference_int(self):
        code = """
        func void modify_val(int num) {
            num = num + 10;
        }
        int my_int = 5;
        modify_val(my_int);
        print(itos(my_int));
        """
        output, error = self._run_code(code)
        self.assertEqual(output.strip(), "15")
        self.assertEqual(error.strip(), "")

    def test_function_pass_by_reference_string(self):
        code = """
        func void modify_str(string text) {
            text = text + " World";
        }
        string my_str = "Hello";
        modify_str(my_str);
        print(my_str);
        """
        output, error = self._run_code(code)
        self.assertEqual(output.strip(), "Hello World")
        self.assertEqual(error.strip(), "")

    def test_shadowing_variable(self):
        code = """
        int x = 5;
        if (true) {
            int x = 0; /* Local shadowing */
            print("Inner x: " + itos(x));
        }
        print("Outer x: " + itos(x));
        """
        output, error = self._run_code(code)
        self.assertEqual(output.strip(), "Inner x: 0\nOuter x: 5")
        self.assertEqual(error.strip(), "")

    def test_built_in_conversions(self):
        code = """
        print(itos(stoi("123") + 1));
        print(ftos(stof("4.5") + 0.5));
        print(ftos(itof(10)));
        print(itos(ftoi(10.99)));
        """
        output, error = self._run_code(code)
        self.assertEqual(output.strip(), "124\n5.0\n10.0\n10")
        self.assertEqual(error.strip(), "")

    def test_input_function(self):
        code = """
        string name = input();
        print("Your name is: " + name);
        """
        output, error = self._run_code(code, input_data=["Alice"])
        self.assertEqual(output.strip(), "Your name is: Alice")
        self.assertEqual(error.strip(), "")

    def test_list_creation_and_access(self):
        code = """
        List<int> numbers = [10, 20, 30];
        print(itos(numbers.len()));
        print(itos(numbers.get(1)));
        """
        output, error = self._run_code(code)
        self.assertEqual(output.strip(), "3\n20")
        self.assertEqual(error.strip(), "")

    def test_list_of_complex_types(self):
        with open("tests/a.txt", "w") as file:
            file.write("a")
        with open("tests/b.txt", "w") as file:
            file.write("b")

        code = """
        File f1 = File("tests/a.txt");
        File f2 = File("tests/b.txt");
        List<File> files = [f1, f2];
        print(files.get(0).get_filename());
        """
        output, error = self._run_code(code)
        self.assertEqual(output.strip(), "a.txt")
        self.assertEqual(error.strip(), "")

        if os.path.exists("tests/a.txt"):
            os.remove("tests/a.txt")
        if os.path.exists("tests/b.txt"):
            os.remove("tests/b.txt")

    def test_folder_file_audio_mocks(self):
        if not os.path.exists("tests/music/song.mp3"):
            os.mkdir("tests/music")
        shutil.copyfile("tests/files/my_track.mp3", "tests/music/song.mp3")
        code = """
        Folder music_folder = Folder("tests/music");
        Audio song = Audio("tests/music/song.mp3");
        music_folder.add_file(song);
        print(song.title);
        song.change_title("New Song Title");
        print(song.title);
        List<Audio> audio_files = music_folder.list_audio();
        print(itos(audio_files.len()));
        print(audio_files.get(0).get_filename());
        """
        output, error = self._run_code(code)

        if os.path.exists("tests/music/song.mp3"):
            os.remove("tests/music/song.mp3")
            os.rmdir("tests/music")

        self.assertEqual(output.strip(), "song\nNew Song Title\n1\nsong.mp3")
        self.assertEqual(error.strip(), "")

    def test_file_move_delete(self):
        if not os.path.exists("tests/src"):
            os.mkdir("tests/src")
        if not os.path.exists("tests/dest"):
            os.mkdir("tests/dest")
        with open("tests/document.txt", "w") as file:
            file.write("File not found test")
        code = """
        Folder src =  Folder("tests/src");
        Folder dest =  Folder("tests/dest");
        File doc =  File("tests/document.txt");
        src.add_file(doc);
        print("Src has doc: " + btos(src.get_file("document.txt") != null));

        doc.move(dest);
        print("Src has doc after move: " + btos(src.get_file("document.txt") != null));
        print("Dest has doc: " + btos(dest.get_file("document.txt") != null));

        doc.delete();
        print("Dest has doc after delete: " + btos(dest.get_file("document.txt") != null));
        """
        output, error = self._run_code(code)
        if os.path.exists("tests/src"):
            os.rmdir("tests/src")
        if os.path.exists("tests/dest"):
            os.rmdir("tests/dest")
        if os.path.exists("tests/document.txt"):
            os.remove("tests/document.txt")

        self.assertEqual(output.strip(), "Src has doc: true\nSrc has doc after move: false\nDest has doc: true\nDest has doc after delete: false")
        self.assertEqual(error.strip(), "")


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
        # Title derived from filename might be "my_track"
        self.assertEqual(output.strip(), "Generic filename: my_track.mp3\nConverted audio title: my_track\n[14, 35] ERROR Built-in function 'ftoa' returned type 'null', but expected 'Audio'.")
        self.assertEqual(error.strip(), "")

    # --- Error Tests (Checking stdout now) ---

    def test_invalid_condition_type(self):
        code = 'if (2 + 5) { print("error"); }'
        output, error = self._run_code(code)
        self.assertIn("[1, 5] ERROR If condition: Type mismatch. Expected 'bool', got 'int'", output)
        self.assertEqual(error.strip(), "")


    def test_undeclared_variable(self):
        code = 'int x = 5; y = 3; print(itos(y));'
        output, error = self._run_code(code)
        self.assertIn("[1, 12] ERROR Undeclared variable 'y' referenced.", output)
        self.assertEqual(error.strip(), "")


    def test_invalid_type_assignment(self):
        code = 'int x = "abc";'
        output, error = self._run_code(code)
        self.assertIn("[1, 9] ERROR In declaration of 'x': Type mismatch. Expected 'int', got 'string'.", output)
        self.assertEqual(error.strip(), "")

    def test_type_conversion_exception(self):
        code = 'int x = stoi("abc");'
        output, error = self._run_code(code)
        self.assertIn("[1, 9] ERROR Cannot convert string 'abc' to int.", output)
        self.assertEqual(error.strip(), "")

    def test_file_not_found_on_operation(self):
        with open("tests/temp.txt", "w") as file:
            file.write("File not found test")
        code = """
        File f =  File("tests/temp.txt");
        f.delete(); /* Make the file "not found" by deleting it */
        f.change_filename("new_name.txt"); /* This should trigger the error */
        """
        output, error = self._run_code(code)
        self.assertIn("[4, 9] ERROR Operation 'change_filename' on deleted file 'temp.txt' is not allowed.", output)
        self.assertEqual(error.strip(), "")

        if os.path.exists("tests/temp.txt"):
            os.remove("tests/temp.txt")


    def test_recursion_limit(self):
        code = """
        func int recursion(int value) {
            if (value > 10) { return 0; }
            return 1 + recursion(value + 1);
        }
        int result = recursion(0);
        """
        config_with_limit = Config(max_func_depth=5)
        output, error = self._run_code(code, config=config_with_limit)
        self.assertIn("[4, 24] ERROR Maximum function call depth (5) exceeded.", output)
        self.assertEqual(error.strip(), "")


    def test_division_by_zero(self):
        code = "int x = 10 / 0; print(itos(x));"
        output, error = self._run_code(code)
        self.assertIn("[1, 9] ERROR Division by zero.", output)
        self.assertEqual(error.strip(), "")

    def test_list_index_out_of_bounds(self):
        code = """
        List<int> numbers = [10, 20];
        print(itos(numbers.get(2)));
        """
        output, error = self._run_code(code)
        self.assertIn("[3, 20] ERROR List index 2 out of bounds for list of size 2.", output)
        self.assertEqual(error.strip(), "")

    def test_invalid_argument_type_for_function(self):
        code = """
        func int add(int a, int b) { return a + b; }
        int result = add("hello", 5);
        """
        output, error = self._run_code(code)
        self.assertIn("[3, 26] ERROR Argument for param 'a': Type mismatch. Expected 'int', got 'string'.", output)
        self.assertEqual(error.strip(), "")

    def test_missing_return_value_in_non_void_function(self):
        code = """
        func int get_number() {
            /* Missing return */
        }
        int x = get_number();
        """
        output, error = self._run_code(code)
        self.assertIn("[2, 9] ERROR Function 'get_number' must return a 'int'.", output)
        self.assertEqual(error.strip(), "")

    def test_return_value_in_void_function(self):
        code = """
        func void do_something() {
            return 1; /* Void function returning value */
        }
        do_something();
        """
        output, error = self._run_code(code)
        self.assertIn("[2, 9] ERROR Void function 'do_something' cannot return a value", output)
        self.assertEqual(error.strip(), "")


    def test_null_object_creation(self):
        code = """
        Folder my_folder = null;
        """
        output, error = self._run_code(code)
        self.assertIn("[2, 28] ERROR In declaration of 'my_folder': Type mismatch. Expected 'Folder', got 'null'.", output)
        self.assertEqual(error.strip(), "")


    def test_calling_non_callable_member(self):
        with open("tests/doc.txt", "w") as file:
            file.write("test")

        code = """
        File my_file = File("tests/doc.txt");
        my_file.filename(); /* filename is a property, not a method */
        """
        output, error = self._run_code(code)
        self.assertIn("[3, 9] ERROR Property 'filename' of type 'File' is not callable.", output)
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
        self.assertIn("[3, 23] ERROR Type 'File' has no attribute 'get_filename'.", output)
        self.assertEqual(error.strip(), "")

        if os.path.exists("tests/doc.txt"):
            os.remove("tests/doc.txt")

    def test_ftoa_on_file(self):
        code = """
        Folder current_folder = Folder("tests/files");
        List<File> files_in_folder = current_folder.list_files();
        int i = 1;
        int num_files = files_in_folder.len();

        File current_file = files_in_folder.get(i);
        string filename = current_file.get_filename();

        Audio audio_version = ftoa(current_file);
        print("Processing complete");
        """
        output, error = self._run_code(code)
        self.assertIn("Processing complete", output)
        self.assertEqual(error.strip(), "")


if __name__ == '__main__':
    unittest.main(argv=['first-arg-is-ignored'], exit=False)