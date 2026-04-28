"""
renderer.py – All pygame drawing: board, pieces, highlights, UI panels.

Board layout (600 × 680 window):
  - 560 × 560 board centred horizontally, starting at y=60
  - 70 px per square
  - Status bar below the board
"""

import pygame
import math

# ── Dimensions ────────────────────────────────────────────────────────
WIN_W, WIN_H  = 600, 680
SQ            = 70           # pixels per square
BOARD_LEFT    = 20
BOARD_TOP     = 60
BOARD_SIZE    = SQ * 8      # 560

# ── Colour palette ────────────────────────────────────────────────────
CLR_BG          = (18,  18,  28)
CLR_LIGHT_SQ    = (240, 217, 181)
CLR_DARK_SQ     = (181, 136, 99)
CLR_SELECT      = (247, 247, 105, 180)   # yellow, semi-transparent
CLR_LAST_MOVE   = (205, 210,  92, 120)
CLR_LEGAL_DOT   = ( 60,  60,  60, 140)
CLR_LEGAL_CAP   = (200,  60,  60, 140)
CLR_TEXT        = (230, 230, 230)
CLR_STATUS_BG   = ( 30,  30,  45)
CLR_BTN_W       = (220, 200, 160)
CLR_BTN_B       = ( 60,  60,  80)
CLR_BTN_HOVER   = (255, 220, 100)
CLR_OVERLAY     = (0,   0,   0, 160)

# Piece letter labels (uppercase = white, lowercase = black)
PIECE_LABEL = {'K':'K','Q':'Q','R':'R','B':'B','N':'N','P':'P',
               'k':'K','q':'Q','r':'R','b':'B','n':'N','p':'P'}
# Piece colours
CLR_WHITE_PIECE  = (255, 252, 235)
CLR_BLACK_PIECE  = ( 30,  25,  20)
CLR_WHITE_RING   = (180, 140,  80)
CLR_BLACK_RING   = (200, 200, 200)


def _sq_rect(idx: int) -> pygame.Rect:
    """Return the pygame.Rect for board index idx (0=a8, 63=h1)."""
    col = idx % 8
    row = idx // 8
    return pygame.Rect(BOARD_LEFT + col * SQ, BOARD_TOP + row * SQ, SQ, SQ)


def _is_light(idx: int) -> bool:
    col, row = idx % 8, idx // 8
    return (col + row) % 2 == 0


class Renderer:
    def __init__(self, screen: pygame.Surface):
        self.screen = screen
        pygame.font.init()

        # Use a reliable built-in bold font for piece letters
        self.piece_font = pygame.font.SysFont("dejavusans", 28, bold=True) or \
                          pygame.font.SysFont(None, 30, bold=True)

        self.label_font  = pygame.font.SysFont("segoeui", 14)
        self.status_font = pygame.font.SysFont("segoeui", 18)
        self.title_font  = pygame.font.SysFont("segoeui", 32, bold=True)
        self.btn_font    = pygame.font.SysFont("segoeui", 22, bold=True)
        self.over_font   = pygame.font.SysFont("segoeui", 28, bold=True)

        # Spinning-dot animation for AI thinking indicator
        self._tick = 0

        # Button rects for color selection screen
        self.btn_white = pygame.Rect(120, 310, 160, 60)
        self.btn_black = pygame.Rect(320, 310, 160, 60)

        # "Play again" button
        self.btn_again = pygame.Rect(200, 420, 200, 50)

    # ── Public draw entry points ──────────────────────────────────────

    def draw_color_select(self, mx: int, my: int) -> None:
        """Draw the startup color-selection screen."""
        self.screen.fill(CLR_BG)
        self._draw_decorative_board()

        # Title
        t = self.title_font.render("Chess", True, CLR_BTN_HOVER)
        self.screen.blit(t, t.get_rect(center=(WIN_W // 2, 180)))
        sub = self.status_font.render("Choose your color to start", True, CLR_TEXT)
        self.screen.blit(sub, sub.get_rect(center=(WIN_W // 2, 225)))

        hover_w = self.btn_white.collidepoint(mx, my)
        hover_b = self.btn_black.collidepoint(mx, my)
        self._draw_button(self.btn_white, "♔  White", hover_w, CLR_BTN_W, (40, 40, 40))
        self._draw_button(self.btn_black, "♚  Black", hover_b, CLR_BTN_B, CLR_TEXT)

    def draw_game(self, board_str: str, selected: int, legal_dests: list,
                  last_move: tuple, status: str, flipped: bool) -> None:
        """Draw the main game board."""
        self._tick += 1
        self.screen.fill(CLR_BG)
        self._draw_board_squares(selected, legal_dests, last_move)
        self._draw_coord_labels(flipped)
        self._draw_pieces(board_str, flipped)
        self._draw_status_bar(status)

    def draw_game_over_overlay(self, message: str, mx: int, my: int) -> None:
        """Overlay on top of the board showing game-over message."""
        overlay = pygame.Surface((WIN_W, WIN_H), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 160))
        self.screen.blit(overlay, (0, 0))

        msg = self.over_font.render(message, True, CLR_BTN_HOVER)
        self.screen.blit(msg, msg.get_rect(center=(WIN_W // 2, WIN_H // 2 - 40)))

        hover = self.btn_again.collidepoint(mx, my)
        self._draw_button(self.btn_again, "Play Again", hover, CLR_BTN_W, (30, 30, 30))

    def draw_thinking_spinner(self) -> None:
        """Small animated spinner during AI turn."""
        cx, cy = WIN_W // 2, BOARD_TOP + BOARD_SIZE + 38
        for i in range(8):
            angle = math.radians(self._tick * 5 + i * 45)
            alpha = int(255 * (i + 1) / 8)
            r = 5
            x = int(cx + 18 * math.cos(angle))
            y = int(cy + 18 * math.sin(angle))
            pygame.draw.circle(self.screen, (*CLR_BTN_HOVER[:3], alpha), (x, y), r)

    # ── Private helpers ───────────────────────────────────────────────

    def _draw_board_squares(self, selected: int, legal_dests: list,
                             last_move: tuple) -> None:
        hl_surf = pygame.Surface((SQ, SQ), pygame.SRCALPHA)
        for idx in range(64):
            rect  = _sq_rect(idx)
            color = CLR_LIGHT_SQ if _is_light(idx) else CLR_DARK_SQ
            pygame.draw.rect(self.screen, color, rect)

            # Last-move highlight
            if idx in last_move and last_move[0] != -1:
                hl_surf.fill(CLR_LAST_MOVE)
                self.screen.blit(hl_surf, rect.topleft)

            # Selected square
            if idx == selected:
                hl_surf.fill(CLR_SELECT)
                self.screen.blit(hl_surf, rect.topleft)

        # Legal move dots / rings
        dot_surf = pygame.Surface((SQ, SQ), pygame.SRCALPHA)
        for dst in legal_dests:
            rect = _sq_rect(dst)
            dot_surf.fill((0, 0, 0, 0))
            # If occupied by enemy → draw a ring; else draw a centre dot
            pygame.draw.circle(dot_surf, CLR_LEGAL_DOT,
                               (SQ // 2, SQ // 2), SQ // 6)
            self.screen.blit(dot_surf, rect.topleft)

    def _draw_coord_labels(self, flipped: bool) -> None:
        files = "abcdefgh"
        ranks = "87654321"
        if flipped:
            files = files[::-1]
            ranks = ranks[::-1]

        for i in range(8):
            # File labels below board
            fc = (CLR_DARK_SQ if i % 2 == 0 else CLR_LIGHT_SQ)
            ft = self.label_font.render(files[i], True, fc)
            self.screen.blit(ft, (BOARD_LEFT + i * SQ + SQ - 12,
                                  BOARD_TOP + BOARD_SIZE - 16))
            # Rank labels on left
            rc = (CLR_LIGHT_SQ if i % 2 == 0 else CLR_DARK_SQ)
            rt = self.label_font.render(ranks[i], True, rc)
            self.screen.blit(rt, (BOARD_LEFT + 3, BOARD_TOP + i * SQ + 3))

    def _draw_pieces(self, board_str: str, flipped: bool) -> None:
        radius = SQ // 2 - 4
        for idx in range(64):
            draw_idx = (63 - idx) if flipped else idx
            ch = board_str[idx]
            if ch == '.':
                continue

            is_white = ch.isupper()
            rect = _sq_rect(draw_idx)
            cx, cy = rect.centerx, rect.centery

            # Outer ring (subtle border)
            ring_col  = CLR_WHITE_RING if is_white else CLR_BLACK_RING
            pygame.draw.circle(self.screen, ring_col, (cx, cy), radius + 2)

            # Filled circle body
            body_col = CLR_WHITE_PIECE if is_white else CLR_BLACK_PIECE
            pygame.draw.circle(self.screen, body_col, (cx, cy), radius)

            # Bold letter label
            label    = PIECE_LABEL.get(ch, ch)
            txt_col  = CLR_BLACK_PIECE if is_white else CLR_WHITE_PIECE
            surf = self.piece_font.render(label, True, txt_col)
            self.screen.blit(surf, surf.get_rect(center=(cx, cy)))

    def _draw_status_bar(self, status: str) -> None:
        bar = pygame.Rect(0, BOARD_TOP + BOARD_SIZE + 10, WIN_W, 40)
        pygame.draw.rect(self.screen, CLR_STATUS_BG, bar, border_radius=6)
        t = self.status_font.render(status, True, CLR_TEXT)
        self.screen.blit(t, t.get_rect(center=bar.center))

    def _draw_button(self, rect: pygame.Rect, label: str,
                     hovered: bool, bg: tuple, fg: tuple) -> None:
        color = CLR_BTN_HOVER if hovered else bg
        pygame.draw.rect(self.screen, color, rect, border_radius=10)
        pygame.draw.rect(self.screen, (200, 200, 200), rect, 2, border_radius=10)
        txt = self.btn_font.render(label, True, fg if not hovered else (30, 30, 30))
        self.screen.blit(txt, txt.get_rect(center=rect.center))

    def _draw_decorative_board(self) -> None:
        """Small decorative chess pattern in the background."""
        sq = 28
        for r in range(8):
            for c in range(8):
                col = CLR_DARK_SQ if (r + c) % 2 else CLR_LIGHT_SQ
                alpha_surf = pygame.Surface((sq, sq), pygame.SRCALPHA)
                alpha_surf.fill((*col, 40))
                self.screen.blit(alpha_surf, (WIN_W // 2 - 4 * sq + c * sq,
                                              WIN_H // 2 - 2 * sq + r * sq - 60))

    def click_to_square(self, mx: int, my: int, flipped: bool) -> int:
        """Convert mouse (mx, my) to board index, or -1 if off-board."""
        col = (mx - BOARD_LEFT) // SQ
        row = (my - BOARD_TOP)  // SQ
        if not (0 <= col < 8 and 0 <= row < 8):
            return -1
        if flipped:
            col = 7 - col
            row = 7 - row
        return row * 8 + col
