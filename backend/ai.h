#ifndef AI_H
#define AI_H

#include "board.h"

/* Returns best move for current player via minimax + alpha-beta */
Move get_best_move(Board *b, int depth);

#endif
