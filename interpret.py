import argparse
import io
import sys
from source.lexer import Lexer
from source.reader import SourceReader
from source.cleaner import Cleaner
from source.parser import Parser
from source.utils import Config
from source.interpreter.interpreter import Interpreter
from source.type_checker.type_checker import TypeChecker

parser = argparse.ArgumentParser(description="Run the lexer or compiler.")
parser.add_argument('-s', '--string', type=str, help='Source code string passed directly')
parser.add_argument('-f', '--file', type=str, help='Path to the input source code file')
parser.add_argument('-c', '--config', type=str, help='Path to the configuration file')
args = parser.parse_args()

if args.config:
    print(f"Using config file: {args.config}")
    try:
        config = Config.from_json_file(args.config)
    except Exception as e:
        print(f"Failed to load config: {e}")
        sys.exit(1)
else:
    config = Config()

try:
    if args.file:
        print(f"Using source file: {args.file}")
        try:
            with open(args.file, "r", encoding="utf-8") as code_file:
                reader = SourceReader(code_file)
                cleaner = Cleaner(reader, config)
                file_lexer = Lexer(reader, cleaner, config)
                parser = Parser(file_lexer)
                program = parser.parse()
                type_checker = TypeChecker()
                type_checker.check(program)
                interpreter = Interpreter()
                interpreter.interpret_program(program)

            code_file.close()
        except OSError as e:
            print(f"Error reading file: {e}")
    else:
        print("Using source code string.")
        stream = io.StringIO(args.string)
        reader = SourceReader(stream)
        cleaner = Cleaner(reader, config)
        lexer_str = Lexer(reader, cleaner, config)
        parser = Parser(lexer_str)
        program = parser.parse()
        interpreter = Interpreter()
        interpreter.interpret_program(program)
except Exception as e:
    print(e)

