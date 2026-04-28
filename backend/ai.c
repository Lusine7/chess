#include "ai.h"
#include "moves.h"
#include "eval.h"
#include <stdlib.h>

#define INF 1000000

/* Move ordering: put captures first to improve alpha-beta pruning */
static int move_score(Board *b, Move m) {
    return b->squares[m.to] != EMPTY ? 1 : 0;
}

static int cmp_moves(const void *a, const void *b_) {
    /* We need the board, but qsort doesn't pass context easily.
       Simple: captures (score=1) before quiets (score=0).
       We store the score in a scratch array instead – see negamax below. */
    (void)a; (void)b_; return 0;
}

/* Negamax with alpha-beta. Score is from the perspective of the side to move. */
static int negamax(Board *b, int depth, int alpha, int beta) {
    if (depth == 0) {
        /* evaluate() is always from white; adjust for current side */
        return b->turn * evaluate(b);
    }

    Move moves[256];
    int  count = generate_moves(b, moves);

    /* Order: captures first */
    for (int i = 0; i < count; i++) {
        for (int j = i + 1; j < count; j++) {
            if (move_score(b, moves[j]) > move_score(b, moves[i])) {
                Move tmp  = moves[i];
                moves[i]  = moves[j];
                moves[j]  = tmp;
            }
        }
    }

    int legal = 0;
    int best  = -INF;

    for (int i = 0; i < count; i++) {
        UndoInfo u;
        board_apply_move(b, moves[i], &u);

        /* skip if move left our king in check */
        if (is_in_check(b, -b->turn)) {
            board_undo_move(b, moves[i], &u);
            continue;
        }
        legal++;

        int score = -negamax(b, depth - 1, -beta, -alpha);
        board_undo_move(b, moves[i], &u);

        if (score > best)  best  = score;
        if (score > alpha) alpha = score;
        if (alpha >= beta) break; /* beta cutoff */
    }

    if (legal == 0) {
        /* No legal moves: checkmate or stalemate */
        if (is_in_check(b, b->turn))
            return -INF + (100 - depth); /* checkmate – prefer faster mates */
        return 0; /* stalemate */
    }

    return best;
}

Move get_best_move(Board *b, int depth) {
    Move moves[256];
    int  count = generate_moves(b, moves);

    Move best_move = moves[0];
    int  best_score = -INF - 1;
    int  alpha = -INF, beta = INF;

    for (int i = 0; i < count; i++) {
        UndoInfo u;
        board_apply_move(b, moves[i], &u);
        if (is_in_check(b, -b->turn)) {
            board_undo_move(b, moves[i], &u);
            continue;
        }
        int score = -negamax(b, depth - 1, -beta, -alpha);
        board_undo_move(b, moves[i], &u);

        if (score > best_score) {
            best_score = score;
            best_move  = moves[i];
            if (score > alpha) alpha = score;
        }
    }
    return best_move;
}
