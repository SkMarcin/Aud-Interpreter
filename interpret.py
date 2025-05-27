import argparse
import io
import sys
from source.lexer import Lexer
from source.reader import SourceReader
from source.cleaner import Cleaner
from source.parser import Parser
from source.utils import Config
from source.interpreter.interpreter import Interpreter

parser = argparse.ArgumentParser(description="Run the lexer or compiler.")
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
    with open(args.file, "r", encoding="utf-8") as code_file:
        reader = SourceReader(code_file)
        cleaner = Cleaner(reader, config)
        file_lexer = Lexer(reader, cleaner, config)
        parser = Parser(file_lexer)
        program = parser.parse()
        interpreter = Interpreter()
        interpreter.interpret_program(program)

    code_file.close()
except Exception as e:
    print(f"Error reading file: {e}")