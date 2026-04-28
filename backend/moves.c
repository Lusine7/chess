#include "moves.h"
#include <stdlib.h>

static inline int on_board(int sq) { return sq >= 0 && sq < 64; }

/* ------------------------------------------------------------------ */
/*  Attack detection                                                   */
/* ------------------------------------------------------------------ */

int is_square_attacked(Board *b, int sq, int by_color) {
    /* --- Pawn attacks --- */
    if (by_color == 1) {
        /* White pawns attack diagonally upward (decreasing index).
           A white pawn at sq+7 attacks sq (if no file-wrap).
           A white pawn at sq+9 attacks sq (if no file-wrap).        */
        if (sq % 8 != 0 && sq + 7 < 64 && b->squares[sq + 7] ==  PAWN) return 1;
        if (sq % 8 != 7 && sq + 9 < 64 && b->squares[sq + 9] ==  PAWN) return 1;
    } else {
        /* Black pawns attack diagonally downward (increasing index). */
        if (sq % 8 != 7 && sq - 7 >= 0 && b->squares[sq - 7] == -PAWN) return 1;
        if (sq % 8 != 0 && sq - 9 >= 0 && b->squares[sq - 9] == -PAWN) return 1;
    }

    /* --- Knight attacks --- */
    static const int kdx[8] = {-2,-2,-1,-1, 1, 1, 2, 2};
    static const int kdy[8] = {-1, 1,-2, 2,-2, 2,-1, 1};
    int f = sq % 8, r = sq / 8;
    for (int i = 0; i < 8; i++) {
        int nf = f + kdx[i], nr = r + kdy[i];
        if (nf < 0 || nf > 7 || nr < 0 || nr > 7) continue;
        if (b->squares[nr * 8 + nf] == by_color * KNIGHT) return 1;
    }

    /* --- Sliding pieces --- */
    /* Rook / Queen straight rays */
    static const int straight[4] = {-8, 8, -1, 1};
    for (int d = 0; d < 4; d++) {
        int dir = straight[d];
        int cur = sq;
        while (1) {
            int nxt = cur + dir;
            if (!on_board(nxt)) break;
            if (abs(nxt % 8 - cur % 8) > 1) break; /* file wrap */
            int p = b->squares[nxt];
            if (p != EMPTY) {
                if (p == by_color * ROOK || p == by_color * QUEEN) return 1;
                break;
            }
            cur = nxt;
        }
    }
    /* Bishop / Queen diagonal rays */
    static const int diag[4] = {-9, -7, 7, 9};
    for (int d = 0; d < 4; d++) {
        int dir = diag[d];
        int cur = sq;
        while (1) {
            int nxt = cur + dir;
            if (!on_board(nxt)) break;
            if (abs(nxt % 8 - cur % 8) != 1) break; /* file wrap */
            int p = b->squares[nxt];
            if (p != EMPTY) {
                if (p == by_color * BISHOP || p == by_color * QUEEN) return 1;
                break;
            }
            cur = nxt;
        }
    }

    /* --- King attacks --- */
    static const int kdirs[8] = {-9,-8,-7,-1,1,7,8,9};
    for (int i = 0; i < 8; i++) {
        int nxt = sq + kdirs[i];
        if (!on_board(nxt)) continue;
        if (abs(nxt % 8 - sq % 8) > 1) continue;
        if (b->squares[nxt] == by_color * KING) return 1;
    }

    return 0;
}

int is_in_check(Board *b, int color) {
    /* Find king */
    for (int i = 0; i < 64; i++) {
        if (b->squares[i] == color * KING) {
            return is_square_attacked(b, i, -color);
        }
    }
    return 0; /* should never happen */
}

/* ------------------------------------------------------------------ */
/*  Move generation helpers                                            */
/* ------------------------------------------------------------------ */

static int add_move(Move *out, int n, int from, int to, int flags, int promo) {
    out[n].from      = from;
    out[n].to        = to;
    out[n].flags     = flags;
    out[n].promotion = promo;
    return n + 1;
}

static int gen_pawn(Board *b, int sq, Move *out, int n) {
    int color = b->squares[sq] > 0 ? 1 : -1;
    int dir   = color == 1 ? -8 : 8;

    /* Promotion rank range */
    int promo_row = color == 1 ? 0 : 7; /* destination row (sq/8) triggers promo */

    /* Single push */
    int to = sq + dir;
    if (on_board(to) && b->squares[to] == EMPTY) {
        if (to / 8 == promo_row) {
            n = add_move(out, n, sq, to, FLAG_PROMOTION, QUEEN);
            n = add_move(out, n, sq, to, FLAG_PROMOTION, ROOK);
            n = add_move(out, n, sq, to, FLAG_PROMOTION, BISHOP);
            n = add_move(out, n, sq, to, FLAG_PROMOTION, KNIGHT);
        } else {
            n = add_move(out, n, sq, to, 0, 0);
        }
        /* Double push from starting rank */
        int start_min = color == 1 ? 48 : 8;
        int start_max = color == 1 ? 55 : 15;
        if (sq >= start_min && sq <= start_max) {
            int to2 = sq + 2 * dir;
            if (on_board(to2) && b->squares[to2] == EMPTY)
                n = add_move(out, n, sq, to2, 0, 0);
        }
    }

    /* Captures (left and right) */
    int cap_offsets[2] = {dir - 1, dir + 1};
    int file_check[2]  = {sq % 8 > 0, sq % 8 < 7}; /* left/right valid? */

    for (int i = 0; i < 2; i++) {
        if (!file_check[i]) continue;
        int cto = sq + cap_offsets[i];
        if (!on_board(cto)) continue;

        int target = b->squares[cto];
        int is_enemy = (target != EMPTY) && ((target > 0) != (color > 0));
        int is_ep    = (cto == b->en_passant);

        if (is_enemy) {
            if (cto / 8 == promo_row) {
                n = add_move(out, n, sq, cto, FLAG_PROMOTION, QUEEN);
                n = add_move(out, n, sq, cto, FLAG_PROMOTION, ROOK);
                n = add_move(out, n, sq, cto, FLAG_PROMOTION, BISHOP);
                n = add_move(out, n, sq, cto, FLAG_PROMOTION, KNIGHT);
            } else {
                n = add_move(out, n, sq, cto, 0, 0);
            }
        } else if (is_ep) {
            n = add_move(out, n, sq, cto, FLAG_EN_PASSANT, 0);
        }
    }
    return n;
}

static int gen_knight(Board *b, int sq, Move *out, int n) {
    static const int dx[8] = {-2,-2,-1,-1, 1, 1, 2, 2};
    static const int dy[8] = {-1, 1,-2, 2,-2, 2,-1, 1};
    int color = b->squares[sq] > 0 ? 1 : -1;
    int f = sq % 8, r = sq / 8;
    for (int i = 0; i < 8; i++) {
        int nf = f + dx[i], nr = r + dy[i];
        if (nf < 0 || nf > 7 || nr < 0 || nr > 7) continue;
        int to = nr * 8 + nf;
        int t = b->squares[to];
        if (t == EMPTY || (t > 0) != (color > 0))
            n = add_move(out, n, sq, to, 0, 0);
    }
    return n;
}

static int gen_sliding(Board *b, int sq, const int *dirs, int ndirs, Move *out, int n) {
    int color = b->squares[sq] > 0 ? 1 : -1;
    for (int d = 0; d < ndirs; d++) {
        int dir = dirs[d];
        int cur = sq;
        while (1) {
            int nxt = cur + dir;
            if (!on_board(nxt)) break;
            if (abs(nxt % 8 - cur % 8) > 1) break; /* wrap guard */
            int t = b->squares[nxt];
            if (t == EMPTY) {
                n = add_move(out, n, sq, nxt, 0, 0);
            } else {
                if ((t > 0) != (color > 0))
                    n = add_move(out, n, sq, nxt, 0, 0);
                break;
            }
            cur = nxt;
        }
    }
    return n;
}

static int gen_king(Board *b, int sq, Move *out, int n) {
    int color = b->squares[sq] > 0 ? 1 : -1;
    static const int dirs[8] = {-9,-8,-7,-1,1,7,8,9};
    for (int i = 0; i < 8; i++) {
        int to = sq + dirs[i];
        if (!on_board(to)) continue;
        if (abs(to % 8 - sq % 8) > 1) continue;
        int t = b->squares[to];
        if (t == EMPTY || (t > 0) != (color > 0))
            n = add_move(out, n, sq, to, 0, 0);
    }

    /* Castling */
    int enemy = -color;
    if (color == 1) { /* White */
        if ((b->castling & CASTLE_WK) &&
            b->squares[61] == EMPTY && b->squares[62] == EMPTY &&
            !is_square_attacked(b, 60, enemy) &&
            !is_square_attacked(b, 61, enemy) &&
            !is_square_attacked(b, 62, enemy))
            n = add_move(out, n, 60, 62, FLAG_CASTLING, 0);

        if ((b->castling & CASTLE_WQ) &&
            b->squares[59] == EMPTY && b->squares[58] == EMPTY && b->squares[57] == EMPTY &&
            !is_square_attacked(b, 60, enemy) &&
            !is_square_attacked(b, 59, enemy) &&
            !is_square_attacked(b, 58, enemy))
            n = add_move(out, n, 60, 58, FLAG_CASTLING, 0);
    } else { /* Black */
        if ((b->castling & CASTLE_BK) &&
            b->squares[5] == EMPTY && b->squares[6] == EMPTY &&
            !is_square_attacked(b, 4, enemy) &&
            !is_square_attacked(b, 5, enemy) &&
            !is_square_attacked(b, 6, enemy))
            n = add_move(out, n, 4, 6, FLAG_CASTLING, 0);

        if ((b->castling & CASTLE_BQ) &&
            b->squares[3] == EMPTY && b->squares[2] == EMPTY && b->squares[1] == EMPTY &&
            !is_square_attacked(b, 4, enemy) &&
            !is_square_attacked(b, 3, enemy) &&
            !is_square_attacked(b, 2, enemy))
            n = add_move(out, n, 4, 2, FLAG_CASTLING, 0);
    }
    return n;
}

/* ------------------------------------------------------------------ */
/*  Public: generate all pseudo-legal moves for current side          */
/* ------------------------------------------------------------------ */

int generate_moves(Board *b, Move *out) {
    static const int straight[4] = {-8, 8, -1,  1};
    static const int diagonal[4] = {-9,-7,  7,  9};
    static const int alldir [8]  = {-9,-8, -7, -1, 1, 7, 8, 9};

    int n = 0;
    for (int sq = 0; sq < 64; sq++) {
        int p = b->squares[sq];
        if (p == EMPTY) continue;
        int color = p > 0 ? 1 : -1;
        if (color != b->turn) continue;

        int ap = p < 0 ? -p : p;
        switch (ap) {
            case PAWN:   n = gen_pawn   (b, sq, out, n); break;
            case KNIGHT: n = gen_knight (b, sq, out, n); break;
            case BISHOP: n = gen_sliding(b, sq, diagonal, 4, out, n); break;
            case ROOK:   n = gen_sliding(b, sq, straight, 4, out, n); break;
            case QUEEN:  n = gen_sliding(b, sq, alldir,   8, out, n); break;
            case KING:   n = gen_king   (b, sq, out, n); break;
        }
    }
    return n;
}

/* ------------------------------------------------------------------ */
/*  Public: filter to legal moves only (king not in check after move) */
/* ------------------------------------------------------------------ */

int generate_legal_moves(Board *b, Move *out) {
    Move pseudo[256];
    int  count = generate_moves(b, pseudo);
    int  legal = 0;
    for (int i = 0; i < count; i++) {
        UndoInfo u;
        board_apply_move(b, pseudo[i], &u);
        if (!is_in_check(b, -b->turn)) /* turn already flipped */
            out[legal++] = pseudo[i];
        board_undo_move(b, pseudo[i], &u);
    }
    return legal;
}
