import argparse
import io
import sys
from source.lexer.lexer import Lexer
from source.lexer.reader import SourceReader
from source.lexer.cleaner import Cleaner
from source.parser.parser import Parser
from source.utils import Config
from source.interpreter.interpreter import Interpreter
from source.type_checker.type_checker import TypeChecker
from source.parser.visitor import ASTPrinter

parser = argparse.ArgumentParser(description="Run the lexer, parser, type checker or compiler.")
parser.add_argument('-c', '--config', type=str, help='Path to the configuration file')

input_type = parser.add_mutually_exclusive_group()
input_type.add_argument('-f', '--file', type=str, help='Path to the input source code file')
input_type.add_argument('-s', '--string', type=str, help='Source code string passed directly')


mode = parser.add_mutually_exclusive_group()
mode.add_argument('-l', '--lex', action='store_true', help='Only lex the source and display tokens')
mode.add_argument('-p', '--parse', action='store_true', help='Only parse the source and display AST tree')
mode.add_argument('-t', '--type-check', action='store_true', help='Only perform type checking')
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

                if args.lex:
                    for token in file_lexer:
                        print(token)
                else:
                    parser_instance = Parser(file_lexer)
                    program = parser_instance.parse()

                    if args.parse:
                        printer = ASTPrinter(indent_char="| ")
                        printer.visit(program)
                    elif args.type_check:
                        type_checker = TypeChecker()
                        type_checker.check(program)
                    else:
                        type_checker = TypeChecker()
                        type_checker.check(program)
                        interpreter = Interpreter()
                        interpreter.interpret_program(program)

        except OSError as e:
            print(f"Error reading file: {e}")
            sys.exit(1)
    elif args.string:
        print("Using source code string.")
        stream = io.StringIO(args.string)
        reader = SourceReader(stream)
        cleaner = Cleaner(reader, config)
        lexer_str = Lexer(reader, cleaner, config)

        if args.lex:
            for token in lexer_str:
                print(token)
        else:
            parser_instance = Parser(lexer_str)
            program = parser_instance.parse()

            if args.parse:
                printer = ASTPrinter(indent_char="| ")
                printer.visit(program)
            elif args.type_check:
                type_checker = TypeChecker()
                type_checker.check(program)
            else:
                type_checker = TypeChecker()
                type_checker.check(program)
                interpreter = Interpreter()
                interpreter.interpret_program(program)
    else:
        parser.error("No source code provided. Use -s or -f.")

except Exception as e:
    print(e)
    sys.exit(1)
