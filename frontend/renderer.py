"""
renderer.py — Pygame-based chess board renderer.
Pieces are rendered from PNG images when available (run setup_pieces.py
first), falling back to pygame-primitive drawing otherwise.
"""

import os
import pygame
from typing import Optional

# ------------------------------------------------------------------ #
#  Piece image loading (module-level, initialised once)               #
# ------------------------------------------------------------------ #
_PIECE_IMAGES: dict = {}   # piece_char -> raw Surface (original size)
_IMAGES_LOADED = False

# Map piece characters to the filenames produced by setup_pieces.py
_PIECE_FILENAMES = {
    'K': 'wK', 'Q': 'wQ', 'R': 'wR', 'B': 'wB', 'N': 'wN', 'P': 'wP',
    'k': 'bK', 'q': 'bQ', 'r': 'bR', 'b': 'bB', 'n': 'bN', 'p': 'bP',
}


def _load_piece_images() -> None:
    """Load PNG pieces from frontend/assets/pieces/ (if they exist)."""
    global _PIECE_IMAGES, _IMAGES_LOADED
    if _IMAGES_LOADED:
        return
    _IMAGES_LOADED = True
    assets_dir = os.path.join(os.path.dirname(__file__), "assets", "pieces")
    for char, stem in _PIECE_FILENAMES.items():
        path = os.path.join(assets_dir, f"{stem}.png")
        if os.path.isfile(path):
            try:
                _PIECE_IMAGES[char] = pygame.image.load(path).convert_alpha()
            except Exception:
                pass  # silently fall back to primitive drawing

# ------------------------------------------------------------------ #
#  Colour palette                                                      #
# ------------------------------------------------------------------ #
LIGHT_SQ   = (240, 217, 181)
DARK_SQ    = (181, 136,  99)
SEL_COL    = (106, 168,  79, 160)
MOVE_DOT   = ( 70, 130,  70, 140)
LAST_MOVE  = (205, 210,  56, 140)
CHECK_SQ   = (220,  50,  50, 160)

BG_STATUS  = ( 30,  30,  30)
TEXT_STATUS= (220, 220, 220)
TEXT_ACCENT= (255, 200,  60)

OVERLAY_BG = (  0,   0,   0, 170)
OVERLAY_TXT= (255, 255, 255)

PROMO_BG   = (245, 245, 245)
PROMO_HOVER= (180, 215, 255)
PROMO_BDR  = ( 80,  80,  80)

STATUS_HEIGHT = 48
PROMO_PIECES  = ['q', 'r', 'b', 'n']

def _make_piece_surface(piece_char: str, sq: int) -> pygame.Surface:
    """Return a surface with the piece image scaled to sq x sq pixels."""
    img    = _PIECE_IMAGES.get(piece_char)
    margin = max(3, sq // 14)
    inner  = sq - 2 * margin
    surf   = pygame.Surface((sq, sq), pygame.SRCALPHA)
    surf.fill((0, 0, 0, 0))
    if img:
        scaled = pygame.transform.smoothscale(img, (inner, inner))
        surf.blit(scaled, (margin, margin))
    return surf


# ================================================================== #
#  Renderer                                                            #
# ================================================================== #

class Renderer:
    def __init__(self, screen: pygame.Surface, board_size: int, flipped: bool = False):
        self.screen     = screen
        self.board_size = board_size
        self.sq_size    = board_size // 8
        self.flipped    = flipped          # True when player plays as black
        self._cache: dict[str, pygame.Surface] = {}
        self._overlay   = pygame.Surface((board_size, board_size), pygame.SRCALPHA)
        _load_piece_images()               # no-op if already done
        self._init_fonts()

    def _init_fonts(self):
        self.font_coord  = pygame.font.SysFont("consolas",  13)
        self.font_status = pygame.font.SysFont("sans",      22, bold=True)
        self.font_overlay= pygame.font.SysFont("sans",      44, bold=True)
        self.font_promo  = pygame.font.SysFont("sans",      18, bold=True)

    # ---------------------------------------------------------------- #
    #  Coordinate helpers                                               #
    # ---------------------------------------------------------------- #

    def sq_to_px(self, rank: int, file: int):
        if self.flipped:
            # Black at bottom: rank 7 → row 0, file 7 → col 0
            return (7 - file) * self.sq_size, rank * self.sq_size
        else:
            # White at bottom: rank 0 → row 7, file 0 → col 0
            return file * self.sq_size, (7 - rank) * self.sq_size

    def px_to_sq(self, px: int, py: int) -> Optional[tuple]:
        if not (0 <= px < self.board_size and 0 <= py < self.board_size):
            return None
        if self.flipped:
            return py // self.sq_size, 7 - px // self.sq_size
        else:
            return 7 - py // self.sq_size, px // self.sq_size

    # ---------------------------------------------------------------- #
    #  Main draw                                                        #
    # ---------------------------------------------------------------- #

    def draw(self, board_state, selected_sq, legal_dests, last_move,
             in_check_sq, status_text, turn_color, game_over,
             promo_pending, promo_hover):
        self._draw_board(board_state, selected_sq, legal_dests,
                         last_move, in_check_sq)
        self._draw_status_bar(status_text, turn_color)
        if promo_pending:
            self._draw_promo_dialog(promo_hover, turn_color)
        elif game_over:
            self._draw_overlay(game_over)

    # ---------------------------------------------------------------- #
    #  Board                                                            #
    # ---------------------------------------------------------------- #

    def _draw_board(self, board_state, selected_sq, legal_dests,
                    last_move, in_check_sq):
        sq  = self.sq_size
        ov  = self._overlay
        ov.fill((0, 0, 0, 0))

        for rank in range(8):
            for file in range(8):
                x, y     = self.sq_to_px(rank, file)
                is_light = (rank + file) % 2 == 0
                pygame.draw.rect(self.screen,
                                 LIGHT_SQ if is_light else DARK_SQ,
                                 (x, y, sq, sq))
                if last_move and (rank, file) in (last_move[0], last_move[1]):
                    pygame.draw.rect(ov, LAST_MOVE, (x, y, sq, sq))
                if in_check_sq and (rank, file) == in_check_sq:
                    pygame.draw.rect(ov, CHECK_SQ, (x, y, sq, sq))
                if selected_sq and (rank, file) == selected_sq:
                    pygame.draw.rect(ov, SEL_COL, (x, y, sq, sq))
                if (rank, file) in legal_dests:
                    if board_state[rank][file]:
                        pygame.draw.rect(ov, MOVE_DOT, (x, y, sq, sq))
                    else:
                        pygame.draw.circle(ov, MOVE_DOT,
                                           (x + sq//2, y + sq//2), sq//6)

        self.screen.blit(ov, (0, 0))

        for rank in range(8):
            for file in range(8):
                p = board_state[rank][file]
                if p:
                    self._blit_piece(p, rank, file)

        self._draw_coords()

    def _blit_piece(self, piece_char: str, rank: int, file: int):
        if piece_char not in self._cache:
            self._cache[piece_char] = _make_piece_surface(piece_char, self.sq_size)
        surf = self._cache[piece_char]
        self.screen.blit(surf, self.sq_to_px(rank, file))

    def _draw_coords(self):
        sq = self.sq_size
        files = "hgfedcba" if self.flipped else "abcdefgh"
        for i in range(8):
            fl = self.font_coord.render(files[i], True, (80, 80, 80))
            self.screen.blit(fl, (i*sq + sq - fl.get_width() - 3,
                                  self.board_size - fl.get_height() - 3))
            rank_num = str(i + 1) if self.flipped else str(8 - i)
            rk = self.font_coord.render(rank_num, True, (80, 80, 80))
            self.screen.blit(rk, (3, i*sq + 3))

    # ---------------------------------------------------------------- #
    #  Status bar                                                       #
    # ---------------------------------------------------------------- #

    def _draw_status_bar(self, status_text: str, turn_color: str):
        bar_y = self.board_size
        pygame.draw.rect(self.screen, BG_STATUS,
                         (0, bar_y, self.board_size, STATUS_HEIGHT))
        dot_fill   = (240, 240, 240) if turn_color == "white" else (20, 20, 20)
        dot_border = (160, 160, 160)
        cx, cy = 24, bar_y + STATUS_HEIGHT // 2
        pygame.draw.circle(self.screen, dot_border, (cx, cy), 13)
        pygame.draw.circle(self.screen, dot_fill,   (cx, cy), 11)
        txt = self.font_status.render(status_text, True, TEXT_STATUS)
        self.screen.blit(txt, (46, bar_y + (STATUS_HEIGHT - txt.get_height()) // 2))

    # ---------------------------------------------------------------- #
    #  Promotion dialog                                                 #
    # ---------------------------------------------------------------- #

    PROMO_NAMES = {'q': 'Queen', 'r': 'Rook', 'b': 'Bishop', 'n': 'Knight'}

    def _draw_promo_dialog(self, hover: Optional[str], turn_color: str = "white"):
        sq      = self.sq_size
        n       = len(PROMO_PIECES)
        box_w   = sq
        box_h   = sq + 24
        total_w = n * box_w
        start_x = (self.board_size - total_w) // 2
        start_y = (self.board_size - box_h)   // 2

        dim = pygame.Surface((self.board_size, self.board_size), pygame.SRCALPHA)
        dim.fill((0, 0, 0, 140))
        self.screen.blit(dim, (0, 0))

        for i, piece in enumerate(PROMO_PIECES):
            bx  = start_x + i * box_w
            by  = start_y
            bg  = PROMO_HOVER if hover == piece else PROMO_BG
            pygame.draw.rect(self.screen, bg,      (bx, by, box_w, box_h), border_radius=6)
            pygame.draw.rect(self.screen, PROMO_BDR,(bx, by, box_w, box_h), 2, border_radius=6)
            # Draw piece icon using the correct color (upper = white, lower = black)
            icon_char = piece.upper() if turn_color == "white" else piece
            icon = _make_piece_surface(icon_char, sq)
            self.screen.blit(icon, (bx, by))
            # Label
            lbl = self.font_promo.render(self.PROMO_NAMES[piece], True, (40, 40, 40))
            self.screen.blit(lbl, (bx + (box_w - lbl.get_width())//2, by + sq + 4))

    def promo_piece_at(self, px: int, py: int) -> Optional[str]:
        sq      = self.sq_size
        n       = len(PROMO_PIECES)
        box_w   = sq
        box_h   = sq + 24
        total_w = n * box_w
        start_x = (self.board_size - total_w) // 2
        start_y = (self.board_size - box_h)   // 2
        for i, piece in enumerate(PROMO_PIECES):
            bx = start_x + i * box_w
            by = start_y
            if bx <= px < bx + box_w and by <= py < by + box_h:
                return piece
        return None

    # ---------------------------------------------------------------- #
    #  Game-over overlay                                                #
    # ---------------------------------------------------------------- #

    def _draw_overlay(self, message: str):
        dim = pygame.Surface(
            (self.board_size, self.board_size + STATUS_HEIGHT), pygame.SRCALPHA)
        dim.fill(OVERLAY_BG)
        self.screen.blit(dim, (0, 0))

        lines   = message.split("\n")
        total_h = len(lines) * 58
        start_y = (self.board_size - total_h) // 2

        for i, line in enumerate(lines):
            colour = TEXT_ACCENT if i == 0 else OVERLAY_TXT
            font   = self.font_overlay if i == 0 else self.font_status
            surf   = font.render(line, True, colour)
            x = (self.board_size - surf.get_width())  // 2
            self.screen.blit(surf, (x, start_y + i * 58))

        hint = self.font_coord.render(
            "Press  R  to restart  ·  Q  to quit", True, (180, 180, 180))
        self.screen.blit(hint, (
            (self.board_size - hint.get_width()) // 2,
            self.board_size - 36))
