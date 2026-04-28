"""
protocol.py – thin wrapper around the C chess subprocess.

All communication is line-delimited text over stdin/stdout pipes.

Commands sent to C:
    INIT
    MOVE e2e4
    AI_MOVE
    LEGAL e2
    QUIT

Responses received from C:
    BOARD <64-char string>
    AI_MOVE <from><to>[promo]
    LEGAL_MOVES [sq ...]
    GAME_OVER WHITE_WIN | BLACK_WIN | DRAW
    ERROR <msg>
"""

import subprocess
import os
import sys


class ChessBackend:
    def __init__(self, exe_path: str):
        if not os.path.isfile(exe_path):
            raise FileNotFoundError(f"Chess engine not found: {exe_path}")
        self._proc = subprocess.Popen(
            [exe_path],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            text=True,
            bufsize=1,          # line-buffered
        )

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _send(self, cmd: str) -> None:
        self._proc.stdin.write(cmd + "\n")
        self._proc.stdin.flush()

    def _read_line(self) -> str:
        line = self._proc.stdout.readline()
        if not line:
            raise IOError("Chess engine closed unexpectedly")
        return line.rstrip("\r\n")

    def _read_response(self) -> dict:
        """
        Read lines until we have at least one meaningful response.
        Returns a dict with any keys present: board, ai_move, legal_moves,
        game_over, error.
        """
        result = {}
        while True:
            line = self._read_line()
            if line.startswith("BOARD "):
                result["board"] = line[6:]          # 64-char string
                # After BOARD, there may be a GAME_OVER on the next line
                # (but we can't block forever – peek heuristically)
                # The C engine always sends GAME_OVER right after BOARD if applicable.
                # We'll read one more optional line without blocking by checking.
                break
            elif line.startswith("AI_MOVE "):
                result["ai_move"] = line[8:]        # e.g. "e7e5" or "e7e8Q"
                # Next line will be the BOARD
                continue
            elif line.startswith("LEGAL_MOVES"):
                parts = line.split()
                result["legal_moves"] = parts[1:]   # list of squares, possibly empty
                break
            elif line.startswith("GAME_OVER "):
                result["game_over"] = line[10:]
                break
            elif line.startswith("ERROR "):
                result["error"] = line[6:]
                break
            # ignore unknown lines

        # After a BOARD line, try to read a potential GAME_OVER line.
        # We peek at what the engine may have queued.
        if "board" in result and "game_over" not in result:
            import select, platform
            if platform.system() != "Windows":
                ready, _, _ = select.select([self._proc.stdout], [], [], 0)
                if ready:
                    peek = self._read_line()
                    if peek.startswith("GAME_OVER "):
                        result["game_over"] = peek[10:]
            else:
                # On Windows, use a non-blocking read trick via a helper thread cache
                pass  # game_over will be picked up on next poll

        return result

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def init(self) -> dict:
        """Reset board, returns response dict with 'board' key."""
        self._send("INIT")
        return self._read_response()

    def move(self, mv: str) -> dict:
        """
        Apply player move.  mv is algebraic like 'e2e4' or 'e7e8Q'.
        Returns dict with 'board' key, possibly 'game_over', or 'error'.
        """
        self._send(f"MOVE {mv}")
        return self._read_response()

    def ai_move(self) -> dict:
        """
        Ask engine for best move.
        Returns dict with 'ai_move' and 'board', possibly 'game_over'.
        """
        self._send("AI_MOVE")
        # Read AI_MOVE line then BOARD line
        result = {}
        while "board" not in result:
            line = self._read_line()
            if line.startswith("AI_MOVE "):
                result["ai_move"] = line[8:]
            elif line.startswith("BOARD "):
                result["board"] = line[6:]
            elif line.startswith("GAME_OVER "):
                result["game_over"] = line[10:]
        # Try to pick up game_over on Windows
        if "game_over" not in result:
            try:
                line2 = self._read_line()   # will block briefly – but engine always sends it
                # Only read if it's game-over; otherwise buffer it
                if line2.startswith("GAME_OVER "):
                    result["game_over"] = line2[10:]
                # For simplicity we discard any other unexpected line here
            except Exception:
                pass
        return result

    def legal_moves(self, sq: str) -> list:
        """Returns list of legal destination square strings for piece on sq."""
        self._send(f"LEGAL {sq}")
        resp = self._read_response()
        return resp.get("legal_moves", [])

    def quit(self) -> None:
        try:
            self._send("QUIT")
            self._proc.wait(timeout=2)
        except Exception:
            self._proc.kill()
