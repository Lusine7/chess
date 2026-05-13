#ifndef MOVES_H
#define MOVES_H

#include "board.h"

#define MAX_MOVES 256

typedef struct {
    int from_rank, from_file;
    int to_rank,   to_file;
    int promotion; /* 0, or QUEEN / ROOK / BISHOP / KNIGHT */
} Move;

/* Attack & check queries */
int is_attacked(const Board *b, int rank, int file, int by_color);
int is_in_check(const Board *b, int color);

/* Move application (modifies board in-place) */
void apply_move(Board *b, const Move *m);

/* Move generation */
int generate_pseudo_moves(const Board *b, Move *moves); /* ignores check  */
int generate_legal_moves(Board *b, Move *moves);        /* fully legal    */

#endif /* MOVES_H */