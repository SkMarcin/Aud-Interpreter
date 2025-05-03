import json
from dataclasses import dataclass

class LexerException(Exception):
    def __init__(self, message, line, column):
        self.line = line
        self.column = column
        self.message = message
        super().__init__(f'[{line}, {column}] ERROR {message}')

# Comment Exceptions
class UnterminatedCommentException(LexerException):
    def __init__(self, line, column):
        message = "Unterminated comment"
        super().__init__(message, line, column)

class MaxCommentLengthException(LexerException):
    def __init__(self, length, line, column):
        message = f"Maximum comment length exceeded ({length})"
        super().__init__(message, line, column)

# String Exceptions
class UnterminatedStringException(LexerException):
    def __init__(self, line, column):
        message = "Unterminated string"
        super().__init__(message, line, column)

class MaxStringLengthException(LexerException):
    def __init__(self, length, line, column):
        message = f"String exceeds maximum length ({length})"
        super().__init__(message, line, column)

class InvalidEscapeSequenceException(LexerException):
    def __init__(self, symbol, line, column):
        message = f"Invalid escape sequence: \\{symbol}"
        super().__init__(message, line, column)

# Identifier Exceptions
class MaxIdentifierLengthException(LexerException):
    def __init__(self, length, line, column):
        message = f"Identifier exceeds maximum length ({length})"
        super().__init__(message, line, column)

# Number Exceptions
class MaxNumberLengthException(LexerException):
    def __init__(self, length, line, column):
        message = f"Number exceeds maximum length ({length})"
        super().__init__(message, line, column)

class InvalidFloatValueException(LexerException):
    def __init__(self, value, line, column):
        message = f"Invalid float value: {value}"
        super().__init__(message, line, column)

# Invalid character Exception
class InvalidCharacterException(LexerException):
    def __init__(self, character, line, column):
        message = f"Invalid character: {character}"
        super().__init__(message, line, column)

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