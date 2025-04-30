from dataclasses import dataclass
from enum import Enum, auto
from typing import Any
from source.utils import LexerException

# --- Token Definition ---

class TokenType(Enum):
    # Keywords
    KEYWORD_FUNC = auto() 
    KEYWORD_INT = auto() 
    KEYWORD_FLOAT = auto() 
    KEYWORD_BOOL = auto() 
    KEYWORD_STRING = auto() 
    KEYWORD_FOLDER = auto() 
    KEYWORD_FILE = auto() 
    KEYWORD_AUDIO = auto()
    KEYWORD_LIST = auto()
    KEYWORD_IF = auto()
    KEYWORD_ELSE = auto()
    KEYWORD_WHILE = auto()
    KEYWORD_RETURN = auto()
    KEYWORD_TRUE = auto()
    KEYWORD_FALSE = auto()
    KEYWORD_VOID = auto()
    KEYWORD_NULL = auto()

    # Identifier
    IDENTIFIER = auto()

    # Literals
    LITERAL_INT = auto()
    LITERAL_FLOAT = auto()
    LITERAL_STRING = auto()

    # Operators
    OP_ASSIGN = auto()                  # =
    OP_PLUS = auto()                    # +
    OP_MINUS = auto()                   # -
    OP_MULTIPLY = auto()                # *
    OP_DIVIDE = auto()                  # /
    OP_EQ = auto()                      # ==
    OP_NEQ = auto()                     # !=
    OP_LT = auto()                      # <
    OP_LTE = auto()                     # <=
    OP_GT = auto()                      # >
    OP_GTE = auto()                     # >=
    OP_AND = auto()                     # &&
    OP_OR = auto()                      # ||

    # Punctuation
    LPAREN = auto()                     # (
    RPAREN = auto()                     # )
    LBRACE = auto()                     # {
    RBRACE = auto()                     # }
    LBRACKET = auto()                   # [
    RBRACKET = auto()                   # ]
    COMMA = auto()                      # ,
    SEMICOLON = auto()                  # ;
    DOT = auto()                        # .

    # Special
    EOF = auto()                        # End of File/Input

@dataclass
class Token:
    type: TokenType
    value: Any
    line: int
    column: int

    def __repr__(self) -> str:
        return f"Token({self.type.name}, {repr(self.value)}, Ln {self.line}, Col {self.column})"

TOKEN_BUILDERS = {
    '=': lambda self, line, col: setattr(
        self, 'current_token',
        Token(TokenType.OP_EQ if self._cleaner.peek_char() == '=' and self._cleaner.peek_char() is not None else TokenType.OP_ASSIGN,
              '==' if self._cleaner.peek_char() == '=' else '=', line, col)
    ),
    '!': lambda self, line, col: setattr(
        self, 'current_token',
        Token(TokenType.OP_NEQ, '!=', line, col) if self._cleaner.peek_char() == '=' and self._cleaner.peek_char() is not None
        else (_ for _ in ()).throw(LexerException(f"Unexpected character: {self.current_char}", line, col))
    ),
    '<': lambda self, line, col: setattr(
        self, 'current_token',
        Token(TokenType.OP_LTE if self._cleaner.peek_char() == '=' and self._cleaner.peek_char() is not None else TokenType.OP_LT,
              '<=' if self._cleaner.peek_char() == '=' else '<', line, col)
    ),
    '>': lambda self, line, col: setattr(
        self, 'current_token',
        Token(TokenType.OP_GTE if self._cleaner.peek_char() == '=' and self._cleaner.peek_char() is not None else TokenType.OP_GT,
              '>=' if self._cleaner.peek_char() == '=' else '>', line, col)
    ),
    '&': lambda self, line, col: setattr(
        self, 'current_token',
        Token(TokenType.OP_AND, '&&', line, col) if self._cleaner.peek_char() == '&' and self._cleaner.peek_char() is not None
        else (_ for _ in ()).throw(LexerException(f"Unexpected character: {self.current_char}", line, col))
    ),
    '|': lambda self, line, col: setattr(
        self, 'current_token',
        Token(TokenType.OP_OR, '||', line, col) if self._cleaner.peek_char() == '|' and self._cleaner.peek_char() is not None
        else (_ for _ in ()).throw(LexerException(f"Unexpected character: {self.current_char}", line, col))
    ),
    '+': lambda self, line, col: setattr(self, 'current_token', Token(TokenType.OP_PLUS, '+', line, col)),
    '-': lambda self, line, col: setattr(self, 'current_token', Token(TokenType.OP_MINUS, '-', line, col)),
    '*': lambda self, line, col: setattr(self, 'current_token', Token(TokenType.OP_MULTIPLY, '*', line, col)),
    '/': lambda self, line, col: setattr(self, 'current_token', Token(TokenType.OP_DIVIDE, '/', line, col)),
    '(': lambda self, line, col: setattr(self, 'current_token', Token(TokenType.LPAREN, '(', line, col)),
    ')': lambda self, line, col: setattr(self, 'current_token', Token(TokenType.RPAREN, ')', line, col)),
    '{': lambda self, line, col: setattr(self, 'current_token', Token(TokenType.LBRACE, '{', line, col)),
    '}': lambda self, line, col: setattr(self, 'current_token', Token(TokenType.RBRACE, '}', line, col)),
    '[': lambda self, line, col: setattr(self, 'current_token', Token(TokenType.LBRACKET, '[', line, col)),
    ']': lambda self, line, col: setattr(self, 'current_token', Token(TokenType.RBRACKET, ']', line, col)),
    ',': lambda self, line, col: setattr(self, 'current_token', Token(TokenType.COMMA, ',', line, col)),
    ';': lambda self, line, col: setattr(self, 'current_token', Token(TokenType.SEMICOLON, ';', line, col)),
    '.': lambda self, line, col: setattr(self, 'current_token', Token(TokenType.DOT, '.', line, col)),
}