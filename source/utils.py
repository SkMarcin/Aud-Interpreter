import json
from dataclasses import dataclass
from source.lexer.tokens import TokenType, Position
from typing import Optional


class LexerException(Exception):
    def __init__(self, message, position: Position):
        self.position: Position = position
        self.message = message
        super().__init__(f'[{self.position.line}, {self.position.column}] ERROR {message}')

# Comment Exceptions
class UnterminatedCommentException(LexerException):
    def __init__(self, position):
        message = "Unterminated comment"
        super().__init__(message, position)

class MaxCommentLengthException(LexerException):
    def __init__(self, length, position):
        message = f"Maximum comment length exceeded ({length})"
        super().__init__(message, position)

# String Exceptions
class UnterminatedStringException(LexerException):
    def __init__(self, position):
        message = "Unterminated string"
        super().__init__(message, position)

class MaxStringLengthException(LexerException):
    def __init__(self, length, position):
        message = f"String exceeds maximum length ({length})"
        super().__init__(message, position)

class InvalidEscapeSequenceException(LexerException):
    def __init__(self, symbol, position):
        message = f"Invalid escape sequence: \\{symbol}"
        super().__init__(message, position)

# Identifier Exceptions
class MaxIdentifierLengthException(LexerException):
    def __init__(self, length, position):
        message = f"Identifier exceeds maximum length ({length})"
        super().__init__(message, position)

# Number Exceptions
class MaxNumberLengthException(LexerException):
    def __init__(self, length, position):
        message = f"Number exceeds maximum length ({length})"
        super().__init__(message, position)

class InvalidFloatValueException(LexerException):
    def __init__(self, value, position):
        message = f"Invalid float value: {value}"
        super().__init__(message, position)

# Invalid character Exception
class InvalidCharacterException(LexerException):
    def __init__(self, character, position):
        message = f"Invalid character: {character}"
        super().__init__(message, position)

# PARSER
class ParserException(Exception):
    def __init__(self, message, position: Position):
        self.position: Position = position
        self.message = message
        super().__init__(f'[{self.position.line}, {self.position.column}] ERROR {message}')

class UnexpectedTokenException(ParserException):
    def __init__(self, position: Position, type: TokenType, expected: Optional[TokenType | str]=None):
        message = f"Unexpected Token {type}"
        if expected:
            message = f"Expected {expected} but found {type}"
        super().__init__(message, position)

class InvalidAssignmentLHS(ParserException):
    def __init__(self, position: Position, type: str):
        message = f"Invalid left-hand side for assignment {type}"
        super().__init__(message, position)

# TYPE CHECKING
class TypeMismatchException(Exception):
    def __init__(self, position: Position, message: str):
        self.position: Position = position
        self.message = message
        super().__init__(f'[{self.position.line}, {self.position.column}] ERROR Type checking: {message}')

# INTERPRETER
class RuntimeException(Exception):
    def __init__(self, message: str, position: Optional[Position] = None):
        self.message = message
        self.position = position
        super().__init__(message)

    def __str__(self):
        if self.position:
            return f'[{self.position.line}, {self.position.column}] ERROR {self.message}'
        return f'[NO_POS] ERROR {self.message}'

@dataclass
class Config:
    max_identifier_length: int = 128
    max_string_length: int = 256
    max_comment_length: int = 256
    max_number_length: int = 128
    max_func_depth: int = 50

    @staticmethod
    def from_json_file(path: str) -> 'Config':
        with open(path, 'r') as f:
            data = json.load(f)
        f.close()
        return Config(**data)

# NEW: Type-checking specific exception


# NEW: Represents a type in the type checker's symbol table
