#ifndef AI_H
#define AI_H

#include "board.h"
#include "moves.h"

/*
 * Search depth.  4 ply is strong enough to be challenging while still
 * responding in reasonable time (<2 s on modern hardware).
 * Increase for a stronger (but slower) engine.
 */
#define AI_DEPTH 4
#define INF      1000000

/*
 * Finds the best move for b->turn using minimax + alpha-beta pruning.
 * Writes the chosen move into *best and returns 1, or returns 0 if
 * there are no legal moves (checkmate / stalemate).
 */
int find_best_move(Board *b, Move *best);

#endif /* AI_H */