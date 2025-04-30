import io
from typing import Optional, TextIO, Tuple

# --- Source Reader ---

class SourceReader:
    """
    Reads characters lazily from a file or string, normalizes line endings,
    and tracks the current position (line, column).
    """
    def __init__(self, source: TextIO):
        self._stream = source
        self._peeked_chars: list[str] = []
        self._eof_reached: bool = False
        self.line: int = 1
        self.column: int = 0

    def _advance(self) -> Optional[str]:
        """
        Returns the next character, from the list if it was peeked previously 
        or otherwise from the stream.
        """
        if self._peeked_chars:
            return self._peeked_chars.pop(0)

        if self._eof_reached:
            return None

        char = self._stream.read(1)

        if not char:
            self._eof_reached = True
            return None

        return char

    def peek_char(self, k: int = 1) -> Optional[str]:
        """Looks ahead k characters and stores them in list for later use. Returns None if EOF."""
        if k <= 0:
            return None

        while len(self._peeked_chars) < k and not self._eof_reached:
            char = self._stream.read(1)
            if char:
                self._peeked_chars.append(char)
            else:
                self._eof_reached = True

        if len(self._peeked_chars) < k:
            return None
        else:
            return self._peeked_chars[k-1]

    def get_char(self) -> Optional[str]:
        """
        Gets the next character, normalizing line endings (\r, \n, \r\n -> \n)
        and updating the position. Returns char or None if EOF.
        """
        char = self._advance()

        if char is None:
            return None

        if char == '\r':
            next_char_peeked = self.peek_char(1)
            if next_char_peeked == '\n':
                self._advance()
                char = '\n'
            else:
                char = '\n'

        if char == '\n':
            self.line += 1
            self.column = 0
        else:
            self.column += 1

        return char

    def current_pos(self) -> Tuple[int, int]:
        """Returns the current (line, column) position."""
        return self.line, self.column
