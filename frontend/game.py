"""
game.py — Chess game logic / state machine.

Responsibilities:
  • Maintains a local mirror of the board (8×8 list of piece chars)
  • Manages turn, selection, legal-move caching and promotion flow
  • Talks to the C engine via ChessProtocol
  • Decides when the AI should think (black's turn)

Piece encoding (mirrors the C backend):
  Upper-case = white  (K Q R B N P)
  Lower-case = black  (k q r b n p)
  ""           = empty
"""

from __future__ import annotations
from protocol import ChessProtocol
from typing   import Optional
import os, sys

# ------------------------------------------------------------------ #
#  Path to compiled binary                                             #
# ------------------------------------------------------------------ #
_HERE    = os.path.dirname(os.path.abspath(__file__))
_BACKEND = os.path.join(_HERE, "..", "backend")

# Accept an .exe (Windows) or bare binary (Linux/macOS)
_BINARY_WIN  = os.path.join(_BACKEND, "chess.exe")
_BINARY_UNIX = os.path.join(_BACKEND, "chess")
BINARY_PATH  = _BINARY_WIN if os.path.exists(_BINARY_WIN) else _BINARY_UNIX


# ------------------------------------------------------------------ #
#  Starting position — mirrors board_init() in the C backend           #
# ------------------------------------------------------------------ #
def _starting_board() -> list[list[str]]:
    """Return an 8×8 grid of piece characters (rank 0 = white's back rank)."""
    b: list[list[str]] = [[""] * 8 for _ in range(8)]

    back = ['R', 'N', 'B', 'Q', 'K', 'B', 'N', 'R']
    for f, p in enumerate(back):
        b[0][f] = p           # white back rank
        b[7][f] = p.lower()   # black back rank

    for f in range(8):
        b[1][f] = 'P'         # white pawns
        b[6][f] = 'p'         # black pawns

    return b


# ------------------------------------------------------------------ #
#  GameState                                                           #
# ------------------------------------------------------------------ #
class GameState:
    """
    Central game state.  The Renderer reads from this object;
    the event loop calls methods on it.

    Parameters
    ----------
    player_color : "white" | "black"
        Which side the human plays.  AI takes the other side.
    """

    def __init__(self, player_color: str = "white", depth: int = 4):
        self.player_color = player_color
        self.depth        = depth
        self.engine       = ChessProtocol(BINARY_PATH)
        self.engine.init()
        self.engine.set_depth(depth)

        self.board: list[list[str]] = _starting_board()

        # --- UI state ---
        self.selected_sq:   Optional[tuple[int, int]] = None
        self.legal_dests:   list[tuple[int, int]]     = []
        self.last_move:     Optional[tuple[tuple[int, int], tuple[int, int]]] = None
        self.in_check_sq:   Optional[tuple[int, int]] = None

        # --- Game metadata ---
        self.turn:        str = "white"   # "white" | "black"
        self.game_state:  str = "playing" # "playing" | "check" | "checkmate" | …
        self.move_number: int = 1
        self.status_text: str = "White to move"
        self.game_over_msg: Optional[str] = None

        # --- Promotion ---
        self.promo_pending:   bool                    = False
        self.promo_from:      Optional[tuple[int, int]] = None
        self.promo_to:        Optional[tuple[int, int]] = None

        # --- AI flags ---
        self.ai_thinking:    bool = False
        self.needs_ai_move:  bool = (player_color == "black")  # AI goes first?

    # ---------------------------------------------------------------- #
    #  Public API called by the event loop                              #
    # ---------------------------------------------------------------- #

    def click_square(self, rank: int, file: int) -> None:
        """Handle a click on the board (ignored when it's the AI's turn)."""
        if self.game_over_msg or self.ai_thinking or self.promo_pending:
            return
        if self.turn != self.player_color:
            return

        piece = self.board[rank][file]

        # ---- First click: select own piece ----
        if self.selected_sq is None:
            if self._is_own_piece(piece):
                self._select(rank, file)
            return

        # ---- Second click ----
        if (rank, file) == self.selected_sq:
            # Clicked same square → deselect
            self._deselect()
            return

        if (rank, file) in self.legal_dests:
            # Valid destination → attempt move
            self._try_move(self.selected_sq, (rank, file))
        elif self._is_own_piece(piece):
            # Clicked a different own piece → re-select
            self._select(rank, file)
        else:
            self._deselect()

    def choose_promotion(self, piece_char: str) -> None:
        """Called when the user clicks a piece in the promotion dialog."""
        if not self.promo_pending:
            return
        fr, ff = self.promo_from
        tr, tf = self.promo_to
        self._execute_move(fr, ff, tr, tf, promotion=piece_char)
        self.promo_pending = False
        self.promo_from = self.promo_to = None

    def request_ai_move(self) -> None:
        """
        Ask the engine to compute and apply the AI's best move.
        Updates the local board mirror from the engine's reply.
        Should be called from the event loop when it's the AI's turn.
        """
        if self.game_over_msg:
            return
        self.ai_thinking = True
        ok, from_sq, to_sq, promo = self.engine.ai_move()
        self.ai_thinking = False

        if ok:
            fr = int(from_sq[1]) - 1
            ff = ord(from_sq[0]) - ord('a')
            tr = int(to_sq[1]) - 1
            tf = ord(to_sq[0]) - ord('a')
            self._apply_local_move(fr, ff, tr, tf, promo)
            self.last_move = ((fr, ff), (tr, tf))

        self._refresh_status()
        self.needs_ai_move = False

    def restart(self) -> None:
        """Reset everything for a new game."""
        self.engine.init()
        self.engine.set_depth(self.depth)
        self.board         = _starting_board()
        self.selected_sq   = None
        self.legal_dests   = []
        self.last_move     = None
        self.in_check_sq   = None
        self.turn          = "white"
        self.game_state    = "playing"
        self.move_number   = 1
        self.status_text   = "White to move"
        self.game_over_msg = None
        self.promo_pending = False
        self.promo_from    = None
        self.promo_to      = None
        self.ai_thinking   = False
        self.needs_ai_move = (self.player_color == "black")

    # ---------------------------------------------------------------- #
    #  Internal helpers                                                  #
    # ---------------------------------------------------------------- #

    def _is_own_piece(self, piece: str) -> bool:
        if not piece:
            return False
        if self.turn == "white":
            return piece.isupper()
        return piece.islower()

    def _select(self, rank: int, file: int) -> None:
        sq_str = self._sq_str(rank, file)
        dests  = self.engine.get_moves(sq_str)
        self.selected_sq  = (rank, file)
        self.legal_dests  = [self._parse_sq(s) for s in dests]

    def _deselect(self) -> None:
        self.selected_sq = None
        self.legal_dests = []

    def _try_move(self, from_sq: tuple[int, int],
                       to_sq:   tuple[int, int]) -> None:
        fr, ff = from_sq
        tr, tf = to_sq
        piece  = self.board[fr][ff]

        # Check if this is a pawn reaching the back rank → need promotion dialog
        is_promotion = (
            piece in ('P', 'p') and
            ((piece == 'P' and tr == 7) or (piece == 'p' and tr == 0))
        )

        if is_promotion:
            self.promo_pending = True
            self.promo_from    = from_sq
            self.promo_to      = to_sq
            self._deselect()
            return

        self._execute_move(fr, ff, tr, tf)

    def _execute_move(self, fr: int, ff: int, tr: int, tf: int,
                      promotion: Optional[str] = None) -> None:
        """Send MOVE to engine, update board on success."""
        from_s = self._sq_str(fr, ff)
        to_s   = self._sq_str(tr, tf)
        ok, _  = self.engine.make_move(from_s, to_s, promotion)
        if not ok:
            self._deselect()
            return

        self._apply_local_move(fr, ff, tr, tf, promotion)
        self.last_move = ((fr, ff), (tr, tf))
        self._deselect()
        self._refresh_status()

        # Signal that the AI should respond on the next frame
        if self.game_over_msg is None and self.turn != self.player_color:
            self.needs_ai_move = True

    def _apply_local_move(self, fr: int, ff: int, tr: int, tf: int,
                           promo: Optional[str]) -> None:
        """Mirror the C engine's board update locally (no legality check)."""
        piece = self.board[fr][ff]
        ptype = piece.upper() if piece else ''

        # En-passant capture: the captured pawn is on the same rank as fr
        # but the same file as tf.  We detect it heuristically.
        if ptype == 'P' and ff != tf and self.board[tr][tf] == '':
            self.board[fr][tf] = ''   # remove captured pawn

        # Castling: move the rook
        if ptype == 'K' and abs(tf - ff) == 2:
            back = 0 if piece.isupper() else 7
            if tf == 6:   # kingside
                self.board[back][5] = self.board[back][7]
                self.board[back][7] = ''
            elif tf == 2: # queenside
                self.board[back][3] = self.board[back][0]
                self.board[back][0] = ''

        # Move piece
        self.board[tr][tf] = piece
        self.board[fr][ff] = ''

        # Promotion
        if promo and ptype == 'P':
            promoted = promo.upper() if piece.isupper() else promo.lower()
            self.board[tr][tf] = promoted

    def _refresh_status(self) -> None:
        """Query STATUS from the engine and update all status fields."""
        turn, state = self.engine.status()
        if turn is None:
            return

        self.turn       = turn
        self.game_state = state

        # Update king-in-check highlight
        self.in_check_sq = None
        if state in ("check", "checkmate"):
            king = 'K' if turn == "white" else 'k'
            for r in range(8):
                for f in range(8):
                    if self.board[r][f] == king:
                        self.in_check_sq = (r, f)

        # Move counter
        if turn == "white":
            self.move_number += 1

        # Status bar text
        turn_cap = turn.capitalize()
        if state == "playing":
            self.status_text   = f"{turn_cap} to move  ·  Move {self.move_number}"
            self.game_over_msg = None
        elif state == "check":
            self.status_text   = f"{turn_cap} is in  CHECK  ·  Move {self.move_number}"
            self.game_over_msg = None
        elif state == "checkmate":
            winner = "Black" if turn == "white" else "White"
            self.status_text   = "Checkmate!"
            self.game_over_msg = f"Checkmate!\n{winner} wins 🏆"
        elif state == "stalemate":
            self.status_text   = "Stalemate — draw"
            self.game_over_msg = "Stalemate!\nIt's a draw"
        elif state == "draw":
            self.status_text   = "Draw (50-move rule)"
            self.game_over_msg = "Draw!\n50-move rule"

    # ---------------------------------------------------------------- #
    #  Utilities                                                         #
    # ---------------------------------------------------------------- #

    @staticmethod
    def _sq_str(rank: int, file: int) -> str:
        return chr(ord('a') + file) + str(rank + 1)

    @staticmethod
    def _parse_sq(sq: str) -> tuple[int, int]:
        file = ord(sq[0]) - ord('a')
        rank = int(sq[1]) - 1
        return rank, file
