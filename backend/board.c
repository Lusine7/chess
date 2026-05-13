#include "board.h"

void board_init(Board *b) {
    memset(b->squares, 0, sizeof(b->squares));

    /* White back rank (rank index 0 = chess rank 1) */
    b->squares[0][0] =  ROOK;
    b->squares[0][1] =  KNIGHT;
    b->squares[0][2] =  BISHOP;
    b->squares[0][3] =  QUEEN;
    b->squares[0][4] =  KING;
    b->squares[0][5] =  BISHOP;
    b->squares[0][6] =  KNIGHT;
    b->squares[0][7] =  ROOK;

    /* White pawns (rank index 1 = chess rank 2) */
    for (int f = 0; f < 8; f++)
        b->squares[1][f] = PAWN;

    /* Black pawns (rank index 6 = chess rank 7) */
    for (int f = 0; f < 8; f++)
        b->squares[6][f] = -PAWN;

    /* Black back rank (rank index 7 = chess rank 8) */
    b->squares[7][0] = -ROOK;
    b->squares[7][1] = -KNIGHT;
    b->squares[7][2] = -BISHOP;
    b->squares[7][3] = -QUEEN;
    b->squares[7][4] = -KING;
    b->squares[7][5] = -BISHOP;
    b->squares[7][6] = -KNIGHT;
    b->squares[7][7] = -ROOK;

    b->turn            = WHITE;
    b->white_castle_k  = 1;
    b->white_castle_q  = 1;
    b->black_castle_k  = 1;
    b->black_castle_q  = 1;
    b->ep_rank         = -1;
    b->ep_file         = -1;
    b->halfmove_clock  = 0;
    b->fullmove_number = 1;
}

void copy_board(Board *dst, const Board *src) {
    memcpy(dst, src, sizeof(Board));
}

int board_color(int piece) {
    if (piece > 0) return WHITE;
    if (piece < 0) return BLACK;
    return 0;
}

int board_type(int piece) {
    return piece < 0 ? -piece : piece;
}

void sq_to_str(int rank, int file, char *out) {
    out[0] = 'a' + file;
    out[1] = '1' + rank;
    out[2] = '\0';
}

int str_to_rank(const char *sq) {
    return sq[1] - '1';
}

int str_to_file(const char *sq) {
    return sq[0] - 'a';
}