import copy

from dataclasses import dataclass
from enum import Enum, auto
from typing import Any

@dataclass
class Position:
    line: int
    column: int

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

    def __str__(self):
        return self.name

@dataclass
class Token:
    type: TokenType
    value: Any
    code_position: Position

    def __init__(self, type: TokenType, value: Any, code_position: Position):
        self.type = type
        self.value = value
        self.code_position = copy.deepcopy(code_position)

    def __repr__(self) -> str:
        return f"Token({self.type.name}, {repr(self.value)}, Ln {self.code_position.line}, Col {self.code_position.column})"

