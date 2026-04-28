#include "board.h"
#include <stdio.h>
#include <string.h>
#include <stdlib.h>

/* Board layout: index 0 = a8 (top-left), index 63 = h1 (bottom-right)
   Rank 8 = indices  0-7,  Rank 7 = indices  8-15,
   Rank 2 = indices 48-55, Rank 1 = indices 56-63                        */

void board_init(Board *b) {
    memset(b->squares, 0, sizeof(b->squares));

    /* Black pieces – rank 8 (indices 0-7): r n b q k b n r */
    b->squares[0] = -ROOK;   b->squares[1] = -KNIGHT;
    b->squares[2] = -BISHOP; b->squares[3] = -QUEEN;
    b->squares[4] = -KING;   b->squares[5] = -BISHOP;
    b->squares[6] = -KNIGHT; b->squares[7] = -ROOK;
    /* Black pawns – rank 7 (indices 8-15) */
    for (int i = 8; i < 16; i++) b->squares[i] = -PAWN;

    /* White pawns – rank 2 (indices 48-55) */
    for (int i = 48; i < 56; i++) b->squares[i] = PAWN;
    /* White pieces – rank 1 (indices 56-63): R N B Q K B N R */
    b->squares[56] = ROOK;   b->squares[57] = KNIGHT;
    b->squares[58] = BISHOP; b->squares[59] = QUEEN;
    b->squares[60] = KING;   b->squares[61] = BISHOP;
    b->squares[62] = KNIGHT; b->squares[63] = ROOK;

    b->turn           = 1; /* white first */
    b->castling       = CASTLE_WK | CASTLE_WQ | CASTLE_BK | CASTLE_BQ;
    b->en_passant     = -1;
    b->halfmove_clock = 0;
    b->fullmove       = 1;
}

char piece_to_char(int piece) {
    static const char *w = ".PNBRQK";
    static const char *bl = ".pnbrqk";
    if (piece > 0 && piece <= 6) return w[piece];
    if (piece < 0 && piece >= -6) return bl[-piece];
    return '.';
}

int char_to_piece(char c) {
    switch (c) {
        case 'P': return  PAWN;   case 'p': return -PAWN;
        case 'N': return  KNIGHT; case 'n': return -KNIGHT;
        case 'B': return  BISHOP; case 'b': return -BISHOP;
        case 'R': return  ROOK;   case 'r': return -ROOK;
        case 'Q': return  QUEEN;  case 'q': return -QUEEN;
        case 'K': return  KING;   case 'k': return -KING;
        default:  return  EMPTY;
    }
}

/* "e2" -> index 52.  index = (8 - rank) * 8 + file */
int square_from_alg(const char *alg) {
    if (!alg || alg[0] < 'a' || alg[0] > 'h') return -1;
    if (!alg[1] || alg[1] < '1' || alg[1] > '8') return -1;
    int file = alg[0] - 'a';
    int rank = alg[1] - '1'; /* 0-based, 0=rank1 */
    return (7 - rank) * 8 + file;
}

/* index 52 -> "e2" */
void alg_from_square(int sq, char *out) {
    out[0] = 'a' + (sq % 8);
    out[1] = '1' + (7 - sq / 8);
    out[2] = '\0';
}

void board_print(Board *b) {
    printf("BOARD ");
    for (int i = 0; i < 64; i++) printf("%c", piece_to_char(b->squares[i]));
    printf("\n");
    fflush(stdout);
}

void board_apply_move(Board *b, Move m, UndoInfo *u) {
    u->captured      = b->squares[m.to];
    u->captured_sq   = -1;
    u->castling      = b->castling;
    u->en_passant    = b->en_passant;
    u->halfmove_clock= b->halfmove_clock;

    int piece     = b->squares[m.from];
    int abs_piece = piece < 0 ? -piece : piece;

    /* halfmove clock */
    b->halfmove_clock = (abs_piece == PAWN || u->captured != EMPTY) ? 0
                                                                     : b->halfmove_clock + 1;

    /* en passant target – reset then set if double pawn push */
    b->en_passant = -1;
    if (abs_piece == PAWN && (m.to - m.from == -16 || m.to - m.from == 16))
        b->en_passant = (m.from + m.to) / 2;

    /* en passant capture: remove the captured pawn */
    if (m.flags & FLAG_EN_PASSANT) {
        int cap_sq = m.to + (b->turn == 1 ? 8 : -8);
        u->captured    = b->squares[cap_sq];
        u->captured_sq = cap_sq;
        b->squares[cap_sq] = EMPTY;
    }

    /* castling: move the rook */
    if (m.flags & FLAG_CASTLING) {
        if      (m.to == 62) { b->squares[61] = b->squares[63]; b->squares[63] = EMPTY; } /* WK */
        else if (m.to == 58) { b->squares[59] = b->squares[56]; b->squares[56] = EMPTY; } /* WQ */
        else if (m.to ==  6) { b->squares[ 5] = b->squares[ 7]; b->squares[ 7] = EMPTY; } /* BK */
        else if (m.to ==  2) { b->squares[ 3] = b->squares[ 0]; b->squares[ 0] = EMPTY; } /* BQ */
    }

    /* update castling rights */
    if (abs_piece == KING) {
        if (b->turn == 1) b->castling &= ~(CASTLE_WK | CASTLE_WQ);
        else              b->castling &= ~(CASTLE_BK | CASTLE_BQ);
    }
    if (m.from == 56 || m.to == 56) b->castling &= ~CASTLE_WQ;
    if (m.from == 63 || m.to == 63) b->castling &= ~CASTLE_WK;
    if (m.from ==  0 || m.to ==  0) b->castling &= ~CASTLE_BQ;
    if (m.from ==  7 || m.to ==  7) b->castling &= ~CASTLE_BK;

    /* move piece */
    b->squares[m.to]   = piece;
    b->squares[m.from] = EMPTY;

    /* promotion */
    if (m.flags & FLAG_PROMOTION)
        b->squares[m.to] = b->turn * m.promotion;

    if (b->turn == -1) b->fullmove++;
    b->turn = -b->turn;
}

void board_undo_move(Board *b, Move m, UndoInfo *u) {
    b->turn = -b->turn; /* restore turn first */

    int piece = b->squares[m.to];

    /* restore moving piece (handle promotion: it was a pawn) */
    b->squares[m.from] = (m.flags & FLAG_PROMOTION) ? b->turn * PAWN : piece;
    b->squares[m.to]   = u->captured;

    /* restore en-passant captured pawn */
    if (m.flags & FLAG_EN_PASSANT && u->captured_sq >= 0) {
        b->squares[u->captured_sq] = u->captured;
        b->squares[m.to]           = EMPTY;
    }

    /* restore castling rook */
    if (m.flags & FLAG_CASTLING) {
        if      (m.to == 62) { b->squares[63] = b->squares[61]; b->squares[61] = EMPTY; }
        else if (m.to == 58) { b->squares[56] = b->squares[59]; b->squares[59] = EMPTY; }
        else if (m.to ==  6) { b->squares[ 7] = b->squares[ 5]; b->squares[ 5] = EMPTY; }
        else if (m.to ==  2) { b->squares[ 0] = b->squares[ 3]; b->squares[ 3] = EMPTY; }
    }

    b->castling       = u->castling;
    b->en_passant     = u->en_passant;
    b->halfmove_clock = u->halfmove_clock;
    if (b->turn == -1) b->fullmove--;
}
