#ifndef EVAL_H
#define EVAL_H

#include "board.h"

/*
 * Static evaluation of the position.
 * Returns a score in centipawns from White's perspective:
 *   positive  -> good for White
 *   negative  -> good for Black
 */
int evaluate(const Board *b);

#endif /* EVAL_H */