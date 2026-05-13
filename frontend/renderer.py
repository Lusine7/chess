"""
renderer.py — Pygame-based chess board renderer (Simplified).
"""

import os
import pygame
from typing import Optional

# ------------------------------------------------------------------ #
#  Piece image loading                                                #
# ------------------------------------------------------------------ #
_PIECE_IMAGES: dict = {}
_IMAGES_LOADED = False

_PIECE_FILENAMES = {
    'K': 'wK', 'Q': 'wQ', 'R': 'wR', 'B': 'wB', 'N': 'wN', 'P': 'wP',
    'k': 'bK', 'q': 'bQ', 'r': 'bR', 'b': 'bB', 'n': 'bN', 'p': 'bP',
}

def _load_piece_images() -> None:
    global _PIECE_IMAGES, _IMAGES_LOADED
    if _IMAGES_LOADED: return
    _IMAGES_LOADED = True
    assets_dir = os.path.join(os.path.dirname(__file__), "assets", "pieces")
    for char, stem in _PIECE_FILENAMES.items():
        path = os.path.join(assets_dir, f"{stem}.png")
        if os.path.isfile(path):
            try:
                _PIECE_IMAGES[char] = pygame.image.load(path).convert_alpha()
            except: pass

# ------------------------------------------------------------------ #
#  Colour palette                                                      #
# ------------------------------------------------------------------ #
LIGHT_SQ   = (240, 217, 181)
DARK_SQ    = (181, 136,  99)
SEL_COL    = (106, 168,  79, 160)
MOVE_DOT   = ( 70, 130,  70, 140)
LAST_MOVE  = (205, 210,  56, 140)
CHECK_SQ   = (220,  50,  50, 160)

BG_STATUS  = ( 20,  20,  20)
TEXT_STATUS= (255, 255, 255)

OVERLAY_BG = (  0,   0,   0, 180)
OVERLAY_TXT= (255, 255, 255)

PROMO_BG   = (250, 250, 250)
PROMO_HOVER= (200, 200, 200)
PROMO_BDR  = (  0,   0,   0)

STATUS_HEIGHT = 40
PROMO_PIECES  = ['q', 'r', 'b', 'n']

def _make_piece_surface(piece_char: str, sq: int) -> pygame.Surface:
    img    = _PIECE_IMAGES.get(piece_char)
    margin = 4
    inner  = sq - 2 * margin
    surf   = pygame.Surface((sq, sq), pygame.SRCALPHA)
    surf.fill((0, 0, 0, 0))
    if img:
        scaled = pygame.transform.smoothscale(img, (inner, inner))
        surf.blit(scaled, (margin, margin))
    return surf

class Renderer:
    def __init__(self, screen: pygame.Surface, board_size: int, flipped: bool = False):
        self.screen     = screen
        self.board_size = board_size
        self.sq_size    = board_size // 8
        self.flipped    = flipped
        self._cache     = {}
        self._overlay   = pygame.Surface((board_size, board_size), pygame.SRCALPHA)
        _load_piece_images()
        self._init_fonts()

    def _init_fonts(self):
        self.font_coord  = pygame.font.SysFont("monospace", 12)
        self.font_status = pygame.font.SysFont("monospace", 18)
        self.font_overlay= pygame.font.SysFont("monospace", 36, bold=True)
        self.font_promo  = pygame.font.SysFont("monospace", 14)

    def sq_to_px(self, rank: int, file: int):
        if self.flipped:
            return (7 - file) * self.sq_size, rank * self.sq_size
        return file * self.sq_size, (7 - rank) * self.sq_size

    def px_to_sq(self, px: int, py: int) -> Optional[tuple]:
        if not (0 <= px < self.board_size and 0 <= py < self.board_size):
            return None
        if self.flipped:
            return py // self.sq_size, 7 - px // self.sq_size
        return 7 - py // self.sq_size, px // self.sq_size

    def draw(self, board_state, selected_sq, legal_dests, last_move,
             in_check_sq, status_text, turn_color, game_over,
             promo_pending, promo_hover):
        self._draw_board(board_state, selected_sq, legal_dests, last_move, in_check_sq)
        self._draw_status_bar(status_text)
        if promo_pending:
            self._draw_promo_dialog(promo_hover, turn_color)
        elif game_over:
            self._draw_overlay(game_over)

    def _draw_board(self, board_state, selected_sq, legal_dests, last_move, in_check_sq):
        sq = self.sq_size
        ov = self._overlay
        ov.fill((0, 0, 0, 0))
        for rank in range(8):
            for file in range(8):
                x, y = self.sq_to_px(rank, file)
                pygame.draw.rect(self.screen, LIGHT_SQ if (rank + file) % 2 == 0 else DARK_SQ, (x, y, sq, sq))
                if last_move and (rank, file) in last_move:
                    pygame.draw.rect(ov, LAST_MOVE, (x, y, sq, sq))
                if in_check_sq and (rank, file) == in_check_sq:
                    pygame.draw.rect(ov, CHECK_SQ, (x, y, sq, sq))
                if selected_sq and (rank, file) == selected_sq:
                    pygame.draw.rect(ov, SEL_COL, (x, y, sq, sq))
                if (rank, file) in legal_dests:
                    if board_state[rank][file]:
                        pygame.draw.rect(ov, MOVE_DOT, (x, y, sq, sq))
                    else:
                        pygame.draw.circle(ov, MOVE_DOT, (x + sq//2, y + sq//2), sq//8)
        self.screen.blit(ov, (0, 0))
        for rank in range(8):
            for file in range(8):
                p = board_state[rank][file]
                if p:
                    if p not in self._cache:
                        self._cache[p] = _make_piece_surface(p, self.sq_size)
                    self.screen.blit(self._cache[p], self.sq_to_px(rank, file))
        self._draw_coords()

    def _draw_coords(self):
        sq = self.sq_size
        files = "hgfedcba" if self.flipped else "abcdefgh"
        for i in range(8):
            fl = self.font_coord.render(files[i], True, (60, 60, 60))
            self.screen.blit(fl, (i*sq + 2, self.board_size - fl.get_height() - 2))
            rk = self.font_coord.render(str(i + 1) if self.flipped else str(8 - i), True, (60, 60, 60))
            self.screen.blit(rk, (sq - rk.get_width() - 2, i*sq + 2))

    def _draw_status_bar(self, status_text: str):
        bar_y = self.board_size
        pygame.draw.rect(self.screen, BG_STATUS, (0, bar_y, self.board_size, STATUS_HEIGHT))
        txt = self.font_status.render(status_text, True, TEXT_STATUS)
        self.screen.blit(txt, (10, bar_y + (STATUS_HEIGHT - txt.get_height()) // 2))

    def _draw_promo_dialog(self, hover: Optional[str], turn_color: str):
        sq = self.sq_size
        box_w, box_h = sq, sq + 20
        start_x = (self.board_size - 4 * box_w) // 2
        start_y = (self.board_size - box_h) // 2
        dim = pygame.Surface((self.board_size, self.board_size), pygame.SRCALPHA)
        dim.fill((0, 0, 0, 120))
        self.screen.blit(dim, (0, 0))
        for i, piece in enumerate(PROMO_PIECES):
            bx, by = start_x + i * box_w, start_y
            pygame.draw.rect(self.screen, PROMO_HOVER if hover == piece else PROMO_BG, (bx, by, box_w, box_h))
            pygame.draw.rect(self.screen, PROMO_BDR, (bx, by, box_w, box_h), 1)
            icon = _make_piece_surface(piece.upper() if turn_color == "white" else piece, sq)
            self.screen.blit(icon, (bx, by))
            lbl = self.font_promo.render({'q':'Queen','r':'Rook','b':'Bishop','n':'Knight'}[piece], True, (0,0,0))
            self.screen.blit(lbl, (bx + (box_w - lbl.get_width())//2, by + sq))

    def promo_piece_at(self, px: int, py: int) -> Optional[str]:
        sq = self.sq_size
        box_w, box_h = sq, sq + 20
        start_x, start_y = (self.board_size - 4 * box_w) // 2, (self.board_size - box_h) // 2
        for i, piece in enumerate(PROMO_PIECES):
            bx, by = start_x + i * box_w, start_y
            if bx <= px < bx + box_w and by <= py < by + box_h: return piece
        return None

    def _draw_overlay(self, message: str):
        dim = pygame.Surface((self.board_size, self.board_size + STATUS_HEIGHT), pygame.SRCALPHA)
        dim.fill(OVERLAY_BG)
        self.screen.blit(dim, (0, 0))
        lines = message.split("\n")
        start_y = (self.board_size - len(lines) * 40) // 2
        for i, line in enumerate(lines):
            surf = self.font_overlay.render(line, True, OVERLAY_TXT)
            self.screen.blit(surf, ((self.board_size - surf.get_width()) // 2, start_y + i * 50))