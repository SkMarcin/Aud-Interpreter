from dataclasses import dataclass

class LexerException(Exception):
    def __init__(self, message, line, column):
        super().__init__(f'[{line}, {column}] ERROR {message}')

@dataclass
class Config:
    max_identifier_length: int = 128
    max_string_length: int = 256
    max_comment_length: int = 256