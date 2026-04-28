"""
main.py — Entry point for the Chess GUI.

Architecture
------------
  SetupScreen — pre-game colour + difficulty picker (this file)
  Renderer    — pure drawing (renderer.py)
  GameState   — logic + protocol bridge (game.py)
  main()      — Pygame event loop

Controls
--------
  Left-click : select piece / move / choose promotion piece
  R          : restart (returns to setup screen)
  Q / Esc    : quit
"""

import sys
import pygame

from renderer import Renderer, STATUS_HEIGHT
from game     import GameState

# ------------------------------------------------------------------ #
#  Window configuration                                                #
# ------------------------------------------------------------------ #
BOARD_SIZE   = 640          # pixels  (must be divisible by 8)
WINDOW_W     = BOARD_SIZE
WINDOW_H     = BOARD_SIZE + STATUS_HEIGHT
FPS          = 60
WINDOW_TITLE = "Chess - AI opponent (minimax + a-b)"

# ------------------------------------------------------------------ #
#  Palette (shared between setup screen and game)                     #
# ------------------------------------------------------------------ #
C_BG         = ( 18,  18,  24)
C_PANEL      = ( 30,  30,  42)
C_BORDER     = ( 60,  60,  85)
C_ACCENT     = (255, 200,  60)   # gold
C_TEXT       = (220, 220, 230)
C_SUBTEXT    = (140, 140, 160)

C_BTN_IDLE   = ( 42,  42,  60)
C_BTN_HOVER  = ( 60,  60,  88)
C_BTN_SEL    = ( 80, 140, 220)   # blue highlight when selected
C_BTN_TXT    = (230, 230, 240)
C_BTN_TXT_S  = (255, 255, 255)

# Difficulty indicator colours
C_EASY   = ( 80, 200,  90)   # green
C_MED    = (240, 190,  50)   # yellow
C_HARD   = (220,  70,  70)   # red

# ------------------------------------------------------------------ #
#  SetupScreen                                                         #
# ------------------------------------------------------------------ #

class _Button:
    """
    A rounded rectangle button with hover + selected state.
    Optionally draws a small coloured circle indicator on the left.
    """

    def __init__(self, rect: pygame.Rect, label: str, value,
                 indicator_color=None):
        self.rect            = rect
        self.label           = label
        self.value           = value
        self.hovered         = False
        self.selected        = False
        self.indicator_color = indicator_color   # (r,g,b) or None

    def draw(self, screen: pygame.Surface, font: pygame.font.Font) -> None:
        if self.selected:
            bg     = C_BTN_SEL
            border = C_ACCENT
            lw     = 3
        elif self.hovered:
            bg     = C_BTN_HOVER
            border = C_BORDER
            lw     = 2
        else:
            bg     = C_BTN_IDLE
            border = C_BORDER
            lw     = 1

        pygame.draw.rect(screen, bg,     self.rect, border_radius=10)
        pygame.draw.rect(screen, border, self.rect, lw, border_radius=10)

        txt_col = C_BTN_TXT_S if self.selected else C_BTN_TXT
        lbl     = font.render(self.label, True, txt_col)

        # Total content width = optional dot + gap + text
        dot_r   = 7
        dot_gap = 10
        if self.indicator_color:
            content_w = dot_r * 2 + dot_gap + lbl.get_width()
        else:
            content_w = lbl.get_width()

        cx = self.rect.x + (self.rect.width  - content_w)  // 2
        cy = self.rect.y + (self.rect.height - lbl.get_height()) // 2

        if self.indicator_color:
            dot_cx = cx + dot_r
            dot_cy = self.rect.y + self.rect.height // 2
            pygame.draw.circle(screen, self.indicator_color,
                               (dot_cx, dot_cy), dot_r)
            # white outline so the dot pops on any background
            pygame.draw.circle(screen, (255, 255, 255),
                               (dot_cx, dot_cy), dot_r, 1)
            screen.blit(lbl, (cx + dot_r * 2 + dot_gap, cy))
        else:
            screen.blit(lbl, (cx, cy))

    def update(self, mx: int, my: int) -> None:
        self.hovered = self.rect.collidepoint(mx, my)

    def hit(self, mx: int, my: int) -> bool:
        return self.rect.collidepoint(mx, my)


def _draw_color_swatch(screen: pygame.Surface,
                       rect: pygame.Rect, is_white: bool) -> None:
    """Draw a small chess-colour swatch (filled circle) inside *rect*."""
    fill   = (240, 240, 240) if is_white else (40, 40, 40)
    border = (180, 180, 180) if is_white else (100, 100, 100)
    r = 9
    cx = rect.x + r + 8
    cy = rect.y + rect.height // 2
    pygame.draw.circle(screen, fill,   (cx, cy), r)
    pygame.draw.circle(screen, border, (cx, cy), r, 2)


def run_setup_screen(screen: pygame.Surface, clock: pygame.time.Clock):
    """
    Show the pre-game setup screen.
    Returns (player_color, depth) once the user clicks Start,
    or calls sys.exit() if they close the window.
    """
    pygame.display.set_caption("Chess - Setup")

    # ---- Fonts -------------------------------------------------------
    font_title  = pygame.font.SysFont("sans", 40, bold=True)
    font_label  = pygame.font.SysFont("sans", 20, bold=True)
    font_btn    = pygame.font.SysFont("sans", 18, bold=True)
    font_start  = pygame.font.SysFont("sans", 22, bold=True)
    font_hint   = pygame.font.SysFont("monospace", 13)

    # ---- Layout constants --------------------------------------------
    W, H  = WINDOW_W, WINDOW_H
    cx    = W // 2
    btn_w = 160
    btn_h = 48
    gap   = 16

    # ---- Color buttons -----------------------------------------------
    color_y = 200
    color_btns = [
        _Button(pygame.Rect(cx - btn_w - gap // 2, color_y, btn_w, btn_h),
                "White", "white"),
        _Button(pygame.Rect(cx + gap // 2,         color_y, btn_w, btn_h),
                "Black", "black"),
    ]
    color_btns[0].selected = True   # default: white

    # ---- Difficulty buttons ------------------------------------------
    diff_y   = 340
    diff_cfg = [
        ("Easy",         2, C_EASY),
        ("Intermediate", 4, C_MED),
        ("Hard",         6, C_HARD),
    ]
    total_diff_w = 3 * btn_w + 2 * gap
    diff_x0      = cx - total_diff_w // 2
    diff_btns = [
        _Button(
            pygame.Rect(diff_x0 + i * (btn_w + gap), diff_y, btn_w, btn_h),
            lbl, val, dot_col
        )
        for i, (lbl, val, dot_col) in enumerate(diff_cfg)
    ]
    diff_btns[1].selected = True   # default: intermediate

    # ---- Start button ------------------------------------------------
    start_w   = 200
    start_h   = 54
    start_btn = _Button(
        pygame.Rect(cx - start_w // 2, H - 130, start_w, start_h),
        "Start Game",
        None,
    )

    # ---- Decorative chess-board thumbnail ----------------------------
    thumb_sq  = 10
    thumb_off = (W - 8 * thumb_sq) // 2

    def _draw_thumbnail(y_off: int) -> None:
        for r in range(8):
            for f in range(8):
                col = (240, 217, 181) if (r + f) % 2 == 0 else (100, 70, 45)
                pygame.draw.rect(
                    screen, col,
                    (thumb_off + f * thumb_sq, y_off + r * thumb_sq,
                     thumb_sq, thumb_sq)
                )

    def _draw_play_triangle(surf: pygame.Surface,
                            btn: _Button, col) -> None:
        """Draw a small right-pointing triangle (play icon) inside *btn*."""
        bx, by, bw, bh = btn.rect
        th = 14        # triangle height
        tw = 11        # triangle base width
        tx = bx + bw // 2 - 50   # shifted left so it sits before the text
        ty = by + (bh - th) // 2
        pts = [(tx, ty), (tx, ty + th), (tx + tw, ty + th // 2)]
        pygame.draw.polygon(surf, col, pts)

    # ---- Color-button swatch positions (drawn before text so rect known) --
    # We'll draw them in the loop

    # ---- Main loop ---------------------------------------------------
    selected_color = "white"
    selected_depth = 4

    while True:
        mx, my = pygame.mouse.get_pos()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit(0)

            if event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_q, pygame.K_ESCAPE):
                    pygame.quit()
                    sys.exit(0)

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                for btn in color_btns:
                    if btn.hit(mx, my):
                        for b in color_btns:
                            b.selected = False
                        btn.selected   = True
                        selected_color = btn.value

                for btn in diff_btns:
                    if btn.hit(mx, my):
                        for b in diff_btns:
                            b.selected = False
                        btn.selected   = True
                        selected_depth = btn.value

                if start_btn.hit(mx, my):
                    return selected_color, selected_depth

        # ---- Hover updates ------------------------------------------
        for b in color_btns + diff_btns:
            b.update(mx, my)
        start_btn.update(mx, my)

        # ---- Draw ---------------------------------------------------
        screen.fill(C_BG)

        # Top bar
        pygame.draw.rect(screen, C_PANEL, (0, 0, W, 110))
        pygame.draw.line(screen, C_BORDER, (0, 110), (W, 110), 1)

        # Title — plain ASCII, no emoji
        title = font_title.render("Chess Setup", True, C_ACCENT)
        screen.blit(title, (cx - title.get_width() // 2, 34))

        # Subtitle
        sub = font_hint.render("AI opponent  |  minimax + alpha-beta pruning",
                               True, C_SUBTEXT)
        screen.blit(sub, (cx - sub.get_width() // 2, 80))

        # Tiny board thumbnail
        _draw_thumbnail(120)

        # Section: Choose your color
        lbl = font_label.render("Choose Your Color", True, C_TEXT)
        screen.blit(lbl, (cx - lbl.get_width() // 2, color_y - 36))

        # Draw colour buttons with swatch overlaid
        for btn in color_btns:
            btn.draw(screen, font_btn)
            is_white = (btn.value == "white")
            _draw_color_swatch(screen, btn.rect, is_white)

        # Section: Difficulty
        lbl2 = font_label.render("Difficulty", True, C_TEXT)
        screen.blit(lbl2, (cx - lbl2.get_width() // 2, diff_y - 36))
        for btn in diff_btns:
            btn.draw(screen, font_btn)

        # Depth hint
        depth_map = {2: "Depth 2 - quick & forgiving",
                     4: "Depth 4 - balanced challenge",
                     6: "Depth 6 - think carefully!"}
        hint_txt = font_hint.render(depth_map[selected_depth], True, C_SUBTEXT)
        screen.blit(hint_txt,
                    (cx - hint_txt.get_width() // 2, diff_y + btn_h + 10))

        # Start button
        start_btn.draw(screen, font_start)
        # Draw play triangle on top of the start button
        tri_col = C_BTN_TXT_S if start_btn.selected or start_btn.hovered \
                  else C_BTN_TXT
        _draw_play_triangle(screen, start_btn, tri_col)

        # Bottom hint
        q_hint = font_hint.render("Q / Esc to quit   |   R in-game to restart",
                                  True, C_SUBTEXT)
        screen.blit(q_hint, (cx - q_hint.get_width() // 2, H - 28))

        pygame.display.flip()
        clock.tick(FPS)


# ------------------------------------------------------------------ #
#  AI move helper                                                      #
# ------------------------------------------------------------------ #

def _trigger_ai(game: GameState) -> None:
    """
    Start the AI move in a background thread so the event loop
    stays responsive while the engine is searching at any depth.
    """
    game.start_ai_move_async()


# ------------------------------------------------------------------ #
#  main                                                                #
# ------------------------------------------------------------------ #

def main() -> None:
    pygame.init()
    screen = pygame.display.set_mode((WINDOW_W, WINDOW_H))
    clock  = pygame.time.Clock()

    # ---- Setup screen -----------------------------------------------
    player_color, depth = run_setup_screen(screen, clock)

    # ---- Game -------------------------------------------------------
    pygame.display.set_caption(WINDOW_TITLE)
    renderer    = Renderer(screen, BOARD_SIZE)
    game        = GameState(player_color=player_color, depth=depth)
    promo_hover: str | None = None

    running = True
    while running:
        # ---- Event handling ---------------------------------------- #
        for event in pygame.event.get():

            if event.type == pygame.QUIT:
                running = False

            elif event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_q, pygame.K_ESCAPE):
                    running = False
                elif event.key == pygame.K_r:
                    # Return to setup screen
                    game.engine.quit()
                    player_color, depth = run_setup_screen(screen, clock)
                    pygame.display.set_caption(WINDOW_TITLE)
                    game        = GameState(player_color=player_color,
                                            depth=depth)
                    promo_hover = None

            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                px, py = event.pos
                if py < BOARD_SIZE:                  # click is on the board
                    if game.promo_pending:
                        piece = renderer.promo_piece_at(px, py)
                        if piece:
                            game.choose_promotion(piece)
                            promo_hover = None
                    else:
                        sq = renderer.px_to_sq(px, py)
                        if sq:
                            game.click_square(*sq)

            elif event.type == pygame.MOUSEMOTION:
                px, py = event.pos
                if game.promo_pending and py < BOARD_SIZE:
                    promo_hover = renderer.promo_piece_at(px, py)
                else:
                    promo_hover = None

        # ---- AI turn ----------------------------------------------- #
        if (game.needs_ai_move and not game.ai_thinking
                and not game.game_over_msg):
            _trigger_ai(game)

        # ---- Rendering --------------------------------------------- #
        screen.fill((20, 20, 20))    # background behind board

        # Show a live "thinking" status while the engine is searching
        if game.ai_thinking:
            import math, time as _time
            dots = "." * (int(_time.time() * 2) % 4)
            status_text = f"AI is thinking{dots}"
        else:
            status_text = game.status_text

        renderer.draw(
            board_state   = game.board,
            selected_sq   = game.selected_sq,
            legal_dests   = game.legal_dests,
            last_move     = game.last_move,
            in_check_sq   = game.in_check_sq,
            status_text   = status_text,
            turn_color    = game.turn,
            game_over     = game.game_over_msg,
            promo_pending = game.promo_pending,
            promo_hover   = promo_hover,
        )

        pygame.display.flip()
        clock.tick(FPS)

    # ---- Cleanup --------------------------------------------------- #
    game.engine.quit()
    pygame.quit()
    sys.exit(0)


if __name__ == "__main__":
    main()