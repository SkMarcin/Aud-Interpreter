import sys
import os
from io import StringIO

current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)

from source.lexer.reader import SourceReader
from source.lexer.cleaner import Cleaner
from source.lexer.lexer import Lexer
from source.parser.parser import Parser
from source.interpreter.interpreter import Interpreter
from source.parser.nodes import ProgramNode
from source.utils import Config



code = """
string test = input();
int x = 20;
func int double_it(int n) {
    n = n * 2;
    return n;
}
int y = 20;
y = double_it(x); /* x should become 20, y should become 40 */
print("x is: " + itos(x));
print("y is: " + itos(y));
"""
code2 = """
Folder root = Folder("my_music");
Audio song1 = Audio("beat.mp3");
Audio song2 = Audio("melody.wav");
root.add_file(song1);
root.add_file(song2);

List<File> files_in_root = root.list_files();
print("Files in root: " + itos(files_in_root.len())); /* Assuming .len works like attribute */

if (files_in_root.len > 0) {
    File first_file = files_in_root.get(0); /* Assuming .get(idx) works */
    print("First file: " + first_file.get_filename());
}

"""

config = Config()
code_stream = StringIO(code)
reader = SourceReader(code_stream)
cleaner = Cleaner(reader, config)
lexer = Lexer(reader, cleaner, config)
parser = Parser(lexer)
program_ast: ProgramNode = parser.parse()

if program_ast:
    from source.visitor import ASTPrinter
    printer = ASTPrinter()
    printer.visit(program_ast)

    interpreter = Interpreter()
    result = interpreter.interpret_program(program_ast)
    print(result)