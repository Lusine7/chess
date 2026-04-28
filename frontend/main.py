"""
main.py — Entry point for the Chess GUI.

Architecture
------------
  Renderer  — pure drawing (renderer.py)
  GameState — logic + protocol bridge (game.py)
  main()    — Pygame event loop

Controls
--------
  Left-click : select piece / move / choose promotion piece
  R          : restart game
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
WINDOW_TITLE = "Chess — AI opponent (minimax + α-β)"

# The AI is always BLACK in this build (human plays White).
PLAYER_COLOR = "white"

# Custom event fired when the AI's move has been computed
AI_MOVE_DONE = pygame.USEREVENT + 1


# ------------------------------------------------------------------ #
#  AI move (runs synchronously on main thread — engine is very fast)  #
# ------------------------------------------------------------------ #

def _trigger_ai(game: GameState) -> None:
    """
    Called once per frame when it's the AI's turn.
    Because the minimax search is fast (depth 4, < 1 s), we keep it
    synchronous so there's no need for threading.
    """
    game.request_ai_move()


# ------------------------------------------------------------------ #
#  main                                                                #
# ------------------------------------------------------------------ #

def main() -> None:
    pygame.init()
    pygame.display.set_caption(WINDOW_TITLE)

    screen   = pygame.display.set_mode((WINDOW_W, WINDOW_H))
    clock    = pygame.time.Clock()
    renderer = Renderer(screen, BOARD_SIZE)
    game     = GameState(player_color=PLAYER_COLOR)

    promo_hover: str | None = None   # which promo button the mouse is over

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
                    game.restart()
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
        if game.needs_ai_move and not game.ai_thinking and not game.game_over_msg:
            _trigger_ai(game)

        # ---- Rendering --------------------------------------------- #
        screen.fill((20, 20, 20))    # background behind board

        renderer.draw(
            board_state   = game.board,
            selected_sq   = game.selected_sq,
            legal_dests   = game.legal_dests,
            last_move     = game.last_move,
            in_check_sq   = game.in_check_sq,
            status_text   = game.status_text,
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
