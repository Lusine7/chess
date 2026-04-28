"""
game.py – Game state machine.

Responsibilities:
  - Track whose turn it is (player color vs AI)
  - Handle click events (piece selection + move submission)
  - Run AI move in a background thread so pygame stays responsive
  - Expose state for the renderer
"""

import threading
from enum import Enum, auto
from protocol import ChessBackend


class Phase(Enum):
    COLOR_SELECT = auto()   # startup screen
    PLAYER_TURN  = auto()
    AI_THINKING  = auto()
    GAME_OVER    = auto()


class Game:
    def __init__(self, backend: ChessBackend):
        self.backend: ChessBackend = backend

        # Board state: 64-char string (index 0=a8, 63=h1)
        self.board_str: str = "." * 64

        # UI state
        self.phase: Phase       = Phase.COLOR_SELECT
        self.selected_sq: int   = -1          # index of selected piece, -1 = none
        self.legal_dests: list  = []          # list of destination square indices
        self.last_move: tuple   = (-1, -1)    # (from, to) for highlighting
        self.game_over_msg: str = ""
        self.status_msg: str    = "Select your color"

        # Set by color-selection screen
        self.player_color: int  = 1           # 1=white, -1=black
        self.ai_color: int      = -1

        # Threading
        self._ai_result: dict   = {}
        self._ai_thread: threading.Thread | None = None

    # ------------------------------------------------------------------
    # Color selection (called by renderer on button click)
    # ------------------------------------------------------------------

    def start_game(self, player_color: int) -> None:
        """Called when the player picks white (1) or black (-1)."""
        self.player_color = player_color
        self.ai_color     = -player_color

        resp = self.backend.init()
        self.board_str = resp.get("board", self.board_str)

        if self.player_color == 1:
            self.phase      = Phase.PLAYER_TURN
            self.status_msg = "Your turn (White)"
        else:
            # AI plays white first
            self.phase      = Phase.AI_THINKING
            self.status_msg = "AI is thinking…"
            self._launch_ai()

    # ------------------------------------------------------------------
    # Click handling (called per pygame click event)
    # ------------------------------------------------------------------

    def handle_click(self, sq: int) -> None:
        """sq is a board index 0-63."""
        if self.phase != Phase.PLAYER_TURN:
            return

        piece = self.board_str[sq] if 0 <= sq < 64 else "."

        if self.selected_sq == -1:
            # First click: select a friendly piece
            if self._is_player_piece(piece):
                self.selected_sq = sq
                alg = self._idx_to_alg(sq)
                self.legal_dests = [
                    self._alg_to_idx(d)
                    for d in self.backend.legal_moves(alg)
                ]
        else:
            # Second click
            if sq == self.selected_sq:
                # Deselect
                self._clear_selection()
                return

            if sq in self.legal_dests:
                # Attempt the move
                from_alg = self._idx_to_alg(self.selected_sq)
                to_alg   = self._idx_to_alg(sq)
                mv       = from_alg + to_alg

                # Check if promotion (player pawn reaching back rank)
                promo = self._check_promotion(self.selected_sq, sq)
                if promo:
                    mv += promo   # e.g. "e7e8Q"

                resp = self.backend.move(mv)
                self._clear_selection()

                if "error" in resp:
                    self.status_msg = f"Illegal: {resp['error']}"
                    return

                self.board_str  = resp.get("board", self.board_str)
                self.last_move  = (self.selected_sq, sq)

                if "game_over" in resp:
                    self._handle_game_over(resp["game_over"])
                    return

                # Trigger AI
                self.phase      = Phase.AI_THINKING
                self.status_msg = "AI is thinking…"
                self._launch_ai()

            else:
                # Click on a different friendly piece – re-select
                if self._is_player_piece(piece):
                    self.selected_sq = sq
                    alg = self._idx_to_alg(sq)
                    self.legal_dests = [
                        self._alg_to_idx(d)
                        for d in self.backend.legal_moves(alg)
                    ]
                else:
                    self._clear_selection()

    # ------------------------------------------------------------------
    # AI move (runs in background thread)
    # ------------------------------------------------------------------

    def _launch_ai(self) -> None:
        self._ai_result = {}
        self._ai_thread = threading.Thread(target=self._ai_worker, daemon=True)
        self._ai_thread.start()

    def _ai_worker(self) -> None:
        self._ai_result = self.backend.ai_move()

    def update(self) -> None:
        """Call once per frame to collect AI result when ready."""
        if self.phase == Phase.AI_THINKING:
            if self._ai_thread and not self._ai_thread.is_alive():
                resp = self._ai_result
                self._ai_thread = None

                mv_str = resp.get("ai_move", "")
                if mv_str and len(mv_str) >= 4:
                    from_idx = self._alg_to_idx(mv_str[:2])
                    to_idx   = self._alg_to_idx(mv_str[2:4])
                    self.last_move = (from_idx, to_idx)

                self.board_str = resp.get("board", self.board_str)

                if "game_over" in resp:
                    self._handle_game_over(resp["game_over"])
                    return

                self.phase      = Phase.PLAYER_TURN
                color_name      = "White" if self.player_color == 1 else "Black"
                self.status_msg = f"Your turn ({color_name})"

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _clear_selection(self) -> None:
        self.selected_sq = -1
        self.legal_dests = []

    def _is_player_piece(self, char: str) -> bool:
        if self.player_color == 1:
            return char.isupper()
        return char.islower()

    def _check_promotion(self, from_sq: int, to_sq: int) -> str:
        """Return promotion char if this move is a pawn promotion, else ''."""
        piece = self.board_str[from_sq]
        if piece == 'P' and to_sq < 8:     # white pawn reaches rank 8 (indices 0-7)
            return 'Q'
        if piece == 'p' and to_sq >= 56:   # black pawn reaches rank 1 (indices 56-63)
            return 'Q'
        return ''

    def _handle_game_over(self, result: str) -> None:
        self.phase = Phase.GAME_OVER
        if result == "WHITE_WIN":
            self.game_over_msg = "Checkmate – White wins!"
        elif result == "BLACK_WIN":
            self.game_over_msg = "Checkmate – Black wins!"
        else:
            self.game_over_msg = "Stalemate – Draw!"
        self.status_msg = self.game_over_msg

    @staticmethod
    def _idx_to_alg(idx: int) -> str:
        return chr(ord('a') + idx % 8) + str(8 - idx // 8)

    @staticmethod
    def _alg_to_idx(alg: str) -> int:
        return (8 - int(alg[1])) * 8 + (ord(alg[0]) - ord('a'))
