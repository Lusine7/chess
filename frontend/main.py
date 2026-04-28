"""
main.py – Entry point.

Launches the C engine subprocess, runs the pygame event loop.
"""

import sys
import os
import pygame

# Resolve paths relative to this file's location
BASE_DIR    = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.join(BASE_DIR, "..", "backend")
_exe_name = "chess.exe" if sys.platform == "win32" else "chess"
EXE_PATH  = os.path.join(BACKEND_DIR, _exe_name)

# Add frontend dir to path for sibling imports
sys.path.insert(0, BASE_DIR)

from protocol import ChessBackend
from game     import Game, Phase
from renderer import Renderer, WIN_W, WIN_H

FPS = 60


def main() -> None:
    if not os.path.isfile(EXE_PATH):
        print(f"ERROR: Chess engine not found at {EXE_PATH}")
        print("Please compile the backend first:")
        print("  cd backend && gcc -O2 -o chess main.c board.c moves.c ai.c eval.c")
        sys.exit(1)

    pygame.init()
    screen   = pygame.display.set_mode((WIN_W, WIN_H))
    pygame.display.set_caption("Chess – ENGS110")
    clock    = pygame.time.Clock()

    backend  = ChessBackend(EXE_PATH)
    game     = Game(backend)
    renderer = Renderer(screen)

    running  = True
    while running:
        mx, my = pygame.mouse.get_pos()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                # ── Color selection screen ──────────────────────────
                if game.phase == Phase.COLOR_SELECT:
                    if renderer.btn_white.collidepoint(mx, my):
                        game.start_game(player_color=1)
                    elif renderer.btn_black.collidepoint(mx, my):
                        game.start_game(player_color=-1)

                # ── Game over screen ────────────────────────────────
                elif game.phase == Phase.GAME_OVER:
                    if renderer.btn_again.collidepoint(mx, my):
                        # Restart: reinitialise game, keep same backend
                        game     = Game(backend)
                        renderer = Renderer(screen)

                # ── Active game ─────────────────────────────────────
                elif game.phase == Phase.PLAYER_TURN:
                    flipped = (game.player_color == -1)
                    sq = renderer.click_to_square(mx, my, flipped)
                    if sq >= 0:
                        game.handle_click(sq)

        # Let the game collect AI results
        game.update()

        # ── Draw ────────────────────────────────────────────────────
        flipped = (game.player_color == -1)

        if game.phase == Phase.COLOR_SELECT:
            renderer.draw_color_select(mx, my)

        else:
            renderer.draw_game(
                board_str   = game.board_str,
                selected    = game.selected_sq,
                legal_dests = game.legal_dests,
                last_move   = game.last_move,
                status      = game.status_msg,
                flipped     = flipped,
            )
            if game.phase == Phase.AI_THINKING:
                renderer.draw_thinking_spinner()
            elif game.phase == Phase.GAME_OVER:
                renderer.draw_game_over_overlay(game.game_over_msg, mx, my)

        pygame.display.flip()
        clock.tick(FPS)

    backend.quit()
    pygame.quit()


if __name__ == "__main__":
    main()
