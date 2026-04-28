"""
renderer.py — Pygame-based chess board renderer.
Pieces are drawn with pygame primitives (no Unicode font dependency).
"""

import pygame
from typing import Optional

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

# Piece colours
WHITE_FILL   = (248, 248, 240)
WHITE_STROKE = ( 40,  40,  40)
BLACK_FILL   = ( 35,  35,  35)
BLACK_STROKE = (210, 210, 210)


# ================================================================== #
#  Piece drawing helpers  (all coordinates in 0-80 unit space)        #
# ================================================================== #

def _s(v, sq):
    """Scale a 0-80 unit value to pixels."""
    return int(v * sq / 80)

def _sp(x, y, sq):
    return (int(x * sq / 80), int(y * sq / 80))

def _poly(surf, pts, sq, fill, stroke, lw):
    scaled = [_sp(x, y, sq) for x, y in pts]
    pygame.draw.polygon(surf, fill,   scaled)
    pygame.draw.polygon(surf, stroke, scaled, lw)

def _rect(surf, x, y, w, h, sq, fill, stroke, lw):
    r = (_s(x, sq), _s(y, sq), _s(w, sq), _s(h, sq))
    pygame.draw.rect(surf, fill,   r)
    pygame.draw.rect(surf, stroke, r, lw)

def _circle(surf, cx, cy, r, sq, fill, stroke, lw):
    pygame.draw.circle(surf, fill,   _sp(cx, cy, sq), _s(r, sq))
    pygame.draw.circle(surf, stroke, _sp(cx, cy, sq), _s(r, sq), lw)


# ------------------------------------------------------------------ #

def _draw_pawn(surf, sq, fill, stroke, lw):
    _circle(surf, 40, 22, 11, sq, fill, stroke, lw)
    _poly(surf, [(32,33),(48,33),(52,58),(28,58)], sq, fill, stroke, lw)
    _poly(surf, [(22,58),(58,58),(62,72),(18,72)], sq, fill, stroke, lw)
    _rect(surf, 16, 72, 48, 6, sq, fill, stroke, lw)

def _draw_rook(surf, sq, fill, stroke, lw):
    for bx in [18, 33, 48]:
        _rect(surf, bx, 12, 10, 14, sq, fill, stroke, lw)
    _rect(surf, 18, 22, 44, 4, sq, fill, stroke, lw)
    _poly(surf, [(24,26),(56,26),(60,60),(20,60)], sq, fill, stroke, lw)
    _poly(surf, [(16,60),(64,60),(68,74),(12,74)], sq, fill, stroke, lw)
    _rect(surf, 10, 74, 60, 6, sq, fill, stroke, lw)

def _draw_knight(surf, sq, fill, stroke, lw, is_white):
    pts = [
        (30,70),(50,70),(52,55),(58,40),
        (56,25),(45,15),(35,15),(28,22),
        (22,30),(24,42),(30,48),(28,55),
    ]
    _poly(surf, pts, sq, fill, stroke, lw)
    _poly(surf, [(16,70),(64,70),(68,78),(12,78)], sq, fill, stroke, lw)
    # eye
    eye_fill = (255,255,255) if not is_white else (0,0,0)
    pygame.draw.circle(surf, stroke,   _sp(47,20,sq), _s(4,sq))
    pygame.draw.circle(surf, eye_fill, _sp(47,20,sq), _s(2,sq))
    # nostril
    pygame.draw.circle(surf, stroke, _sp(38,28,sq), _s(3,sq))

def _draw_bishop(surf, sq, fill, stroke, lw):
    pts = [(40,12),(52,20),(56,38),(54,56),(52,62),(28,62),(26,56),(24,38),(28,20)]
    _poly(surf, pts, sq, fill, stroke, lw)
    _circle(surf, 40, 12, 6, sq, fill, stroke, lw)
    lw2 = max(1, lw)
    pygame.draw.line(surf, stroke, _sp(40,32,sq), _sp(40,52,sq), lw2)
    pygame.draw.line(surf, stroke, _sp(32,42,sq), _sp(48,42,sq), lw2)
    _poly(surf, [(18,62),(62,62),(66,74),(14,74)], sq, fill, stroke, lw)
    _rect(surf, 12, 74, 56, 6, sq, fill, stroke, lw)

def _draw_queen(surf, sq, fill, stroke, lw):
    # Five crown balls
    for cx in [20, 30, 40, 50, 60]:
        _circle(surf, cx, 14, 5, sq, fill, stroke, lw)
    crown = [(20,14),(20,36),(60,36),(60,14),(55,20),(50,22),(45,16),(40,10),(35,16),(30,22),(25,20)]
    _poly(surf, crown, sq, fill, stroke, lw)
    _poly(surf, [(22,36),(58,36),(54,62),(26,62)], sq, fill, stroke, lw)
    _poly(surf, [(16,62),(64,62),(68,74),(12,74)], sq, fill, stroke, lw)
    _rect(surf, 10, 74, 60, 6, sq, fill, stroke, lw)

def _draw_king(surf, sq, fill, stroke, lw):
    # Cross
    _rect(surf, 36,  8,  8, 22, sq, fill, stroke, lw)
    _rect(surf, 28, 14, 24,  8, sq, fill, stroke, lw)
    _poly(surf, [(22,30),(58,30),(54,62),(26,62)], sq, fill, stroke, lw)
    _poly(surf, [(16,62),(64,62),(68,74),(12,74)], sq, fill, stroke, lw)
    _rect(surf, 10, 74, 60,  6, sq, fill, stroke, lw)


_DRAW_FN = {
    'P': _draw_pawn,
    'R': _draw_rook,
    'B': _draw_bishop,
    'Q': _draw_queen,
    'K': _draw_king,
}


def _make_piece_surface(piece_char: str, sq: int) -> pygame.Surface:
    surf = pygame.Surface((sq, sq), pygame.SRCALPHA)
    surf.fill((0, 0, 0, 0))
    is_white = piece_char.isupper()
    ptype    = piece_char.upper()
    fill     = WHITE_FILL   if is_white else BLACK_FILL
    stroke   = WHITE_STROKE if is_white else BLACK_STROKE
    lw       = max(2, sq // 22)

    if ptype == 'N':
        _draw_knight(surf, sq, fill, stroke, lw, is_white)
    elif ptype in _DRAW_FN:
        _DRAW_FN[ptype](surf, sq, fill, stroke, lw)

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
            self._draw_promo_dialog(promo_hover)
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

    def _draw_promo_dialog(self, hover: Optional[str]):
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
            # Draw piece icon (white queen promotion)
            icon_char = piece.upper()
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
