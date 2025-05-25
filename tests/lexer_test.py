import sys
import os
import io
import unittest
from typing import List, Tuple, Any

current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)

from source.reader import SourceReader
from source.cleaner import Cleaner
from source.lexer import Lexer
from source.utils import Config, LexerException
from source.tokens import TokenType

class TestLexer(unittest.TestCase):

    def assert_tokens(self, code: str, expected_tokens: List[Tuple[TokenType, Any]], config: Config = None):
        """Helper method to lex code and compare with expected token tuples."""
        stream = io.StringIO(code)
        reader = SourceReader(stream)
        cleaner = Cleaner(reader, config=config)
        lexer = Lexer(reader=reader, cleaner=cleaner, config=config)
        produced_tokens = []
        try:
            for token in lexer:
                produced_tokens.append((token.type, token.value))
                if token.type == TokenType.EOF:
                    break
        except LexerException as e:
            print(f"Caught LexerException during token generation: {e}")

        # Add EOF if the last expected token isn't already EOF
        full_expected = expected_tokens
        if not expected_tokens or expected_tokens[-1][0] != TokenType.EOF:
            full_expected = expected_tokens + [(TokenType.EOF, None)]

        # Use assertEqual for detailed diffs
        self.assertEqual(produced_tokens, full_expected, f"\nFailed for code:\n---\n{code}\n---")

    def assert_lexer_error(self, code: str, expected_message_part: str, config: Config = None):
        """Helper method to assert that lexing raises a LexerException."""
        stream = io.StringIO(code)
        reader = SourceReader(stream)
        cleaner = Cleaner(reader, config=config)
        lexer = Lexer(reader, cleaner, config=config)
        with self.assertRaises(LexerException) as cm:
            list(lexer)
        self.assertIn(expected_message_part, str(cm.exception),
                      f"\nExpected error containing '{expected_message_part}' for code:\n---\n{code}\n---")

    # --- Basic Token Tests ---

    def test_empty_input(self):
        self.assert_tokens("", [])

    def test_whitespace_only(self):
        self.assert_tokens("   \n\t \r\n  ", [])

    def test_keywords(self):
        code = "func int float bool string Folder File Audio List if else while return true false void null"
        expected = [
            (TokenType.KEYWORD_FUNC, "func"), (TokenType.KEYWORD_INT, "int"),
            (TokenType.KEYWORD_FLOAT, "float"), (TokenType.KEYWORD_BOOL, "bool"),
            (TokenType.KEYWORD_STRING, "string"), (TokenType.KEYWORD_FOLDER, "Folder"),
            (TokenType.KEYWORD_FILE, "File"), (TokenType.KEYWORD_AUDIO, "Audio"),
            (TokenType.KEYWORD_LIST, "List"), (TokenType.KEYWORD_IF, "if"),
            (TokenType.KEYWORD_ELSE, "else"), (TokenType.KEYWORD_WHILE, "while"),
            (TokenType.KEYWORD_RETURN, "return"), (TokenType.KEYWORD_TRUE, "true"),
            (TokenType.KEYWORD_FALSE, "false"), (TokenType.KEYWORD_VOID, "void"),
            (TokenType.KEYWORD_NULL, "null")
        ]
        self.assert_tokens(code, expected)

    def test_identifiers(self):
        code = "myVar _var var123 _123 another_long_identifier FolderVar file_handle"
        expected = [
            (TokenType.IDENTIFIER, "myVar"), (TokenType.IDENTIFIER, "_var"),
            (TokenType.IDENTIFIER, "var123"), (TokenType.IDENTIFIER, "_123"),
            (TokenType.IDENTIFIER, "another_long_identifier"),
            (TokenType.IDENTIFIER, "FolderVar"), (TokenType.IDENTIFIER, "file_handle"),
        ]
        self.assert_tokens(code, expected)

    def test_integers(self):
        code = "0 1 123 9876543210 007"
        expected = [
            (TokenType.LITERAL_INT, 0), (TokenType.LITERAL_INT, 1),
            (TokenType.LITERAL_INT, 123), (TokenType.LITERAL_INT, 9876543210),
            (TokenType.LITERAL_INT, 7),
        ]
        self.assert_tokens(code, expected)

    def test_floats(self):
        code = "1.0 0.5 123.456 987.0 0.0 100.001"
        expected = [
            (TokenType.LITERAL_FLOAT, 1.0), (TokenType.LITERAL_FLOAT, 0.5),
            (TokenType.LITERAL_FLOAT, 123.456), (TokenType.LITERAL_FLOAT, 987.0),
            (TokenType.LITERAL_FLOAT, 0.0), (TokenType.LITERAL_FLOAT, 100.001)
        ]
        self.assert_tokens(code, expected)

    def test_number_followed_by_dot(self):
        # Ensure '1.' is INT then DOT, not treated as part of float
        self.assert_tokens("1.", [(TokenType.LITERAL_INT, 1), (TokenType.DOT, '.')])
        self.assert_tokens("x = 10. ;", [
            (TokenType.IDENTIFIER, 'x'), (TokenType.OP_ASSIGN, '='),
            (TokenType.LITERAL_INT, 10), (TokenType.DOT, '.'),
            (TokenType.SEMICOLON, ';')
        ])
        # Ensure '.5' is DOT then INT
        self.assert_tokens(".5", [(TokenType.DOT, '.'), (TokenType.LITERAL_INT, 5)])


    def test_simple_strings(self):
        self.assert_tokens('""', [(TokenType.LITERAL_STRING, "")])
        self.assert_tokens('"hello"', [(TokenType.LITERAL_STRING, "hello")])
        self.assert_tokens('"hello world with spaces"', [(TokenType.LITERAL_STRING, "hello world with spaces")])

    def test_string_escapes(self):
        code = r'"\" \\ \n \t escapes\"end"'
        expected_str = "\" \\ \n \t escapes\"end"
        self.assert_tokens(code, [(TokenType.LITERAL_STRING, expected_str)])
        self.assert_tokens(r'"\n\t"', [(TokenType.LITERAL_STRING, "\n\t")])

    def test_operators(self):
        code = "= == + - * / != < <= > >= && ||"
        expected = [
            (TokenType.OP_ASSIGN, "="), (TokenType.OP_EQ, "=="), (TokenType.OP_PLUS, "+"),
            (TokenType.OP_MINUS, "-"), (TokenType.OP_MULTIPLY, "*"), (TokenType.OP_DIVIDE, "/"),
            (TokenType.OP_NEQ, "!="), (TokenType.OP_LT, "<"), (TokenType.OP_LTE, "<="),
            (TokenType.OP_GT, ">"), (TokenType.OP_GTE, ">="), (TokenType.OP_AND, "&&"),
            (TokenType.OP_OR, "||")
        ]
        self.assert_tokens(code, expected)

    def test_punctuation(self):
        code = "( ) { } [ ] , ; ."
        expected = [
            (TokenType.LPAREN, "("), (TokenType.RPAREN, ")"), (TokenType.LBRACE, "{"),
            (TokenType.RBRACE, "}"), (TokenType.LBRACKET, "["), (TokenType.RBRACKET, "]"),
            (TokenType.COMMA, ","), (TokenType.SEMICOLON, ";"), (TokenType.DOT, ".")
        ]
        self.assert_tokens(code, expected)

    def test_simple_assignment(self):
        code = "int x = 10;"
        expected = [
            (TokenType.KEYWORD_INT, "int"), (TokenType.IDENTIFIER, "x"),
            (TokenType.OP_ASSIGN, "="), (TokenType.LITERAL_INT, 10),
            (TokenType.SEMICOLON, ";")
        ]
        self.assert_tokens(code, expected)

    def test_function_call(self):
        code = "my_func(arg1, 1.5);"
        expected = [
            (TokenType.IDENTIFIER, "my_func"), (TokenType.LPAREN, "("),
            (TokenType.IDENTIFIER, "arg1"), (TokenType.COMMA, ","),
            (TokenType.LITERAL_FLOAT, 1.5), (TokenType.RPAREN, ")"),
            (TokenType.SEMICOLON, ";")
        ]
        self.assert_tokens(code, expected)

    def test_method_call(self):
        code = "my_obj.do_something(0);"
        expected = [
            (TokenType.IDENTIFIER, "my_obj"), (TokenType.DOT, "."),
            (TokenType.IDENTIFIER, "do_something"), (TokenType.LPAREN, "("),
            (TokenType.LITERAL_INT, 0), (TokenType.RPAREN, ")"),
            (TokenType.SEMICOLON, ";")
        ]
        self.assert_tokens(code, expected)

    def test_mixed_whitespace_and_newlines(self):
        code = "int \t x\n=\r\n 5 ; "
        expected = [
            (TokenType.KEYWORD_INT, "int"), (TokenType.IDENTIFIER, "x"),
            (TokenType.OP_ASSIGN, "="), (TokenType.LITERAL_INT, 5),
            (TokenType.SEMICOLON, ";")
        ]
        self.assert_tokens(code, expected)

    def test_block_comment(self):
        code = "/* this is a comment */ int y = 1;"
        expected = [
            (TokenType.KEYWORD_INT, "int"), (TokenType.IDENTIFIER, "y"),
            (TokenType.OP_ASSIGN, "="), (TokenType.LITERAL_INT, 1),
            (TokenType.SEMICOLON, ";")
        ]
        self.assert_tokens(code, expected)

    def test_multiline_block_comment(self):
        code = "a /* multi \n line \n comment */ b"
        expected = [(TokenType.IDENTIFIER, 'a'), (TokenType.IDENTIFIER, 'b')]
        self.assert_tokens(code, expected)

    def test_empty_block_comment(self):
        code = "x /**/ y"
        expected = [(TokenType.IDENTIFIER, 'x'), (TokenType.IDENTIFIER, 'y')]
        self.assert_tokens(code, expected)

    def test_comment_at_eof(self):
        code = "int x = 5; /* comment at end */"
        expected = [
             (TokenType.KEYWORD_INT, "int"), (TokenType.IDENTIFIER, "x"),
             (TokenType.OP_ASSIGN, "="), (TokenType.LITERAL_INT, 5),
             (TokenType.SEMICOLON, ";")
        ]
        self.assert_tokens(code, expected)

    def test_code_inside_comment(self):
        code = "/* int z = 10; */ float f = 1.0;"
        expected = [
             (TokenType.KEYWORD_FLOAT, "float"), (TokenType.IDENTIFIER, "f"),
             (TokenType.OP_ASSIGN, "="), (TokenType.LITERAL_FLOAT, 1.0),
             (TokenType.SEMICOLON, ";")
        ]
        self.assert_tokens(code, expected)

    def test_incorrectly_nested_comment(self):
        code = "/* outer /* inner */ value = 5; */ "
        expected_after = [
            (TokenType.IDENTIFIER, "value"), (TokenType.OP_ASSIGN, "="),
            (TokenType.LITERAL_INT, 5), (TokenType.SEMICOLON, ";"),
            (TokenType.OP_MULTIPLY, '*'), (TokenType.OP_DIVIDE, '/')
        ]
        self.assert_tokens(code, expected_after)

    # --- Error Handling ---

    def test_invalid_character(self):
        self.assert_lexer_error("int x = ?;", "Invalid character: ?")
        self.assert_lexer_error("#", "Invalid character: #")
        self.assert_lexer_error("@", "Invalid character: @")

    def test_unterminated_string(self):
        self.assert_lexer_error('"hello', "Unterminated string")
        self.assert_lexer_error('"hello\\', "Unterminated string")

    def test_unterminated_comment(self):
        self.assert_lexer_error("int x = 5; /* unending", "Unterminated comment")

    def test_invalid_escape_sequence(self):
        self.assert_lexer_error(r'"\z"', "Invalid escape sequence: \\z")

    def test_number_format_errors(self):
        self.assert_tokens("1.2.3", [
            (TokenType.LITERAL_FLOAT, 1.2),
            (TokenType.DOT, '.'),
            (TokenType.LITERAL_INT, 3)
        ])

    def test_lone_ampersand_pipe(self):
        self.assert_lexer_error("int x = 5 & 3;", "Invalid character: &")
        self.assert_lexer_error("bool y = true | false;", "Invalid character: |")

    # --- Length Limits ---

    def test_identifier_length_limit(self):
        config = Config(max_identifier_length=10)
        ok_ident = "a" * 10
        long_ident = "a" * 11
        self.assert_tokens(ok_ident, [(TokenType.IDENTIFIER, ok_ident)], config=config)
        self.assert_lexer_error(long_ident, "Identifier exceeds maximum length (10)", config=config)

    def test_string_length_limit(self):
        config = Config(max_string_length=5)
        ok_str_content = "a" * 5
        long_str_content = "a" * 6
        self.assert_tokens(f'"{ok_str_content}"', [(TokenType.LITERAL_STRING, ok_str_content)], config=config)
        self.assert_lexer_error(f'"{long_str_content}"', "String exceeds maximum length (5)", config=config)
        ok_esc_str = r'"aaaa"'
        long_esc_str = r'"aaaaa"'
        too_long_esc_str = r'"aaaaaa"'
        self.assert_tokens(ok_esc_str, [(TokenType.LITERAL_STRING, "a"*4)], config=config)
        self.assert_tokens(long_esc_str, [(TokenType.LITERAL_STRING, "a"*5)], config=config)
        self.assert_lexer_error(too_long_esc_str, "String exceeds maximum length (5)", config=config)

    def test_comment_length_limit(self):
        config = Config(max_comment_length=10)
        ok_comment = "a" * 10
        long_comment = "a" * 11
        self.assert_tokens(f"/*{ok_comment}*/ int x=1;", [(TokenType.KEYWORD_INT,'int'), (TokenType.IDENTIFIER,'x'),(TokenType.OP_ASSIGN,'='),(TokenType.LITERAL_INT,1),(TokenType.SEMICOLON,';')], config=config)
        self.assert_lexer_error(f"/*{long_comment}*/", "Maximum comment length exceeded (10)", config=config)

    def test_number_length_limit(self):
        config = Config(max_number_length=10)
        ok_number = "1234567890;"
        long_number = "12345678900;"
        self.assert_tokens(ok_number, [(TokenType.LITERAL_INT,1234567890),(TokenType.SEMICOLON,';')], config=config)
        self.assert_lexer_error(long_number, "Number exceeds maximum length (10)", config=config)


if __name__ == '__main__':
    unittest.main(argv=['first-arg-is-ignored'], exit=False)