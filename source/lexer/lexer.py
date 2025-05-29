import os
import io
import sys
from typing import Optional, Dict, Iterator

current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)

from source.lexer.cleaner import Cleaner
from source.lexer.reader import SourceReader
from source.tokens import Token, TokenType
from source.utils import (
    UnterminatedStringException,
    MaxStringLengthException,
    InvalidEscapeSequenceException,
    MaxIdentifierLengthException,
    InvalidCharacterException,
    MaxNumberLengthException,
    InvalidFloatValueException,
    Config,
    Position,
)

TOKEN_BUILDERS = {
    '=': lambda self, position: setattr(
        self, 'current_token',
        Token(TokenType.OP_EQ if self._reader.peek_char() == '=' else TokenType.OP_ASSIGN,
              '==' if self._reader.peek_char() == '=' else '=', position)
    ),
    '!': lambda self, position: setattr(
        self, 'current_token',
        Token(TokenType.OP_NEQ, '!=', position) if self._reader.peek_char() == '='
        else (_ for _ in ()).throw(InvalidCharacterException(self.current_char, position))
    ),
    '<': lambda self, position: setattr(
        self, 'current_token',
        Token(TokenType.OP_LTE if self._reader.peek_char() == '=' else TokenType.OP_LT,
              '<=' if self._reader.peek_char() == '=' else '<', position)
    ),
    '>': lambda self, position: setattr(
        self, 'current_token',
        Token(TokenType.OP_GTE if self._reader.peek_char() == '=' else TokenType.OP_GT,
              '>=' if self._reader.peek_char() == '=' else '>', position)
    ),
    '&': lambda self, position: setattr(
        self, 'current_token',
        Token(TokenType.OP_AND, '&&', position) if self._reader.peek_char() == '&'
        else (_ for _ in ()).throw(InvalidCharacterException(self.current_char, position))
    ),
    '|': lambda self, position: setattr(
        self, 'current_token',
        Token(TokenType.OP_OR, '||', position) if self._reader.peek_char() == '|'
        else (_ for _ in ()).throw(InvalidCharacterException(self.current_char, position))
    ),
    '+': lambda self, position: setattr(self, 'current_token', Token(TokenType.OP_PLUS, '+', position)),
    '-': lambda self, position: setattr(self, 'current_token', Token(TokenType.OP_MINUS, '-', position)),
    '*': lambda self, position: setattr(self, 'current_token', Token(TokenType.OP_MULTIPLY, '*', position)),
    '/': lambda self, position: setattr(self, 'current_token', Token(TokenType.OP_DIVIDE, '/', position)),
    '(': lambda self, position: setattr(self, 'current_token', Token(TokenType.LPAREN, '(', position)),
    ')': lambda self, position: setattr(self, 'current_token', Token(TokenType.RPAREN, ')', position)),
    '{': lambda self, position: setattr(self, 'current_token', Token(TokenType.LBRACE, '{', position)),
    '}': lambda self, position: setattr(self, 'current_token', Token(TokenType.RBRACE, '}', position)),
    '[': lambda self, position: setattr(self, 'current_token', Token(TokenType.LBRACKET, '[', position)),
    ']': lambda self, position: setattr(self, 'current_token', Token(TokenType.RBRACKET, ']', position)),
    ',': lambda self, position: setattr(self, 'current_token', Token(TokenType.COMMA, ',', position)),
    ';': lambda self, position: setattr(self, 'current_token', Token(TokenType.SEMICOLON, ';', position)),
    '.': lambda self, position: setattr(self, 'current_token', Token(TokenType.DOT, '.', position)),
}

class Lexer:
    """
    Generates a stream of tokens from a SourceReader.
    """
    KEYWORDS: Dict[str, TokenType] = {
        "func": TokenType.KEYWORD_FUNC,
        "int": TokenType.KEYWORD_INT,
        "float": TokenType.KEYWORD_FLOAT,
        "bool": TokenType.KEYWORD_BOOL,
        "string": TokenType.KEYWORD_STRING,
        "Folder": TokenType.KEYWORD_FOLDER,
        "File": TokenType.KEYWORD_FILE,
        "Audio": TokenType.KEYWORD_AUDIO,
        "List": TokenType.KEYWORD_LIST,
        "if": TokenType.KEYWORD_IF,
        "else": TokenType.KEYWORD_ELSE,
        "while": TokenType.KEYWORD_WHILE,
        "return": TokenType.KEYWORD_RETURN,
        "true": TokenType.KEYWORD_TRUE,
        "false": TokenType.KEYWORD_FALSE,
        "void": TokenType.KEYWORD_VOID,
        "null": TokenType.KEYWORD_NULL,
    }

    ESCAPE_CHARS: Dict[str, str] = {
        '"': '"',
        '\\': '\\',
        'n': '\n',
        't': '\t',
        'r': '\r',
    }

    def __init__(self, reader: SourceReader, cleaner: Cleaner, config: Optional[Config] = None):
        self._reader = reader
        self._cleaner = cleaner
        self._config = config if config else Config()
        self.current_token: Token = None
        self.current_char: str = None

    def _read_identifier(self) -> Token:
        """Reads an identifier or keyword."""
        value = []
        position = self._reader.current_pos()
        if not (self.current_char.isalpha() or self.current_char == '_'):
            return False

        while self.current_char is not None and (self.current_char.isalnum() or self.current_char == '_'):
            if len(value) == self._config.max_identifier_length:
                raise MaxIdentifierLengthException(self._config.max_identifier_length, position)
            value.append(self.current_char)
            self.current_char = self._reader.get_char()

        str_value = ''.join(value)

        token_type = self.KEYWORDS.get(str_value, TokenType.IDENTIFIER)
        self.current_token = Token(token_type, str_value, position)

        return True

    def _build_number(self, value: int, num_fractional: int, position: Position):
        if num_fractional > 0:
            try:
                divisor = 10.0 ** num_fractional
                value = ( float(value) / divisor )
                self.current_token = Token(TokenType.LITERAL_FLOAT, value, position)
                return True
            except ValueError:
                raise InvalidFloatValueException(f"Invalid float literal: {value}", position)
        else:
            self.current_token = Token(TokenType.LITERAL_INT, value, position)
            return True

    def _read_number(self) -> Token:
        """Reads an integer or float literal."""
        is_float = False
        value: int = 0
        num_fractional_digits: int = 0
        position = self._reader.current_pos()
        length: int = 0

        if not self.current_char.isdecimal() or self.current_char == '.':
            return False

        if self.current_char == '0' and self._reader.peek_char() != '.':
            self.current_token = Token(TokenType.LITERAL_INT, 0, position)

        while self.current_char is not None and (self.current_char.isdecimal() or self.current_char == '.'):
            if length == self._config.max_number_length:
                raise MaxNumberLengthException(self._config.max_number_length, position)

            if self.current_char.isdecimal():
                digit = int(self.current_char)
                value = value * 10 + digit
                length += 1
                if is_float:
                    num_fractional_digits += 1

            elif not is_float:
                # Check if the char after '.' is a digit
                peeked = self._reader.peek_char()
                if peeked is not None and peeked.isdecimal():
                    is_float = True
                else:
                    self._build_number(value, num_fractional_digits, position)
                    return True

            else:
                self._build_number(value, num_fractional_digits, position)
                return True

            self.current_char = self._reader.get_char()

        self._build_number(value, num_fractional_digits, position)
        return True


    def _read_string(self) -> bool:
        """Reads a string literal enclosed in double quotes."""
        string = []
        escape_char = None
        position = self._reader.current_pos()

        if self.current_char != '"':
            return False

        self.current_char = self._reader.get_char()

        while self.current_char != '"':
            if self.current_char is None:
                raise UnterminatedStringException(position)

            if self.current_char == '\\':
                escape_char = self._reader.get_char()
                if escape_char is None:
                    raise UnterminatedStringException(position)

                try:
                    self.current_char = self.ESCAPE_CHARS[escape_char]
                except KeyError:
                    raise InvalidEscapeSequenceException(escape_char, position)

            if len(string) == self._config.max_string_length:
                raise MaxStringLengthException(self._config.max_string_length, position)
            else:
                string.append(self.current_char)

            self.current_char = self._reader.get_char()

        string_value = "".join(string)
        self.current_token = Token(TokenType.LITERAL_STRING, string_value, position)
        self.current_char = self._cleaner.get_char()
        return True

    def _read_simple_token(self) -> bool:
        position = self._reader.current_pos()
        if self.current_char in TOKEN_BUILDERS:
            TOKEN_BUILDERS[self.current_char](self, position)
            self.current_char = self._cleaner.get_char()
            if len(self.current_token.value) > 1:
                self.current_char = self._cleaner.get_char()
            return True
        else:
            return False

    def get_next_token(self) -> Token:
        """Reads and returns the next token from the source."""
        if self.current_char is None or self.current_char.isspace():
            self.current_char = self._cleaner.get_char()
        position = self._reader.current_pos()

        if not self.current_char:
            return Token(TokenType.EOF, None, position)

        if self._read_identifier() or self._read_number() or self._read_string() or self._read_simple_token():
            return self.current_token

        raise InvalidCharacterException(f"Invalid character: {self.current_char}", position)

    def get_current_pos(self) -> Position:
        return self._reader.current_pos()

    def __iter__(self) -> Iterator[Token]:
        """Allows iterating through the tokens."""
        while True:
            token = self.get_next_token()
            yield token
            if token.type == TokenType.EOF:
                break

# --- Example Usage ---

if __name__ == "__main__":
    # Example with a string source
    code_string = """
/* This is a block comment
    spanning multiple lines */
func int add(int x, float y) {
    string message = "Processing...";
    print(message);
    int result = x * ftoi(y) + 10; /* Inline comment */
    if (result > 100 && x != 0) {
        return result;
    } else {
        /* bool flag = true; */
        return -1;
    }
}

float value = 123.45;
List<int> numbers = [1, 2, 3];
int final_val = calculate(5, value);
File f = File("test.txt"); /* Constructor */
f.change_filename("new_name.doc");
int err = 1.2.3; /* Invalid float *//
/* Unterminated
    """

    print("--- Lexing from string ---")
    config = Config()
    code_stream = io.StringIO(code_string)
    reader = SourceReader(code_stream)
    cleaner = Cleaner(reader, config)
    lexer_str = Lexer(reader, cleaner, config)
    for token in lexer_str:
        print(token)

    print("\n--- Lexing from file ---")
    file_path = "temp_test_code.txt"
    with open(file_path, "w", encoding="utf-8") as f:
        f.write("int main() {\n")
        f.write("  print(\"Hello from file!\\r\\n\");\r")
        f.write("  return 0;\n")
        f.write("}\n")

    try:
        with open(file_path, "r", encoding="utf-8") as code_file:
            lexer_file = Lexer(code_file)
            for token in lexer_file:
                print(token)
    except Exception as e:
        print(f"Error reading file: {e}")
    finally:
        try:
            os.remove(file_path)
        except OSError:
            pass