#ifndef AI_H
#define AI_H

#include "board.h"
#include "moves.h"

#define INF 1000000

/*
 * Runtime search depth — set by the DEPTH <n> command from the frontend.
 * Defaults to 4 (intermediate).  Supported values: 2 (easy), 4, 6 (hard).
 */
extern int ai_depth;

/*
 * Finds the best move for b->turn using minimax + alpha-beta pruning.
 * Writes the chosen move into *best and returns 1, or returns 0 if
 * there are no legal moves (checkmate / stalemate).
 */
int find_best_move(Board *b, Move *best);

#endif /* AI_H */