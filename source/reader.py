import io
from typing import Optional, TextIO, Tuple

# --- Source Reader ---

class SourceReader:
    """
    Reads characters lazily from a file or string, normalizes line endings,
    and tracks the current position (line, column).
    """
    def __init__(self, source: str | TextIO, buffer_size: int = 10):
        if isinstance(source, str):
            self._stream = io.StringIO(source)
            self._is_file = False
        else:
            self._stream = source
            self._is_file = True

        self._buffer: list[str] = []
        self._buffer_size = buffer_size
        self._eof_reached: bool = False

    def _fill_buffer(self, amount: int = 1):
        """Fills the buffer with at least 'amount' characters if possible."""
        if self._eof_reached:
            return
        needed = max(0, amount - len(self._buffer))
        if needed > 0:
            read_chars = self._stream.read(max(needed, self._buffer_size))
            if not read_chars:
                self._eof_reached = True
            self._buffer.extend(list(read_chars))

    def _advance(self) -> Optional[str]:
        """Consumes and returns the next character from the buffer, refilling if necessary."""
        self._fill_buffer(1)
        if not self._buffer:
            return None
        char = self._buffer.pop(0)
        return char

    def peek_char(self, k: int = 1) -> Optional[str]:
        """Looks ahead k characters without consuming. Returns None if EOF."""
        self._fill_buffer(k)
        if k > len(self._buffer):
            return None
        return self._buffer[k-1]

    def get_char(self) -> Optional[str]:
        """
        Gets the next significant character, normalizing line endings (\r, \n, \r\n -> \n)
        and updating the position. Returns (char, line, col) or None if EOF.
        """
        char = self._advance()

        if char is None:
            return None 

        return char

    def current_pos(self) -> Tuple[int, int]:
        """Returns the current (line, column) position."""
        return self.line, self.column

    def close(self):
        """Closes the underlying stream if it's a file."""
        if self._is_file and not self._stream.closed:
            self._stream.close()
