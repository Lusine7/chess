"""
protocol.py — thin wrapper around the C chess engine subprocess.

All communication is line-based ASCII over stdin / stdout.
Every method blocks until the engine responds (one line).
"""

import subprocess
import os


class ChessProtocol:
    def __init__(self, binary_path: str):
        if not os.path.exists(binary_path):
            raise FileNotFoundError(
                f"Chess binary not found at '{binary_path}'.\n"
                "Run:  cd backend && make"
            )
        self.proc = subprocess.Popen(
            [binary_path],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            bufsize=1,          # line-buffered
        )

    # ------------------------------------------------------------------ #
    #  Low-level I/O                                                       #
    # ------------------------------------------------------------------ #

    def _send(self, command: str) -> str:
        """Send a command line and return the engine's single-line reply."""
        self.proc.stdin.write(command + "\n")
        self.proc.stdin.flush()
        reply = self.proc.stdout.readline()
        return reply.strip()

    # ------------------------------------------------------------------ #
    #  High-level API                                                      #
    # ------------------------------------------------------------------ #

    def init(self) -> bool:
        """Reset the board to the starting position."""
        return self._send("INIT") == "OK"

    def set_depth(self, depth: int) -> bool:
        """
        Set the AI search depth (2 = easy, 4 = intermediate, 6 = hard).
        Must be called after init() so the engine is ready.
        """
        return self._send(f"DEPTH {depth}") == "OK"

    def get_moves(self, square: str) -> list[str]:
        """
        Return a list of legal destination squares for the piece on `square`.
        e.g. get_moves("e2") -> ["e3", "e4"]
        """
        reply = self._send(f"MOVES {square}")
        if reply.startswith("MOVES"):
            parts = reply.split()
            return parts[1:]        # may be empty if no legal moves
        return []

    def make_move(self, from_sq: str, to_sq: str,
                  promotion: str | None = None) -> tuple[bool, str]:
        """
        Ask the engine to play a player move.
        `promotion` is a single character: 'q' | 'r' | 'b' | 'n' (or None).
        Returns (success, raw_reply).
        """
        move_str = from_sq + to_sq + (promotion or "")
        reply = self._send(f"MOVE {move_str}")
        return reply.startswith("MOVED"), reply

    def ai_move(self) -> tuple[bool, str | None, str | None, str | None]:
        """
        Ask the engine to compute and play its best move.
        Returns (success, from_sq, to_sq, promotion_char | None).
        """
        reply = self._send("AI_MOVE")
        if reply.startswith("AI_MOVED"):
            parts = reply.split()
            move  = parts[1]
            from_sq = move[:2]
            to_sq   = move[2:4]
            promo   = move[4] if len(move) > 4 else None
            return True, from_sq, to_sq, promo
        return False, None, None, None

    def status(self) -> tuple[str | None, str | None]:
        """
        Query game state.
        Returns (turn, state) e.g. ("white", "playing") or ("black", "checkmate").
        """
        reply = self._send("STATUS")
        parts = reply.split()
        if len(parts) == 3 and parts[0] == "STATUS":
            return parts[1], parts[2]
        return None, None

    def quit(self) -> None:
        """Shut the engine down gracefully."""
        try:
            self._send("QUIT")
        except Exception:
            pass
        try:
            self.proc.terminate()
        except Exception:
            pass