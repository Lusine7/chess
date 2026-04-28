#include "moves.h"
#include <stdlib.h>

/* ------------------------------------------------------------------ */
/*  Helpers                                                             */
/* ------------------------------------------------------------------ */

static int in_bounds(int rank, int file) {
    return rank >= 0 && rank < 8 && file >= 0 && file < 8;
}

/* ------------------------------------------------------------------ */
/*  Attack detection                                                    */
/* ------------------------------------------------------------------ */

/*
 * Returns 1 if (rank, file) is attacked by any piece of `by_color`.
 * Used both for check detection and castling legality.
 */
int is_attacked(const Board *b, int rank, int file, int by_color) {

    /* --- Pawn attacks ---
     * White pawns move up (+rank), so a white pawn at (r,f) attacks (r+1, f±1).
     * Therefore (rank,file) is attacked by a white pawn sitting at (rank-1, file±1).
     * For black it's the mirror: look at (rank+1, file±1).
     */
    int pawn_src_rank = (by_color == WHITE) ? rank - 1 : rank + 1;
    for (int df = -1; df <= 1; df += 2) {
        int pf = file + df;
        if (in_bounds(pawn_src_rank, pf) &&
            b->squares[pawn_src_rank][pf] == by_color * PAWN)
            return 1;
    }

    /* --- Knight attacks --- */
    static const int kn[8][2] = {
        {-2,-1},{-2,1},{-1,-2},{-1,2},{1,-2},{1,2},{2,-1},{2,1}
    };
    for (int i = 0; i < 8; i++) {
        int nr = rank + kn[i][0], nf = file + kn[i][1];
        if (in_bounds(nr, nf) && b->squares[nr][nf] == by_color * KNIGHT)
            return 1;
    }

    /* --- Diagonal sliders (bishop / queen) --- */
    static const int diag[4][2] = {{1,1},{1,-1},{-1,1},{-1,-1}};
    for (int i = 0; i < 4; i++) {
        int r = rank + diag[i][0], f = file + diag[i][1];
        while (in_bounds(r, f)) {
            int p = b->squares[r][f];
            if (p != EMPTY) {
                if (p == by_color * BISHOP || p == by_color * QUEEN) return 1;
                break;
            }
            r += diag[i][0]; f += diag[i][1];
        }
    }

    /* --- Straight sliders (rook / queen) --- */
    static const int straight[4][2] = {{1,0},{-1,0},{0,1},{0,-1}};
    for (int i = 0; i < 4; i++) {
        int r = rank + straight[i][0], f = file + straight[i][1];
        while (in_bounds(r, f)) {
            int p = b->squares[r][f];
            if (p != EMPTY) {
                if (p == by_color * ROOK || p == by_color * QUEEN) return 1;
                break;
            }
            r += straight[i][0]; f += straight[i][1];
        }
    }

    /* --- King attacks --- */
    for (int dr = -1; dr <= 1; dr++) {
        for (int df = -1; df <= 1; df++) {
            if (dr == 0 && df == 0) continue;
            int nr = rank + dr, nf = file + df;
            if (in_bounds(nr, nf) && b->squares[nr][nf] == by_color * KING)
                return 1;
        }
    }

    return 0;
}

/* Returns 1 if `color`'s king is currently in check. */
int is_in_check(const Board *b, int color) {
    for (int r = 0; r < 8; r++)
        for (int f = 0; f < 8; f++)
            if (b->squares[r][f] == color * KING)
                return is_attacked(b, r, f, -color);
    return 0; /* shouldn't happen */
}

/* ------------------------------------------------------------------ */
/*  Pseudo-move generation helpers                                      */
/* ------------------------------------------------------------------ */

static void add_move(Move *moves, int *cnt,
                     int fr, int ff, int tr, int tf, int promo) {
    moves[*cnt].from_rank  = fr;
    moves[*cnt].from_file  = ff;
    moves[*cnt].to_rank    = tr;
    moves[*cnt].to_file    = tf;
    moves[*cnt].promotion  = promo;
    (*cnt)++;
}

/*
 * Add a pawn move, expanding to four promotion moves when the pawn
 * reaches the back rank.
 */
static void add_pawn_move(Move *moves, int *cnt,
                          int fr, int ff, int tr, int tf, int color) {
    int promo_rank = (color == WHITE) ? 7 : 0;
    if (tr == promo_rank) {
        add_move(moves, cnt, fr, ff, tr, tf, QUEEN);
        add_move(moves, cnt, fr, ff, tr, tf, ROOK);
        add_move(moves, cnt, fr, ff, tr, tf, BISHOP);
        add_move(moves, cnt, fr, ff, tr, tf, KNIGHT);
    } else {
        add_move(moves, cnt, fr, ff, tr, tf, 0);
    }
}

/* ------------------------------------------------------------------ */
/*  Pseudo-move generation                                              */
/* ------------------------------------------------------------------ */

int generate_pseudo_moves(const Board *b, Move *moves) {
    int count = 0;
    int color = b->turn;
    int opp   = -color;

    /* Sliding piece directions: [0..3] diagonal, [4..7] straight */
    static const int dirs[8][2] = {
        {1,1},{1,-1},{-1,1},{-1,-1},
        {1,0},{-1,0},{0,1},{0,-1}
    };

    for (int r = 0; r < 8; r++) {
        for (int f = 0; f < 8; f++) {
            int piece = b->squares[r][f];
            if (board_color(piece) != color) continue;
            int type  = board_type(piece);

            switch (type) {

            /* ---- Pawn ---- */
            case PAWN: {
                int dir        = color;            /* WHITE=+1, BLACK=-1 */
                int start_rank = (color == WHITE) ? 1 : 6;
                int nr         = r + dir;

                /* Single push */
                if (in_bounds(nr, f) && b->squares[nr][f] == EMPTY) {
                    add_pawn_move(moves, &count, r, f, nr, f, color);

                    /* Double push from starting rank */
                    int nr2 = r + 2 * dir;
                    if (r == start_rank && b->squares[nr2][f] == EMPTY)
                        add_move(moves, &count, r, f, nr2, f, 0);
                }

                /* Diagonal captures (normal + en-passant) */
                for (int df = -1; df <= 1; df += 2) {
                    int nf = f + df;
                    if (!in_bounds(nr, nf)) continue;
                    if (board_color(b->squares[nr][nf]) == opp)
                        add_pawn_move(moves, &count, r, f, nr, nf, color);
                    else if (b->ep_rank == nr && b->ep_file == nf)
                        add_move(moves, &count, r, f, nr, nf, 0);
                }
                break;
            }

            /* ---- Knight ---- */
            case KNIGHT: {
                static const int kn[8][2] = {
                    {-2,-1},{-2,1},{-1,-2},{-1,2},{1,-2},{1,2},{2,-1},{2,1}
                };
                for (int i = 0; i < 8; i++) {
                    int nr = r + kn[i][0], nf = f + kn[i][1];
                    if (in_bounds(nr, nf) && board_color(b->squares[nr][nf]) != color)
                        add_move(moves, &count, r, f, nr, nf, 0);
                }
                break;
            }

            /* ---- Bishop / Rook / Queen (sliders) ---- */
            case BISHOP:
            case ROOK:
            case QUEEN: {
                int d_start = (type == ROOK)   ? 4 : 0;
                int d_end   = (type == BISHOP)  ? 4 : 8;
                for (int d = d_start; d < d_end; d++) {
                    int nr = r + dirs[d][0], nf = f + dirs[d][1];
                    while (in_bounds(nr, nf)) {
                        int target = b->squares[nr][nf];
                        if (target == EMPTY) {
                            add_move(moves, &count, r, f, nr, nf, 0);
                        } else {
                            if (board_color(target) == opp)
                                add_move(moves, &count, r, f, nr, nf, 0);
                            break; /* blocked */
                        }
                        nr += dirs[d][0]; nf += dirs[d][1];
                    }
                }
                break;
            }

            /* ---- King ---- */
            case KING: {
                /* Normal one-square moves */
                for (int dr = -1; dr <= 1; dr++) {
                    for (int df = -1; df <= 1; df++) {
                        if (dr == 0 && df == 0) continue;
                        int nr = r + dr, nf = f + df;
                        if (in_bounds(nr, nf) &&
                            board_color(b->squares[nr][nf]) != color)
                            add_move(moves, &count, r, f, nr, nf, 0);
                    }
                }

                /* Castling — only if king is on its home square and not in check */
                int back = (color == WHITE) ? 0 : 7;
                if (r == back && f == 4 && !is_in_check(b, color)) {

                    /* Kingside */
                    int ck = (color == WHITE) ? b->white_castle_k : b->black_castle_k;
                    if (ck &&
                        b->squares[back][5] == EMPTY &&
                        b->squares[back][6] == EMPTY &&
                        !is_attacked(b, back, 5, opp) &&
                        !is_attacked(b, back, 6, opp))
                        add_move(moves, &count, r, f, back, 6, 0);

                    /* Queenside */
                    int cq = (color == WHITE) ? b->white_castle_q : b->black_castle_q;
                    if (cq &&
                        b->squares[back][3] == EMPTY &&
                        b->squares[back][2] == EMPTY &&
                        b->squares[back][1] == EMPTY &&
                        !is_attacked(b, back, 3, opp) &&
                        !is_attacked(b, back, 2, opp))
                        add_move(moves, &count, r, f, back, 2, 0);
                }
                break;
            }

            } /* switch */
        }
    }

    return count;
}

/* ------------------------------------------------------------------ */
/*  Apply a move                                                        */
/* ------------------------------------------------------------------ */

void apply_move(Board *b, const Move *m) {
    int fr = m->from_rank, ff = m->from_file;
    int tr = m->to_rank,   tf = m->to_file;

    int piece    = b->squares[fr][ff];
    int type     = board_type(piece);
    int color    = board_color(piece);
    int captured = b->squares[tr][tf]; /* save before overwriting */

    /* Snapshot en-passant target then clear it */
    int prev_ep_rank = b->ep_rank;
    int prev_ep_file = b->ep_file;
    b->ep_rank = -1;
    b->ep_file = -1;

    /* En-passant capture — remove the captured pawn laterally */
    if (type == PAWN && tf == prev_ep_file && tr == prev_ep_rank)
        b->squares[fr][tf] = EMPTY;

    /* Double pawn push — set new en-passant target */
    if (type == PAWN && abs(tr - fr) == 2) {
        b->ep_rank = (fr + tr) / 2;
        b->ep_file = ff;
    }

    /* Castling — move the rook and revoke rights */
    if (type == KING) {
        int back = (color == WHITE) ? 0 : 7;
        if (ff == 4 && tf == 6) { /* kingside  */
            b->squares[back][5] = b->squares[back][7];
            b->squares[back][7] = EMPTY;
        } else if (ff == 4 && tf == 2) { /* queenside */
            b->squares[back][3] = b->squares[back][0];
            b->squares[back][0] = EMPTY;
        }
        if (color == WHITE) { b->white_castle_k = 0; b->white_castle_q = 0; }
        else                { b->black_castle_k = 0; b->black_castle_q = 0; }
    }

    /* Rook move — revoke that side's castling right */
    if (type == ROOK) {
        if (color == WHITE) {
            if (ff == 0) b->white_castle_q = 0;
            if (ff == 7) b->white_castle_k = 0;
        } else {
            if (ff == 0) b->black_castle_q = 0;
            if (ff == 7) b->black_castle_k = 0;
        }
    }

    /* If a rook is captured on its home square, revoke castling right */
    if (tr == 0 && tf == 0) b->white_castle_q = 0;
    if (tr == 0 && tf == 7) b->white_castle_k = 0;
    if (tr == 7 && tf == 0) b->black_castle_q = 0;
    if (tr == 7 && tf == 7) b->black_castle_k = 0;

    /* Move the piece */
    b->squares[tr][tf] = piece;
    b->squares[fr][ff] = EMPTY;

    /* Promotion */
    if (m->promotion != 0)
        b->squares[tr][tf] = color * m->promotion;

    /* Halfmove clock */
    if (type == PAWN || captured != EMPTY)
        b->halfmove_clock = 0;
    else
        b->halfmove_clock++;

    if (color == BLACK) b->fullmove_number++;

    b->turn = -color;
}

/* ------------------------------------------------------------------ */
/*  Legal move generation (filters pseudo-moves that leave king in check) */
/* ------------------------------------------------------------------ */

int generate_legal_moves(Board *b, Move *moves) {
    Move pseudo[MAX_MOVES];
    int  n     = generate_pseudo_moves(b, pseudo);
    int  count = 0;

    for (int i = 0; i < n; i++) {
        Board tmp;
        copy_board(&tmp, b);
        apply_move(&tmp, &pseudo[i]);
        if (!is_in_check(&tmp, b->turn))   /* king must not be in check after move */
            moves[count++] = pseudo[i];
    }

    return count;
}