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
import math
import time as _time
import pygame

from renderer import Renderer, STATUS_HEIGHT
from game     import GameState

# ------------------------------------------------------------------ #
#  Window configuration                                                #
# ------------------------------------------------------------------ #
BOARD_SIZE   = 640
WINDOW_W     = BOARD_SIZE
WINDOW_H     = BOARD_SIZE + STATUS_HEIGHT
FPS          = 60
WINDOW_TITLE = "Chess - AI opponent (minimax + a-b)"

# ------------------------------------------------------------------ #
#  Palette                                                             #
# ------------------------------------------------------------------ #
C_BG          = ( 11,  13,  20)
C_PANEL       = ( 18,  21,  32)
C_BORDER_DIM  = ( 32,  36,  55)
C_BORDER      = ( 48,  53,  78)

C_GOLD        = (212, 170,  60)
C_GOLD_BRIGHT = (248, 208,  90)
C_GOLD_DIM    = (120, 100,  38)

C_TEXT        = (215, 218, 232)
C_SUBTEXT     = (115, 120, 148)
C_DIM         = ( 55,  60,  88)

C_BTN_IDLE    = ( 25,  29,  45)
C_BTN_HOVER   = ( 35,  40,  62)
C_BTN_SEL_BG  = ( 28,  50, 100)

C_EASY        = ( 72, 200,  95)
C_MED         = (235, 185,  50)
C_HARD        = (215,  65,  60)


# ------------------------------------------------------------------ #
#  Drawing helpers                                                     #
# ------------------------------------------------------------------ #

def draw_glow(surface, rect, color, layers=5, border_radius=12):
    for i in range(layers, 0, -1):
        inf = i * 5
        exp = rect.inflate(inf * 2, inf * 2)
        gs  = pygame.Surface(exp.size, pygame.SRCALPHA)
        pygame.draw.rect(gs, (*color[:3], int(50 / i)), gs.get_rect(),
                         border_radius=border_radius + inf)
        surface.blit(gs, exp.topleft)


def draw_divider(surface, cx, y, half=220):
    pygame.draw.line(surface, C_GOLD_DIM, (cx - half, y), (cx - 14, y), 1)
    pygame.draw.line(surface, C_GOLD_DIM, (cx + 14,   y), (cx + half, y), 1)
    d   = 6
    pts = [(cx, y - d), (cx + d, y), (cx, y + d), (cx - d, y)]
    pygame.draw.polygon(surface, C_GOLD, pts)


def draw_section_label(surface, cx, y, text, font):
    lbl = font.render(text, True, C_GOLD)
    lw  = lbl.get_width()
    pad = 14
    lx  = cx - lw // 2
    surface.blit(lbl, (lx, y - lbl.get_height() // 2))
    pygame.draw.line(surface, C_GOLD_DIM, (lx - pad - 60, y), (lx - pad, y), 1)
    pygame.draw.line(surface, C_GOLD_DIM, (lx + lw + pad, y), (lx + lw + pad + 60, y), 1)


def draw_king_icon(surface, cx, cy, size=24, color=C_GOLD):
    """Minimalist king silhouette: cross on top, trapezoid body."""
    s = size
    bar = max(2, s // 9)
    # Vertical cross bar
    pygame.draw.rect(surface, color,
                     (cx - bar // 2, cy - s // 2, bar, s // 2))
    # Horizontal cross bar
    pygame.draw.rect(surface, color,
                     (cx - s // 4, cy - s // 4, s // 2, bar))
    # Body (rounded rect)
    body_h = s // 2
    pygame.draw.rect(surface, color,
                     (cx - s // 2, cy - body_h // 4, s, body_h),
                     border_radius=4)


def draw_piece_swatch(surface, cx, cy, is_white, selected):
    r      = 10
    fill   = (238, 232, 212) if is_white else (30, 28, 36)
    border = (C_GOLD_BRIGHT if selected
              else ((200, 190, 165) if is_white else (90, 85, 100)))
    pygame.draw.circle(surface, fill,   (cx, cy), r)
    pygame.draw.circle(surface, border, (cx, cy), r, 2 if selected else 1)


# ------------------------------------------------------------------ #
#  Button                                                              #
# ------------------------------------------------------------------ #

class _Button:
    def __init__(self, rect, label, value,
                 indicator_color=None, is_start=False):
        self.rect            = rect
        self.label           = label
        self.value           = value
        self.hovered         = False
        self.selected        = False
        self.indicator_color = indicator_color
        self.is_start        = is_start

    def draw(self, surface, font):
        r = self.rect

        if self.is_start:
            bg = C_GOLD_BRIGHT if self.hovered else C_GOLD
            draw_glow(surface, r, bg, layers=3 if self.hovered else 2,
                      border_radius=14)
            pygame.draw.rect(surface, bg, r, border_radius=14)
            txt_col = (10, 10, 14)
        else:
            if self.selected:
                bg = C_BTN_SEL_BG
                draw_glow(surface, r, C_GOLD, layers=4, border_radius=11)
                bc, bw = C_GOLD, 2
            elif self.hovered:
                bg, bc, bw = C_BTN_HOVER, C_BORDER, 1
            else:
                bg, bc, bw = C_BTN_IDLE, C_BORDER_DIM, 1
            pygame.draw.rect(surface, bg, r, border_radius=11)
            pygame.draw.rect(surface, bc, r, bw, border_radius=11)
            txt_col = (255, 255, 255) if self.selected else C_TEXT

        lbl   = font.render(self.label, True, txt_col)
        dot_r = 7
        dot_g = 10

        if self.indicator_color:
            cw  = dot_r * 2 + dot_g + lbl.get_width()
            ox  = r.x + (r.width - cw) // 2
            oy  = r.y + (r.height - lbl.get_height()) // 2
            dcx = ox + dot_r
            dcy = r.y + r.height // 2
            pygame.draw.circle(surface, self.indicator_color, (dcx, dcy), dot_r)
            pygame.draw.circle(surface, (255, 255, 255),      (dcx, dcy), dot_r, 1)
            surface.blit(lbl, (ox + dot_r * 2 + dot_g, oy))

        elif self.is_start:
            # Triangle + text centred together
            tri_h, tri_w, tri_g = 14, 11, 10
            total = tri_w + tri_g + lbl.get_width()
            sx    = r.x + (r.width - total) // 2
            ty    = r.y + (r.height - tri_h) // 2
            sy    = r.y + (r.height - lbl.get_height()) // 2
            pts   = [(sx, ty), (sx, ty + tri_h), (sx + tri_w, ty + tri_h // 2)]
            pygame.draw.polygon(surface, (10, 10, 14), pts)
            surface.blit(lbl, (sx + tri_w + tri_g, sy))

        else:
            ox = r.x + (r.width  - lbl.get_width())  // 2
            oy = r.y + (r.height - lbl.get_height()) // 2
            surface.blit(lbl, (ox, oy))

    def update(self, mx, my):
        self.hovered = self.rect.collidepoint(mx, my)

    def hit(self, mx, my):
        return self.rect.collidepoint(mx, my)


# ------------------------------------------------------------------ #
#  SetupScreen                                                         #
# ------------------------------------------------------------------ #

def run_setup_screen(screen: pygame.Surface, clock: pygame.time.Clock):
    pygame.display.set_caption("Chess - Setup")

    font_title   = pygame.font.SysFont("georgia",  52, bold=True)
    font_sub     = pygame.font.SysFont("georgia",  16)
    font_section = pygame.font.SysFont("sans",     12, bold=True)
    font_btn     = pygame.font.SysFont("sans",     17, bold=True)
    font_start   = pygame.font.SysFont("sans",     21, bold=True)
    font_hint    = pygame.font.SysFont("monospace", 11)

    W, H = WINDOW_W, WINDOW_H
    cx   = W // 2

    HEADER_H = 128
    btn_w    = 162
    btn_h    = 50
    gap      = 14

    COLOR_Y  = 230     # vertical centre of color buttons
    DIFF_Y   = 378     # vertical centre of diff buttons
    START_Y  = 498
    START_W  = 214
    START_H  = 58

    color_btns = [
        _Button(pygame.Rect(cx - btn_w - gap // 2, COLOR_Y - btn_h // 2,
                            btn_w, btn_h), "White", "white"),
        _Button(pygame.Rect(cx + gap // 2,          COLOR_Y - btn_h // 2,
                            btn_w, btn_h), "Black", "black"),
    ]
    color_btns[0].selected = True

    diff_cfg = [
        ("Easy",         2, C_EASY),
        ("Intermediate", 4, C_MED),
        ("Hard",         6, C_HARD),
    ]
    total_dw = 3 * btn_w + 2 * gap
    dx0      = cx - total_dw // 2
    diff_btns = [
        _Button(pygame.Rect(dx0 + i * (btn_w + gap),
                            DIFF_Y - btn_h // 2, btn_w, btn_h),
                lbl, val, dot)
        for i, (lbl, val, dot) in enumerate(diff_cfg)
    ]
    diff_btns[1].selected = True

    start_btn = _Button(
        pygame.Rect(cx - START_W // 2, START_Y, START_W, START_H),
        "Start Game", None, is_start=True,
    )

    # Pre-bake chess texture surface
    sq_size = 44
    bg_tex  = pygame.Surface((W, H), pygame.SRCALPHA)
    for row in range(H // sq_size + 2):
        for col in range(W // sq_size + 2):
            if (row + col) % 2 == 0:
                pygame.draw.rect(bg_tex, (255, 255, 255, 7),
                                 (col * sq_size, row * sq_size,
                                  sq_size, sq_size))

    # Mini decorative board strip for header
    msq = 8
    mw, mh = 14 * msq, 3 * msq
    mini = pygame.Surface((mw, mh), pygame.SRCALPHA)
    for rr in range(mh // msq):
        for cc in range(mw // msq):
            a = (200, 165, 100, 60) if (rr + cc) % 2 == 0 \
                else ( 70,  50,  25, 60)
            pygame.draw.rect(mini, a, (cc * msq, rr * msq, msq, msq))

    depth_hints = {2: "Depth 2  —  quick & forgiving",
                   4: "Depth 4  —  balanced challenge",
                   6: "Depth 6  —  think carefully!"}

    selected_color = "white"
    selected_depth = 4

    while True:
        mx, my = pygame.mouse.get_pos()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit(); sys.exit(0)
            if event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_q, pygame.K_ESCAPE):
                    pygame.quit(); sys.exit(0)
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                for btn in color_btns:
                    if btn.hit(mx, my):
                        for b in color_btns: b.selected = False
                        btn.selected   = True
                        selected_color = btn.value
                for btn in diff_btns:
                    if btn.hit(mx, my):
                        for b in diff_btns: b.selected = False
                        btn.selected   = True
                        selected_depth = btn.value
                if start_btn.hit(mx, my):
                    return selected_color, selected_depth

        for b in color_btns + diff_btns + [start_btn]:
            b.update(mx, my)

        # ---- Draw -----------------------------------------------
        screen.fill(C_BG)
        screen.blit(bg_tex, (0, 0))

        # Header panel
        pygame.draw.rect(screen, C_PANEL, (0, 0, W, HEADER_H))
        # Mini board strips at header edges
        screen.blit(mini, (0, HEADER_H - mh))
        screen.blit(pygame.transform.flip(mini, True, False),
                    (W - mw, HEADER_H - mh))
        # Gold bottom border of header
        pygame.draw.line(screen, C_GOLD_DIM, (0, HEADER_H), (W, HEADER_H), 1)

        # King icon
        draw_king_icon(screen, cx - 114, 52, size=28, color=C_GOLD)

        # Title
        title = font_title.render("CHESS", True, C_GOLD_BRIGHT)
        screen.blit(title, (cx - title.get_width() // 2, 18))

        # Thin gold rule under title
        pygame.draw.line(screen, C_GOLD_DIM,
                         (cx - 120, 72), (cx + 120, 72), 1)

        # Subtitle
        sub = font_sub.render("Choose your side and difficulty",
                              True, C_SUBTEXT)
        screen.blit(sub, (cx - sub.get_width() // 2, 80))

        # ---- Color section ----------------------------------------
        draw_section_label(screen, cx,
                           COLOR_Y - btn_h // 2 - 26,
                           "CHOOSE YOUR COLOR", font_section)
        for btn in color_btns:
            btn.draw(screen, font_btn)
            draw_piece_swatch(screen,
                              btn.rect.x + 20,
                              btn.rect.y + btn.rect.height // 2,
                              btn.value == "white", btn.selected)

        # ---- Divider ----------------------------------------------
        div_y = (COLOR_Y + btn_h // 2 + DIFF_Y - btn_h // 2) // 2
        draw_divider(screen, cx, div_y)

        # ---- Difficulty section -----------------------------------
        draw_section_label(screen, cx,
                           DIFF_Y - btn_h // 2 - 26,
                           "DIFFICULTY", font_section)
        for btn in diff_btns:
            btn.draw(screen, font_btn)

        hint = font_hint.render(depth_hints[selected_depth], True, C_SUBTEXT)
        screen.blit(hint, (cx - hint.get_width() // 2,
                           DIFF_Y + btn_h // 2 + 11))

        # ---- Divider 2 -------------------------------------------
        draw_divider(screen, cx, START_Y - 22, half=160)

        # ---- Start button ----------------------------------------
        start_btn.draw(screen, font_start)

        # ---- Footer ----------------------------------------------
        footer = font_hint.render(
            "Q / Esc  to quit     |     R  to restart in-game",
            True, C_DIM)
        screen.blit(footer, (cx - footer.get_width() // 2, H - 24))

        pygame.display.flip()
        clock.tick(FPS)


# ------------------------------------------------------------------ #
#  AI move helper                                                      #
# ------------------------------------------------------------------ #

def _trigger_ai(game: GameState) -> None:
    game.start_ai_move_async()


# ------------------------------------------------------------------ #
#  main                                                                #
# ------------------------------------------------------------------ #

def main() -> None:
    pygame.init()
    screen = pygame.display.set_mode((WINDOW_W, WINDOW_H))
    clock  = pygame.time.Clock()

    player_color, depth = run_setup_screen(screen, clock)

    pygame.display.set_caption(WINDOW_TITLE)
    renderer    = Renderer(screen, BOARD_SIZE, flipped=(player_color == "black"))
    game        = GameState(player_color=player_color, depth=depth)
    promo_hover: str | None = None

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_q, pygame.K_ESCAPE):
                    running = False
                elif event.key == pygame.K_r:
                    game.engine.quit()
                    player_color, depth = run_setup_screen(screen, clock)
                    pygame.display.set_caption(WINDOW_TITLE)
                    renderer    = Renderer(screen, BOARD_SIZE,
                                           flipped=(player_color == "black"))
                    game        = GameState(player_color=player_color,
                                            depth=depth)
                    promo_hover = None
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                px, py = event.pos
                if py < BOARD_SIZE:
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

        if (game.needs_ai_move and not game.ai_thinking
                and not game.game_over_msg):
            _trigger_ai(game)

        screen.fill((20, 20, 20))

        dots        = "." * (int(_time.time() * 2) % 4)
        status_text = (f"AI is thinking{dots}"
                       if game.ai_thinking else game.status_text)

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

    game.engine.quit()
    pygame.quit()
    sys.exit(0)


if __name__ == "__main__":
    main()