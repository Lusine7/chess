#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "board.h"
#include "moves.h"
#include "ai.h"

#define AI_DEPTH 4

static Board board;

/* Check game-over after a move has been applied.
   Prints GAME_OVER line if needed. Returns 1 if game is over. */
static int check_game_over(void) {
    Move legal[256];
    int  count = generate_legal_moves(&board, legal);
    if (count == 0) {
        if (is_in_check(&board, board.turn)) {
            /* The side that just moved wins */
            printf("GAME_OVER %s\n", board.turn == 1 ? "BLACK_WIN" : "WHITE_WIN");
        } else {
            printf("GAME_OVER DRAW\n");
        }
        fflush(stdout);
        return 1;
    }
    return 0;
}

/* Parse "e2e4" or "e7e8Q" into a Move, validate, apply.
   Returns 1 on success, 0 on illegal move.                 */
static int parse_and_apply(const char *mv) {
    if (strlen(mv) < 4) return 0;

    int from = square_from_alg(mv);
    int to   = square_from_alg(mv + 2);
    if (from < 0 || to < 0) return 0;

    /* Find matching legal move */
    Move legal[256];
    int  count = generate_legal_moves(&board, legal);
    int  promo_piece = 0;
    if (strlen(mv) >= 5) {
        switch (mv[4]) {
            case 'q': case 'Q': promo_piece = QUEEN;  break;
            case 'r': case 'R': promo_piece = ROOK;   break;
            case 'b': case 'B': promo_piece = BISHOP; break;
            case 'n': case 'N': promo_piece = KNIGHT; break;
        }
    }

    for (int i = 0; i < count; i++) {
        if (legal[i].from != from || legal[i].to != to) continue;
        if (legal[i].flags & FLAG_PROMOTION) {
            if (promo_piece == 0) promo_piece = QUEEN; /* default */
            if (legal[i].promotion != promo_piece) continue;
        }
        UndoInfo u;
        board_apply_move(&board, legal[i], &u);
        return 1;
    }
    return 0;
}

int main(void) {
    /* Disable stdout buffering so Python subprocess gets lines immediately */
    setvbuf(stdout, NULL, _IONBF, 0);

    board_init(&board);

    char line[256];
    while (fgets(line, sizeof(line), stdin)) {
        /* Strip trailing newline/CR */
        int len = (int)strlen(line);
        while (len > 0 && (line[len-1] == '\n' || line[len-1] == '\r'))
            line[--len] = '\0';

        if (len == 0) continue;

        /* ---- INIT ---- */
        if (strcmp(line, "INIT") == 0) {
            board_init(&board);
            board_print(&board);

        /* ---- MOVE <from><to>[promo] ---- */
        } else if (strncmp(line, "MOVE ", 5) == 0) {
            const char *mv = line + 5;
            if (parse_and_apply(mv)) {
                board_print(&board);
                check_game_over();
            } else {
                printf("ERROR Illegal move: %s\n", mv);
                fflush(stdout);
            }

        /* ---- AI_MOVE ---- */
        } else if (strcmp(line, "AI_MOVE") == 0) {
            Move best = get_best_move(&board, AI_DEPTH);
            UndoInfo u;
            board_apply_move(&board, best, &u);

            char from_s[3], to_s[3];
            alg_from_square(best.from, from_s);
            alg_from_square(best.to,   to_s);

            if (best.flags & FLAG_PROMOTION) {
                char promo_ch = piece_to_char(best.promotion); /* uppercase */
                printf("AI_MOVE %s%s%c\n", from_s, to_s, promo_ch);
            } else {
                printf("AI_MOVE %s%s\n", from_s, to_s);
            }
            fflush(stdout);
            board_print(&board);
            check_game_over();

        /* ---- LEGAL <sq> ---- */
        } else if (strncmp(line, "LEGAL ", 6) == 0) {
            int src = square_from_alg(line + 6);
            Move legal[256];
            int  count = generate_legal_moves(&board, legal);
            printf("LEGAL_MOVES");
            for (int i = 0; i < count; i++) {
                if (legal[i].from == src) {
                    char dst[3];
                    alg_from_square(legal[i].to, dst);
                    printf(" %s", dst);
                }
            }
            printf("\n");
            fflush(stdout);

        /* ---- QUIT ---- */
        } else if (strcmp(line, "QUIT") == 0) {
            break;
        } else {
            printf("ERROR Unknown command: %s\n", line);
            fflush(stdout);
        }
    }
    return 0;
}
