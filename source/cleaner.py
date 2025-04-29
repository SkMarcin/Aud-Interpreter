import os
import sys

current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)

from typing import Optional, Tuple, TextIO
from .utils import Config, LexerException
from .reader import SourceReader

# --- Whitespace, Line Ending and Comment Handler ---

class Cleaner:
    """Cleans Reader output to only characters relevant to the lexer"""
    def __init__(self, reader: SourceReader, config: Config):
        self._reader = reader
        self._config = config

    def get_char(self) -> Optional[str]:
        """
        Reads from the SourceReader, skips whitespace and comments,
        and returns the first significant character found.
        Returns None if EOF is reached after skipping.
        """
        while True:
            char = self._reader.get_char()

            if char is None:
                return None

            # Skip Whitespace
            if char.isspace():
                continue

            # Check Comment Start '/'
            if char == '/':
                if self._reader.peek_char() == '*':
                    self._reader.get_char() # Consume '*'
                    comment_start_line, comment_start_col = self._reader.current_pos()
                    comment_len = 0
                    while True:
                        inner_char = self._reader.get_char()
                        if inner_char is None:
                            raise LexerException("Unterminated comment", comment_start_line, comment_start_col)

                        # Check for Comment End '*/'
                        if inner_char == '*' and self._reader.peek_char() == '/':
                            self._reader.get_char() # Consume '/'
                            break

                        comment_len += 1
                        if comment_len > self._config.max_comment_length:
                            raise LexerException(f"Maximum comment length exceeded ({self._config.max_comment_length})", comment_start_line, comment_start_col)

                    continue
                else:
                    # It's not a comment '/'
                    return char
            else:
                # Character is not whitespace and not the start of a comment
                return char

    def peek_char(self, k: int = 1) -> Optional[str]:
        """Call reader peek char method"""
        return self._reader.peek_char(k)
