#include "ai.h"
#include "eval.h"

/* ------------------------------------------------------------------ */
/*  minimax — recursive alpha-beta search                               */
/*                                                                      */
/*  depth      : plies remaining (0 = leaf, return static eval)        */
/*  alpha      : best score the maximiser can already guarantee        */
/*  beta       : best score the minimiser can already guarantee        */
/*  maximizing : 1 if it's White's turn to move at this node           */
/* ------------------------------------------------------------------ */
static int minimax(Board *b, int depth, int alpha, int beta, int maximizing) {

    /* ---- Leaf node: return static evaluation ---- */
    if (depth == 0)
        return evaluate(b);

    Move moves[MAX_MOVES];
    int  n = generate_legal_moves(b, moves);

    /* ---- Terminal node: checkmate or stalemate ---- */
    if (n == 0) {
        if (is_in_check(b, b->turn)) {
            /*
             * Checkmate. Return a large score weighted by depth so the
             * engine prefers shorter mates (or delays being mated).
             */
            return maximizing ? -INF + (AI_DEPTH - depth)
                              :  INF - (AI_DEPTH - depth);
        }
        return 0; /* Stalemate */
    }

    if (maximizing) {
        int best = -INF;
        for (int i = 0; i < n; i++) {
            Board tmp;
            copy_board(&tmp, b);
            apply_move(&tmp, &moves[i]);
            int score = minimax(&tmp, depth - 1, alpha, beta, 0);
            if (score > best)  best  = score;
            if (score > alpha) alpha = score;
            if (alpha >= beta) break;   /* beta cut-off */
        }
        return best;
    } else {
        int best = INF;
        for (int i = 0; i < n; i++) {
            Board tmp;
            copy_board(&tmp, b);
            apply_move(&tmp, &moves[i]);
            int score = minimax(&tmp, depth - 1, alpha, beta, 1);
            if (score < best) best = score;
            if (score < beta) beta = score;
            if (alpha >= beta) break;   /* alpha cut-off */
        }
        return best;
    }
}

/* ------------------------------------------------------------------ */
/*  find_best_move                                                       */
/* ------------------------------------------------------------------ */
int find_best_move(Board *b, Move *best) {
    Move moves[MAX_MOVES];
    int  n = generate_legal_moves(b, moves);
    if (n == 0) return 0;

    int maximizing  = (b->turn == WHITE);
    int best_score  = maximizing ? -INF : INF;
    *best = moves[0]; /* safe default */

    for (int i = 0; i < n; i++) {
        Board tmp;
        copy_board(&tmp, b);
        apply_move(&tmp, &moves[i]);

        int score = minimax(&tmp, AI_DEPTH - 1, -INF, INF, !maximizing);

        if (maximizing ? (score > best_score) : (score < best_score)) {
            best_score = score;
            *best      = moves[i];
        }
    }

    return 1;
}