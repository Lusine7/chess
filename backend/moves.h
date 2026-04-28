#ifndef MOVES_H
#define MOVES_H

#include "board.h"

int generate_moves(Board *b, Move *out);         /* pseudo-legal */
int generate_legal_moves(Board *b, Move *out);   /* legal only */
int is_in_check(Board *b, int color);
int is_square_attacked(Board *b, int sq, int by_color);

#endif
