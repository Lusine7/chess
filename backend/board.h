#ifndef BOARD_H
#define BOARD_H

/* Piece codes: positive = white, negative = black, 0 = empty */
#define EMPTY   0
#define PAWN    1
#define KNIGHT  2
#define BISHOP  3
#define ROOK    4
#define QUEEN   5
#define KING    6

/* Castling rights bitmask */
#define CASTLE_WK 1
#define CASTLE_WQ 2
#define CASTLE_BK 4
#define CASTLE_BQ 8

/* Move flags */
#define FLAG_EN_PASSANT 1
#define FLAG_CASTLING   2
#define FLAG_PROMOTION  4

typedef struct {
    int squares[64]; /* index 0=a8, index 63=h1 */
    int turn;        /* 1=white, -1=black */
    int castling;    /* bitmask */
    int en_passant;  /* -1 or target square index */
    int halfmove_clock;
    int fullmove;
} Board;

typedef struct {
    int from, to;
    int promotion; /* 0 or piece code */
    int flags;
} Move;

typedef struct {
    int captured;
    int captured_sq; /* for en passant */
    int castling;
    int en_passant;
    int halfmove_clock;
} UndoInfo;

void board_init(Board *b);
void board_apply_move(Board *b, Move m, UndoInfo *u);
void board_undo_move(Board *b, Move m, UndoInfo *u);
void board_print(Board *b);

int  square_from_alg(const char *alg);
void alg_from_square(int sq, char *out);
char piece_to_char(int piece);
int  char_to_piece(char c);

#endif
