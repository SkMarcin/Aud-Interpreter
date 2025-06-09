import unittest
import io
import os
import shutil
from unittest.mock import patch
from source.lexer.lexer import Lexer
from source.lexer.reader import SourceReader
from source.lexer.cleaner import Cleaner
from source.parser.parser import Parser
from source.type_checker.type_checker import TypeChecker
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
        type_checker = TypeChecker()
        type_checker.check(program)

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


    # Passing by reference
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

    def test_pass_by_reference_list_mutation(self):
        code = """
        func void add_to_list(List<int> l, int val) {
            /* Assuming List has an 'add' method, or this needs to be adapted */
            l = [val]; /* This rebinds 'l' locally, won't affect caller's list object */
            print("Inside func, list len: " + itos(l.len()));
        }
        List<int> my_list = [10, 20];
        print("Before func, list len: " + itos(my_list.len()));
        add_to_list(my_list, 30);
        print("After func, list len: " + itos(my_list.len())); /* Should still be 2 */
        print(itos(my_list.get(0)));
        """
        output, _ = self._run_code(code)
        self.assertEqual(output.strip(), "Before func, list len: 2\nInside func, list len: 1\nAfter func, list len: 2\n10")

    def test_pass_by_reference_complex_object_mutation(self):
        shutil.copyfile("tests/files/my_track.mp3", "tests/my_track.mp3")
        code = f"""
        func void rename_audio(Audio track) {{
            track.change_title("New Title From Func");
        }}
        Audio my_track = Audio("tests/my_track.mp3");
        print("Original title: " + my_track.title);
        rename_audio(my_track);
        print("Title after func: " + my_track.title);
        """
        output, _ = self._run_code(code)
        if os.path.exists("tests/my_track.mp3"):
            os.remove("tests/my_track.mp3")
        self.assertIn("Original title: my_track", output)
        self.assertIn("Title after func: New Title From Func", output)

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

    # Return tests
    def test_return_in_single_loop(self):
        code = """
        func int find_five() {
            int i = 1;
            while (i < 10) {
                if (i - 5 == 0) {
                    return i;
                }
                i = i + 1;
            }
            return -1; /* Should not reach here if found */
        }
        print(itos(find_five()));
        """
        output, _ = self._run_code(code)
        self.assertEqual(output.strip(), "5")

    def test_return_in_nested_loop(self):
        code = """
        func int find_in_matrix() {
            int i = 0;
            while (i < 3) {
                int j = 0;
                while (j < 3) {
                    if (i == 1 && j == 1) {
                        return i * 10 + j;
                    }
                    j = j + 1;
                }
                i = i + 1;
            }
            return -1;
        }
        print(itos(find_in_matrix()));
        """
        output, _ = self._run_code(code)
        self.assertEqual(output.strip(), "11")

    def test_return_stops_function_execution(self):
        code = """
        func void test_return() {
            print("Before return");
            return;
            print("After return"); /* Should not be printed */
        }
        test_return();
        """
        output, _ = self._run_code(code)
        self.assertEqual(output.strip(), "Before return")

    def test_function_called_multiple_times_in_expression(self):
        code = """
        int counter = 0;
        func int increment_and_get() {
            counter = counter + 1;
            return counter;
        }
        int result = increment_and_get() + increment_and_get(); /* Called twice */
        print(itos(result)); /* Expected 1 + 2 = 3 */
        print(itos(counter)); /* Expected 2 */
        """
        output, _ = self._run_code(code)
        self.assertEqual(output.strip(), "3\n2")

    def test_function_result_consumed_once_via_variable(self):
        code = """
        int counter = 0;
        func int increment_and_get_once() {
            counter = counter + 1;
            print("Function called");
            return counter;
        }
        int val = increment_and_get_once(); /* Called once */
        int result = val + val;
        print(itos(result));
        print(itos(counter));
        """
        output, _ = self._run_code(code)
        self.assertEqual(output.strip(), "Function called\n2\n1")

    def test_operator_precedence_complex(self):
        # Expected: 2 + (3*4) - (10/5) = 2 + 12 - 2 = 12
        output, _ = self._run_code('print(itos(2 + 3 * 4 - 10 / 5));')
        self.assertEqual(output.strip(), "12")
        # Expected: (2 * 3) + (4 / 2) - 1 = 6 + 2 - 1 = 7
        output, _ = self._run_code('print(itos(2 * 3 + 4 / 2 - 1));')
        self.assertEqual(output.strip(), "7")

    def test_operator_associativity_subtraction(self):
        # Expected: (10 - 3) - 2 = 7 - 2 = 5
        output, _ = self._run_code('print(itos(10 - 3 - 2));')
        self.assertEqual(output.strip(), "5")

    def test_operator_associativity_division_multiplication(self):
        # Expected: (100 / 10) / 2 = 10 / 2 = 5
        output, _ = self._run_code('print(itos(100 / 10 / 2));')
        self.assertEqual(output.strip(), "5")
        # Expected: (2 * 3) * 4 = 6 * 4 = 24 (though * is also left-associative)
        output, _ = self._run_code('print(itos(2 * 3 * 4));')
        self.assertEqual(output.strip(), "24")
        # Expected: (100 / 5) * 2 = 20 * 2 = 40
        output, _ = self._run_code('print(itos(100 / 5 * 2));')
        self.assertEqual(output.strip(), "40")

    def test_unary_minus_precedence(self):
        # Expected: (-2) * 3 = -6
        output, _ = self._run_code('print(itos(-2 * 3));')
        self.assertEqual(output.strip(), "-6")
        # Expected: -(2 * 3) = -6
        output, _ = self._run_code('print(itos(-(2 * 3)));')
        self.assertEqual(output.strip(), "-6")
        # Expected: 5 - (-2) = 7
        output, _ = self._run_code('int x = -2; print(itos(5-x));')
        self.assertEqual(output.strip(), "7")

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

        if (failed_conversion != null) {
            print("Bad conversion did not fail.");
        } else {
            print("Conversion to audio failed as expected.");
        }
        """
        output, error = self._run_code(code)
        print(output)
        self.assertEqual(output.strip(), "Generic filename: my_track.mp3\nConverted audio title: my_track\nConversion to audio failed as expected.")
        self.assertEqual(error.strip(), "")

    # --- Error Tests ---

    def test_undeclared_variable(self):
        code = 'int x = 5; y = 3; print(itos(y));'
        output, error = self._run_code(code)
        self.assertIn("[1, 12] ERROR Undeclared variable 'y' referenced.", output)
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

    def test_division_by_zero_variable(self):
        code = "int y = 0; int x = 10 / y;"
        output, _ = self._run_code(code)
        self.assertIn("[1, 20] ERROR Division by zero.", output)

    def test_list_index_out_of_bounds(self):
        code = """
        List<int> numbers = [10, 20];
        print(itos(numbers.get(2)));
        """
        output, error = self._run_code(code)
        self.assertIn("[3, 20] ERROR List index 2 out of bounds for list of size 2.", output)
        self.assertEqual(error.strip(), "")

    def test_access_member_on_null_runtime(self):
        code = """
        File f = null;
        string name = f.filename;
        """
        output, _ = self._run_code(code)
        self.assertIn("ERROR Attempted to access member 'filename' on null object", output)

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