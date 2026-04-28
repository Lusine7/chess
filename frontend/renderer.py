"""
renderer.py — Pygame-based chess board renderer.

Draws:
  • The 8×8 board with a subtle wood-tone palette
  • Unicode chess pieces scaled to each square
  • Selection highlight and legal-move dots
  • An in-game promotion dialog
  • End-game overlay (checkmate / stalemate / draw)
  • Status bar (turn indicator + move counter)
"""

import pygame
from typing import Optional

# ------------------------------------------------------------------ #
#  Colour palette                                                      #
# ------------------------------------------------------------------ #
LIGHT_SQ    = (240, 217, 181)   # cream
DARK_SQ     = (181, 136,  99)   # warm brown
SEL_COLOUR  = (106, 168,  79, 160)   # translucent green (RGBA)
MOVE_DOT    = ( 70, 130,  70, 140)
LAST_MOVE   = (205, 210,  56, 140)   # yellow tint for last-move flash
CHECK_SQ    = (220,  50,  50, 160)   # red tint on king-in-check square

BG_STATUS   = ( 30,  30,  30)
TEXT_STATUS = (220, 220, 220)
TEXT_ACCENT = (255, 200,  60)

OVERLAY_BG  = (  0,   0,   0, 170)  # dark semi-transparent overlay
OVERLAY_TXT = (255, 255, 255)

PROMO_BG    = (245, 245, 245)
PROMO_HOVER = (180, 215, 255)
PROMO_BORDER= ( 80,  80,  80)

# Unicode piece glyphs  (white / black, keyed by piece letter + color)
PIECE_GLYPHS = {
    'K': '♔', 'Q': '♕', 'R': '♖', 'B': '♗', 'N': '♘', 'P': '♙',
    'k': '♚', 'q': '♛', 'r': '♜', 'b': '♝', 'n': '♞', 'p': '♟',
}

STATUS_HEIGHT  = 48
PROMO_PIECES   = ['q', 'r', 'b', 'n']
PROMO_LABELS   = {'q': '♛', 'r': '♜', 'b': '♝', 'n': '♞'}


class Renderer:
    """
    Owns all Pygame surfaces and fonts.  Call draw() once per frame.

    Parameters
    ----------
    screen      : pygame.Surface  — the main window surface
    board_size  : int             — pixel width/height of the board area
    """

    def __init__(self, screen: pygame.Surface, board_size: int):
        self.screen     = screen
        self.board_size = board_size
        self.sq_size    = board_size // 8

        self._init_fonts()
        self._piece_surfaces: dict[str, pygame.Surface] = {}

        # Overlay surface (for transparency)
        self._overlay = pygame.Surface(
            (board_size, board_size), pygame.SRCALPHA
        )

    # ---------------------------------------------------------------- #
    #  Font initialisation                                               #
    # ---------------------------------------------------------------- #

    def _init_fonts(self):
        sq = self.sq_size
        # Try to find a system font with good Unicode chess glyph coverage
        candidates = [
            "segoeuisymbol", "dejavusans", "notoemoji",
            "symbola", "freesans", "arial",
        ]
        piece_font = None
        for name in candidates:
            f = pygame.font.SysFont(name, int(sq * 0.82))
            if f:
                piece_font = f
                break
        self.font_piece  = piece_font or pygame.font.Font(None, int(sq * 0.82))
        self.font_coord  = pygame.font.SysFont("consolas", 13, bold=False)
        self.font_status = pygame.font.SysFont("segoeuisymbol", 22, bold=True)
        self.font_overlay= pygame.font.SysFont("segoeuisymbol", 46, bold=True)
        self.font_promo  = pygame.font.SysFont("segoeuisymbol", int(sq * 0.75))

    # ---------------------------------------------------------------- #
    #  Coordinate helpers                                                #
    # ---------------------------------------------------------------- #

    def sq_to_px(self, rank: int, file: int) -> tuple[int, int]:
        """Top-left pixel of a square (rank 0 = white's back rank = bottom)."""
        x = file * self.sq_size
        y = (7 - rank) * self.sq_size      # flip so rank 0 is at the bottom
        return x, y

    def px_to_sq(self, px: int, py: int) -> Optional[tuple[int, int]]:
        """Convert a pixel coordinate to (rank, file), or None if out of board."""
        if not (0 <= px < self.board_size and 0 <= py < self.board_size):
            return None
        file = px // self.sq_size
        rank = 7 - (py // self.sq_size)
        return rank, file

    # ---------------------------------------------------------------- #
    #  Main draw entry-point                                             #
    # ---------------------------------------------------------------- #

    def draw(
        self,
        board_state: list[list[str]],   # 8×8 grid of piece chars or ""
        selected_sq: Optional[tuple[int, int]],
        legal_dests: list[tuple[int, int]],
        last_move:   Optional[tuple[tuple[int, int], tuple[int, int]]],
        in_check_sq: Optional[tuple[int, int]],
        status_text: str,
        turn_color:  str,               # "white" | "black"
        game_over:   Optional[str],     # None or overlay message
        promo_pending: bool,
        promo_hover: Optional[str],
    ):
        self._draw_board(board_state, selected_sq, legal_dests,
                         last_move, in_check_sq)
        self._draw_status_bar(status_text, turn_color)

        if promo_pending:
            self._draw_promotion_dialog(promo_hover)
        elif game_over:
            self._draw_overlay(game_over)

    # ---------------------------------------------------------------- #
    #  Board drawing                                                     #
    # ---------------------------------------------------------------- #

    def _draw_board(self, board_state, selected_sq, legal_dests,
                    last_move, in_check_sq):
        sq = self.sq_size
        ov = self._overlay
        ov.fill((0, 0, 0, 0))

        for rank in range(8):
            for file in range(8):
                x, y   = self.sq_to_px(rank, file)
                is_light = (rank + file) % 2 == 0
                colour   = LIGHT_SQ if is_light else DARK_SQ
                pygame.draw.rect(self.screen, colour, (x, y, sq, sq))

                # ---- Last-move highlight ----
                if last_move:
                    if (rank, file) in (last_move[0], last_move[1]):
                        pygame.draw.rect(ov, LAST_MOVE, (x, y, sq, sq))

                # ---- King-in-check highlight ----
                if in_check_sq and (rank, file) == in_check_sq:
                    pygame.draw.rect(ov, CHECK_SQ, (x, y, sq, sq))

                # ---- Selection highlight ----
                if selected_sq and (rank, file) == selected_sq:
                    pygame.draw.rect(ov, SEL_COLOUR, (x, y, sq, sq))

                # ---- Legal-move dots ----
                if (rank, file) in legal_dests:
                    # If the destination has an enemy piece → ring; else dot
                    piece = board_state[rank][file]
                    if piece:
                        pygame.draw.rect(ov, MOVE_DOT, (x, y, sq, sq))
                    else:
                        cx, cy = x + sq // 2, y + sq // 2
                        pygame.draw.circle(ov, MOVE_DOT,
                                           (cx, cy), sq // 6)

        self.screen.blit(ov, (0, 0))

        # ---- Draw pieces ----
        for rank in range(8):
            for file in range(8):
                piece = board_state[rank][file]
                if piece:
                    self._draw_piece(piece, rank, file)

        # ---- Rank / file coordinates ----
        self._draw_coordinates()

    def _draw_piece(self, piece_char: str, rank: int, file: int):
        glyph = PIECE_GLYPHS.get(piece_char, piece_char)
        key   = piece_char
        if key not in self._piece_surfaces:
            surf = self.font_piece.render(glyph, True, (10, 10, 10))
            self._piece_surfaces[key] = surf

        surf = self._piece_surfaces[key]
        x, y = self.sq_to_px(rank, file)
        sq   = self.sq_size
        # Centre piece in square
        cx   = x + (sq - surf.get_width())  // 2
        cy   = y + (sq - surf.get_height()) // 2
        self.screen.blit(surf, (cx, cy))

    def _draw_coordinates(self):
        sq    = self.sq_size
        pad   = 3
        files = "abcdefgh"
        ranks = "12345678"
        for i in range(8):
            # file labels (bottom edge of board)
            label = self.font_coord.render(files[i], True, (80, 80, 80))
            x = i * sq + sq - label.get_width() - pad
            y = self.board_size - label.get_height() - pad
            self.screen.blit(label, (x, y))

            # rank labels (left edge)
            label = self.font_coord.render(ranks[7 - i], True, (80, 80, 80))
            self.screen.blit(label, (pad, i * sq + pad))

    # ---------------------------------------------------------------- #
    #  Status bar                                                        #
    # ---------------------------------------------------------------- #

    def _draw_status_bar(self, status_text: str, turn_color: str):
        bar_y = self.board_size
        bar_w = self.board_size
        pygame.draw.rect(self.screen, BG_STATUS,
                         (0, bar_y, bar_w, STATUS_HEIGHT))

        # Turn indicator circle
        dot_color = (240, 240, 240) if turn_color == "white" else (20, 20, 20)
        dot_border= (180, 180, 180)
        cx, cy = 24, bar_y + STATUS_HEIGHT // 2
        pygame.draw.circle(self.screen, dot_border, (cx, cy), 13)
        pygame.draw.circle(self.screen, dot_color,  (cx, cy), 11)

        txt = self.font_status.render(status_text, True, TEXT_STATUS)
        self.screen.blit(txt, (46, bar_y + (STATUS_HEIGHT - txt.get_height()) // 2))

    # ---------------------------------------------------------------- #
    #  Promotion dialog                                                  #
    # ---------------------------------------------------------------- #

    def _draw_promotion_dialog(self, hover: Optional[str]):
        """Four piece buttons centred on the board."""
        sq      = self.sq_size
        n       = len(PROMO_PIECES)
        box_w   = sq
        box_h   = sq
        total_w = n * box_w
        start_x = (self.board_size - total_w) // 2
        start_y = (self.board_size - box_h)   // 2

        # Dim background
        dim = pygame.Surface((self.board_size, self.board_size), pygame.SRCALPHA)
        dim.fill((0, 0, 0, 140))
        self.screen.blit(dim, (0, 0))

        for i, piece in enumerate(PROMO_PIECES):
            bx = start_x + i * box_w
            by = start_y
            bg = PROMO_HOVER if hover == piece else PROMO_BG
            pygame.draw.rect(self.screen, bg,          (bx, by, box_w, box_h), border_radius=6)
            pygame.draw.rect(self.screen, PROMO_BORDER, (bx, by, box_w, box_h), 2, border_radius=6)

            glyph = PROMO_LABELS[piece]
            surf  = self.font_promo.render(glyph, True, (20, 20, 20))
            cx    = bx + (box_w - surf.get_width())  // 2
            cy    = by + (box_h - surf.get_height()) // 2
            self.screen.blit(surf, (cx, cy))

    def promo_piece_at(self, px: int, py: int) -> Optional[str]:
        """Return which promotion piece (or None) the pixel is hovering over."""
        sq      = self.sq_size
        n       = len(PROMO_PIECES)
        box_w   = sq
        box_h   = sq
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
    #  Game-over overlay                                                 #
    # ---------------------------------------------------------------- #

    def _draw_overlay(self, message: str):
        dim = pygame.Surface(
            (self.board_size, self.board_size + STATUS_HEIGHT),
            pygame.SRCALPHA
        )
        dim.fill(OVERLAY_BG)
        self.screen.blit(dim, (0, 0))

        # Main message
        lines = message.split("\n")
        total_h = len(lines) * 56
        start_y = (self.board_size - total_h) // 2

        for i, line in enumerate(lines):
            colour = TEXT_ACCENT if i == 0 else OVERLAY_TXT
            font   = self.font_overlay if i == 0 else self.font_status
            surf   = font.render(line, True, colour)
            x = (self.board_size - surf.get_width()) // 2
            y = start_y + i * 56
            self.screen.blit(surf, (x, y))

        # "Press R to restart" hint
        hint = self.font_coord.render(
            "Press  R  to restart  ·  Q  to quit", True, (180, 180, 180)
        )
        hx = (self.board_size - hint.get_width()) // 2
        hy = self.board_size - 36
        self.screen.blit(hint, (hx, hy))
