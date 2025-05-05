import json
from dataclasses import dataclass

@dataclass
class Position:
    line: int
    column: int

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

@dataclass
class Config:
    max_identifier_length: int = 128
    max_string_length: int = 256
    max_comment_length: int = 256
    max_number_length: int = 128

    @staticmethod
    def from_json_file(path: str) -> 'Config':
        with open(path, 'r') as f:
            data = json.load(f)
        f.close()
        return Config(**data)