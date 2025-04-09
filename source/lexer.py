import os
from typing import TextIO, Optional, Dict, Iterator
from reader import SourceReader
from cleaner import Cleaner
from tokens import Token, TokenType
from utils import LexerException, Config

# --- Lexer ---

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

    def __init__(self, source: str | TextIO, config: Optional[Config] = None):
        self._reader = SourceReader(source)
        self._config = config if config else Config()
        self._cleaner = Cleaner(self._reader, self._config)

    def _read_identifier(self, first_char: str, line: int, col: int) -> Token:
        """Reads an identifier or keyword."""
        ident = first_char
        while True:
            peeked = self._reader.peek_char()
            if peeked is not None and (peeked.isalnum() or peeked == '_'):
                char_data = self._cleaner.get_char()
                ident += char_data[0]
                if len(ident) > self._config.max_identifier_length:
                     raise LexerException(f"Identifier exceeds maximum length ({self._config.max_identifier_length})", line, col)
            else:
                break
        token_type = self.KEYWORDS.get(ident, TokenType.IDENTIFIER)
        if token_type == TokenType.KEYWORD_TRUE:
             return Token(token_type, True, line, col)
        if token_type == TokenType.KEYWORD_FALSE:
             return Token(token_type, False, line, col)

        return Token(token_type, ident, line, col)

    def _read_number(self, first_char: str, line: int, col: int) -> Token:
        """Reads an integer or float literal."""
        is_float = False
        integer_part: int = int(first_char)
        fractional_part: int = 0
        num_fractional_digits: int = 0

        while True:
            peeked = self._reader.peek_char()
            if peeked is not None and peeked.isdecimal():
                digit = int(self._cleaner.get_char()[0])
                if is_float:
                    fractional_part = fractional_part * 10 + digit
                    num_fractional_digits += 1
                else:
                    integer_part = integer_part * 10 + digit

            elif peeked == '.' and not is_float:
                # Check if the char after '.' is a digit
                peeked2 = self._reader.peek_char(2)
                if peeked2 is not None and peeked2.isdecimal():
                    is_float = True
                    self._cleaner.get_char()[0]
                else:
                    break
            else:
                break

        if is_float:
            try:
                divisor = 10.0 ** num_fractional_digits
                float_value = float(integer_part) + ( float(fractional_part) / divisor )
                return Token(TokenType.LITERAL_FLOAT, float_value, line, col)
            except ValueError:
                 raise LexerException(f"Invalid float literal: {float_value}", line, col)
        else:
            try:
                return Token(TokenType.LITERAL_INT, integer_part, line, col)
            except ValueError:
                 raise LexerException(f"Invalid integer literal: {integer_part}", line, col)

    def _read_string(self, line: int, col: int) -> Token:
        """Reads a string literal enclosed in double quotes."""
        string_val = ""
        while True:
            char, char_line, char_col = self._cleaner.get_char()
            if char is None:
                raise LexerException("Unterminated string", line, col)

            if char == '\\':
                escape_char_data = self._cleaner.get_char()
                if escape_char_data is None:
                    raise LexerException("Unterminated string", char_line, char_col)

                escape_char, _, _ = escape_char_data

                if escape_char == '"':
                    string_val += '"'
                elif escape_char == '\\':
                    string_val += '\\'
                elif escape_char == 'n':
                    string_val += '\n'
                elif escape_char == 't':
                    string_val += '\t'
                elif escape_char == 'r':
                    string_val += '\r'

                else:
                    raise LexerException(f"Invalid escape sequence: \\{escape_char}", char_line, char_col)

            elif char == '"':
                break
            else:
                string_val += char

            if len(string_val) > self._config.max_string_length:
                 raise LexerException("String too long", line, col)

        return Token(TokenType.LITERAL_STRING, string_val, line, col)


    def get_next_token(self) -> Token:
        """Reads and returns the next token from the source."""
        char_data = self._cleaner.get_char()
        if char_data is None:
            line, col = self._cleaner.line, self._cleaner.column
            return Token(TokenType.EOF, None, line, col)

        char, line, col = char_data

        if char.isalpha() or char == '_':
            return self._read_identifier(char, line, col)

        if char.isdecimal():
            return self._read_number(char, line, col)

        if char == '"':
            return self._read_string(line, col)

        # Operators and Punctuation
        if char == '=':
            if self._reader.peek_char() == '=':
                self._cleaner.get_char() # Consume '='
                return Token(TokenType.OP_EQ, "==", line, col)
            return Token(TokenType.OP_ASSIGN, "=", line, col)
        if char == '!':
            if self._reader.peek_char() == '=':
                self._cleaner.get_char() # Consume '='
                return Token(TokenType.OP_NEQ, "!=", line, col)
            raise LexerException(f"Unexpected character: {char}", line, col)
        if char == '<':
            if self._reader.peek_char() == '=':
                self._cleaner.get_char() # Consume '='
                return Token(TokenType.OP_LTE, "<=", line, col)
            return Token(TokenType.OP_LT, "<", line, col)
        if char == '>':
            if self._reader.peek_char() == '=':
                self._cleaner.get_char() # Consume '='
                return Token(TokenType.OP_GTE, ">=", line, col)
            return Token(TokenType.OP_GT, ">", line, col)
        if char == '&':
            if self._reader.peek_char() == '&':
                self._cleaner.get_char() # Consume '&'
                return Token(TokenType.OP_AND, "&&", line, col)
            raise LexerException(f"Unexpected character: {char}", line, col)
        if char == '|':
            if self._reader.peek_char() == '|':
                self._cleaner.get_char() # Consume '|'
                return Token(TokenType.OP_OR, "||", line, col)
            raise LexerException(f"Unexpected character: {char}", line, col)

        if char == '+': return Token(TokenType.OP_PLUS, "+", line, col)
        if char == '-': return Token(TokenType.OP_MINUS, "-", line, col)
        if char == '*': return Token(TokenType.OP_MULTIPLY, "*", line, col)
        if char == '/': return Token(TokenType.OP_DIVIDE, "/", line, col)
        if char == '(': return Token(TokenType.LPAREN, "(", line, col)
        if char == ')': return Token(TokenType.RPAREN, ")", line, col)
        if char == '{': return Token(TokenType.LBRACE, "{", line, col)
        if char == '}': return Token(TokenType.RBRACE, "}", line, col)
        if char == '[': return Token(TokenType.LBRACKET, "[", line, col)
        if char == ']': return Token(TokenType.RBRACKET, "]", line, col)
        if char == ',': return Token(TokenType.COMMA, ",", line, col)
        if char == ';': return Token(TokenType.SEMICOLON, ";", line, col)
        if char == '.': return Token(TokenType.DOT, ".", line, col)

        raise LexerException(f"Invalid character: {char}", line, col)

    def __iter__(self) -> Iterator[Token]:
        """Allows iterating through the tokens."""
        while True:
            try:
                token = self.get_next_token()
            except LexerException as e:
                print(e)
                break
            yield token
            if token.type == TokenType.EOF:
                break
        self._reader.close()

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
    lexer_str = Lexer(code_string)
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