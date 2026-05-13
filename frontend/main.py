"""
main.py — Entry point for the Chess GUI (Simplified).
"""

import sys
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
WINDOW_TITLE = "Chess"

# ------------------------------------------------------------------ #
#  UI Components                                                       #
# ------------------------------------------------------------------ #

class _Button:
    def __init__(self, rect, label, value):
        self.rect     = rect
        self.label    = label
        self.value    = value
        self.hovered  = False
        self.selected = False

    def draw(self, surface, font):
        bg = (100, 100, 100) if self.selected else ((60, 60, 60) if self.hovered else (40, 40, 40))
        fg = (255, 255, 255)
        pygame.draw.rect(surface, bg, self.rect)
        pygame.draw.rect(surface, (180, 180, 180), self.rect, 1) # Simple border
        
        txt = font.render(self.label, True, fg)
        surface.blit(txt, (self.rect.centerx - txt.get_width() // 2, 
                           self.rect.centery - txt.get_height() // 2))

    def update(self, mx, my):
        self.hovered = self.rect.collidepoint(mx, my)

    def hit(self, mx, my):
        return self.rect.collidepoint(mx, my)

def run_setup_screen(screen, clock):
    font_large = pygame.font.SysFont("monospace", 32, bold=True)
    font_small = pygame.font.SysFont("monospace", 18)
    
    W, H = screen.get_size()
    cx = W // 2
    
    color_btns = [
        _Button(pygame.Rect(cx - 110, 180, 100, 40), "White", "white"),
        _Button(pygame.Rect(cx + 10,  180, 100, 40), "Black", "black")
    ]
    color_btns[0].selected = True
    
    diff_btns = [
        _Button(pygame.Rect(cx - 160, 300, 100, 40), "Easy", 2),
        _Button(pygame.Rect(cx - 50,  300, 100, 40), "Med", 4),
        _Button(pygame.Rect(cx + 60,  300, 100, 40), "Hard", 6)
    ]
    diff_btns[1].selected = True
    
    start_btn = _Button(pygame.Rect(cx - 75, 420, 150, 50), "START", None)
    
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
                        btn.selected = True
                        selected_color = btn.value
                for btn in diff_btns:
                    if btn.hit(mx, my):
                        for b in diff_btns: b.selected = False
                        btn.selected = True
                        selected_depth = btn.value
                if start_btn.hit(mx, my):
                    return selected_color, selected_depth
        
        for b in color_btns + diff_btns + [start_btn]:
            b.update(mx, my)
            
        screen.fill((20, 20, 20))
        
        title = font_large.render("CHESS SETUP", True, (255, 255, 255))
        screen.blit(title, (cx - title.get_width() // 2, 80))
        
        lbl_col = font_small.render("CHOOSE COLOR", True, (150, 150, 150))
        screen.blit(lbl_col, (cx - lbl_col.get_width() // 2, 150))
        
        lbl_diff = font_small.render("CHOOSE DIFFICULTY", True, (150, 150, 150))
        screen.blit(lbl_diff, (cx - lbl_diff.get_width() // 2, 270))
        
        for b in color_btns + diff_btns + [start_btn]:
            b.draw(screen, font_small)
            
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