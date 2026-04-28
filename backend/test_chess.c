/*
 * test_chess.c — Unit tests for the chess engine.
 *
 * Build and run:
 *   make test
 *
 * No external framework — a tiny macro harness is defined below.
 * Each TEST() function is registered in main() and run in order.
 * The suite prints a summary and exits with 0 (all pass) or 1 (any fail).
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "board.h"
#include "moves.h"
#include "eval.h"
#include "ai.h"

/* ================================================================== */
/*  Minimal test harness                                               */
/* ================================================================== */

static int _total  = 0;
static int _passed = 0;
static int _failed = 0;
static const char *_current_suite = "";

#define SUITE(name)  do { _current_suite = (name); \
                          printf("\n── %s\n", _current_suite); } while(0)

#define CHECK(expr) do {                                              \
    _total++;                                                         \
    if (expr) {                                                       \
        _passed++;                                                    \
        printf("  ✓  %s\n", #expr);                                  \
    } else {                                                          \
        _failed++;                                                    \
        printf("  ✗  %s  ← FAILED (%s:%d)\n", #expr, __FILE__, __LINE__); \
    }                                                                 \
} while(0)

#define CHECK_EQ(a,b) do {                                            \
    _total++;                                                         \
    int _a = (int)(a), _b = (int)(b);                                \
    if (_a == _b) {                                                   \
        _passed++;                                                    \
        printf("  ✓  %s == %d\n", #a, _b);                          \
    } else {                                                          \
        _failed++;                                                    \
        printf("  ✗  %s: expected %d, got %d  (%s:%d)\n",           \
               #a, _b, _a, __FILE__, __LINE__);                      \
    }                                                                 \
} while(0)

/* ================================================================== */
/*  Helpers                                                            */
/* ================================================================== */

/* Count legal moves for one specific piece on the board. */
static int legal_moves_from(Board *b, int rank, int file) {
    Move moves[MAX_MOVES];
    int  n = generate_legal_moves(b, moves);
    int  c = 0;
    for (int i = 0; i < n; i++)
        if (moves[i].from_rank == rank && moves[i].from_file == file)
            c++;
    return c;
}

/* Return 1 if the given destination exists among legal moves from sq. */
static int has_legal_move(Board *b, int fr, int ff, int tr, int tf) {
    Move moves[MAX_MOVES];
    int  n = generate_legal_moves(b, moves);
    for (int i = 0; i < n; i++)
        if (moves[i].from_rank == fr && moves[i].from_file == ff &&
            moves[i].to_rank   == tr && moves[i].to_file   == tf)
            return 1;
    return 0;
}

/* Clear the board (keep metadata intact). */
static void clear_pieces(Board *b) {
    memset(b->squares, 0, sizeof(b->squares));
}

/* Place a piece and return pointer to its square for convenience. */
static void place(Board *b, int rank, int file, int piece) {
    b->squares[rank][file] = piece;
}

/* ================================================================== */
/*  board.c tests                                                      */
/* ================================================================== */

static void test_board_init_piece_positions(void) {
    SUITE("board_init — piece positions");
    Board b;
    board_init(&b);

    /* White back rank */
    CHECK_EQ(b.squares[0][0],  ROOK);
    CHECK_EQ(b.squares[0][1],  KNIGHT);
    CHECK_EQ(b.squares[0][2],  BISHOP);
    CHECK_EQ(b.squares[0][3],  QUEEN);
    CHECK_EQ(b.squares[0][4],  KING);
    CHECK_EQ(b.squares[0][5],  BISHOP);
    CHECK_EQ(b.squares[0][6],  KNIGHT);
    CHECK_EQ(b.squares[0][7],  ROOK);

    /* Black back rank */
    CHECK_EQ(b.squares[7][0], -ROOK);
    CHECK_EQ(b.squares[7][3], -QUEEN);
    CHECK_EQ(b.squares[7][4], -KING);

    /* Pawns */
    for (int f = 0; f < 8; f++) {
        CHECK(b.squares[1][f] == PAWN);
        CHECK(b.squares[6][f] == -PAWN);
    }

    /* Empty middle ranks */
    for (int r = 2; r <= 5; r++)
        for (int f = 0; f < 8; f++)
            CHECK(b.squares[r][f] == EMPTY);
}

static void test_board_init_metadata(void) {
    SUITE("board_init — metadata");
    Board b;
    board_init(&b);

    CHECK_EQ(b.turn,            WHITE);
    CHECK_EQ(b.white_castle_k,  1);
    CHECK_EQ(b.white_castle_q,  1);
    CHECK_EQ(b.black_castle_k,  1);
    CHECK_EQ(b.black_castle_q,  1);
    CHECK_EQ(b.ep_rank,        -1);
    CHECK_EQ(b.ep_file,        -1);
    CHECK_EQ(b.halfmove_clock,  0);
    CHECK_EQ(b.fullmove_number, 1);
}

static void test_copy_board(void) {
    SUITE("copy_board — independence");
    Board src, dst;
    board_init(&src);
    copy_board(&dst, &src);

    /* Mutating dst must not affect src */
    dst.squares[3][3] = QUEEN;
    CHECK(src.squares[3][3] == EMPTY);

    dst.turn = BLACK;
    CHECK_EQ(src.turn, WHITE);
}

static void test_sq_str_roundtrip(void) {
    SUITE("sq_to_str / str_to_rank / str_to_file — round-trip");
    for (int r = 0; r < 8; r++) {
        for (int f = 0; f < 8; f++) {
            char buf[3];
            sq_to_str(r, f, buf);
            CHECK(str_to_rank(buf) == r);
            CHECK(str_to_file(buf) == f);
        }
    }
}

static void test_board_color_and_type(void) {
    SUITE("board_color / board_type");
    CHECK_EQ(board_color( QUEEN), WHITE);
    CHECK_EQ(board_color(-QUEEN), BLACK);
    CHECK_EQ(board_color( EMPTY), 0);
    CHECK_EQ(board_type(  QUEEN), QUEEN);
    CHECK_EQ(board_type( -QUEEN), QUEEN);
    CHECK_EQ(board_type(  PAWN),  PAWN);
    CHECK_EQ(board_type( -PAWN),  PAWN);
}

/* ================================================================== */
/*  moves.c — is_attacked                                              */
/* ================================================================== */

static void test_pawn_attacks(void) {
    SUITE("is_attacked — pawns");
    Board b;
    board_init(&b);
    clear_pieces(&b);

    /* White pawn on e4 (rank 3, file 4) attacks d5 and f5 */
    place(&b, 3, 4, PAWN);
    CHECK(is_attacked(&b, 4, 3, WHITE));   /* d5 attacked */
    CHECK(is_attacked(&b, 4, 5, WHITE));   /* f5 attacked */
    CHECK(!is_attacked(&b, 4, 4, WHITE));  /* e5 not attacked by pawn */
    CHECK(!is_attacked(&b, 3, 4, WHITE));  /* own square not attacked */

    /* Black pawn on e5 (rank 4, file 4) attacks d4 and f4 */
    clear_pieces(&b);
    place(&b, 4, 4, -PAWN);
    CHECK(is_attacked(&b, 3, 3, BLACK));
    CHECK(is_attacked(&b, 3, 5, BLACK));
    CHECK(!is_attacked(&b, 3, 4, BLACK));
}

static void test_knight_attacks(void) {
    SUITE("is_attacked — knights");
    Board b;
    board_init(&b);
    clear_pieces(&b);

    /* White knight on d4 (rank 3, file 3) */
    place(&b, 3, 3, KNIGHT);
    /* All 8 knight jumps */
    CHECK(is_attacked(&b, 5, 4, WHITE));  /* +2,+1 */
    CHECK(is_attacked(&b, 5, 2, WHITE));  /* +2,-1 */
    CHECK(is_attacked(&b, 1, 4, WHITE));  /* -2,+1 */
    CHECK(is_attacked(&b, 1, 2, WHITE));  /* -2,-1 */
    CHECK(is_attacked(&b, 4, 5, WHITE));  /* +1,+2 */
    CHECK(is_attacked(&b, 4, 1, WHITE));  /* +1,-2 */
    CHECK(is_attacked(&b, 2, 5, WHITE));  /* -1,+2 */
    CHECK(is_attacked(&b, 2, 1, WHITE));  /* -1,-2 */
    /* Non-attacked squares */
    CHECK(!is_attacked(&b, 3, 4, WHITE));
    CHECK(!is_attacked(&b, 5, 3, WHITE));
}

static void test_bishop_attacks(void) {
    SUITE("is_attacked — bishops");
    Board b;
    board_init(&b);
    clear_pieces(&b);

    /* White bishop on c1 (rank 0, file 2) */
    place(&b, 0, 2, BISHOP);
    CHECK(is_attacked(&b, 1, 3, WHITE));   /* diagonal d2 */
    CHECK(is_attacked(&b, 4, 6, WHITE));   /* diagonal g5 */
    CHECK(!is_attacked(&b, 0, 3, WHITE));  /* same rank, not diagonal */

    /* Blocker cuts off the diagonal */
    /* Use ROOK (not PAWN) so the blocker itself doesn't attack (3,5) */
    place(&b, 2, 4, ROOK);                 /* blocker on e3 */
    CHECK(is_attacked(&b, 2, 4, WHITE));   /* can still see the blocker */
    CHECK(!is_attacked(&b, 3, 5, WHITE));  /* blocked beyond it */
}

static void test_rook_attacks(void) {
    SUITE("is_attacked — rooks");
    Board b;
    board_init(&b);
    clear_pieces(&b);

    /* White rook on a1 (rank 0, file 0) */
    place(&b, 0, 0, ROOK);
    CHECK(is_attacked(&b, 0, 7, WHITE));  /* same rank, far end */
    CHECK(is_attacked(&b, 7, 0, WHITE));  /* same file, far end */
    CHECK(!is_attacked(&b, 1, 1, WHITE)); /* diagonal — not attacked */

    /* Blocker on a4 (rank 3, file 0) */
    place(&b, 3, 0, PAWN);
    CHECK(is_attacked(&b, 3, 0, WHITE));  /* sees the blocker */
    CHECK(!is_attacked(&b, 7, 0, WHITE)); /* blocked beyond */
}

static void test_queen_attacks(void) {
    SUITE("is_attacked — queen (combines rook + bishop)");
    Board b;
    board_init(&b);
    clear_pieces(&b);

    /* Queen on d4 (rank 3, file 3) */
    place(&b, 3, 3, QUEEN);
    CHECK(is_attacked(&b, 3, 7, WHITE)); /* same rank */
    CHECK(is_attacked(&b, 7, 3, WHITE)); /* same file */
    CHECK(is_attacked(&b, 6, 6, WHITE)); /* diagonal */
    CHECK(is_attacked(&b, 0, 0, WHITE)); /* anti-diagonal */
    CHECK(!is_attacked(&b, 5, 4, WHITE));/* knight-jump — not attacked */
}

static void test_king_attacks(void) {
    SUITE("is_attacked — king");
    Board b;
    board_init(&b);
    clear_pieces(&b);

    /* White king on e4 (rank 3, file 4) */
    place(&b, 3, 4, KING);
    for (int dr = -1; dr <= 1; dr++)
        for (int df = -1; df <= 1; df++) {
            if (dr == 0 && df == 0) continue;
            CHECK(is_attacked(&b, 3+dr, 4+df, WHITE));
        }
    CHECK(!is_attacked(&b, 3, 6, WHITE)); /* two files away */
    CHECK(!is_attacked(&b, 5, 4, WHITE)); /* two ranks away */
}

/* ================================================================== */
/*  moves.c — legal move counts                                        */
/* ================================================================== */

static void test_starting_position_move_count(void) {
    SUITE("generate_legal_moves — starting position");
    Board b;
    board_init(&b);

    Move moves[MAX_MOVES];
    int n = generate_legal_moves(&b, moves);
    CHECK_EQ(n, 20); /* 16 pawn + 4 knight moves */
}

static void test_pawn_starting_double_push(void) {
    SUITE("pawn — double push from starting rank");
    Board b;
    board_init(&b);
    clear_pieces(&b);
    b.turn = WHITE;

    place(&b, 1, 4, PAWN);   /* white pawn on e2 */
    place(&b, 0, 4, KING);   /* kings required to avoid crashes in legality */
    place(&b, 7, 4, -KING);

    int n = legal_moves_from(&b, 1, 4);
    CHECK_EQ(n, 2); /* e3 and e4 */
    CHECK(has_legal_move(&b, 1, 4, 2, 4)); /* e3 */
    CHECK(has_legal_move(&b, 1, 4, 3, 4)); /* e4 */
}

static void test_pawn_blocked_no_double_push(void) {
    SUITE("pawn — blocker prevents double push");
    Board b;
    board_init(&b);
    clear_pieces(&b);
    b.turn = WHITE;

    place(&b, 1, 4, PAWN);
    place(&b, 2, 4, -PAWN);  /* blocker on e3 */
    place(&b, 0, 4, KING);
    place(&b, 7, 4, -KING);

    int n = legal_moves_from(&b, 1, 4);
    CHECK_EQ(n, 0);
}

static void test_pawn_capture(void) {
    SUITE("pawn — diagonal capture");
    Board b;
    board_init(&b);
    clear_pieces(&b);
    b.turn = WHITE;

    place(&b, 3, 3, PAWN);    /* white pawn on d4 */
    place(&b, 4, 4, -PAWN);   /* black pawn on e5 — capturable */
    place(&b, 0, 4, KING);
    place(&b, 7, 4, -KING);

    CHECK(has_legal_move(&b, 3, 3, 4, 4)); /* capture e5 */
    CHECK(has_legal_move(&b, 3, 3, 4, 3)); /* push to d5 */
    CHECK(!has_legal_move(&b, 3, 3, 4, 2)); /* no piece to capture there */
}

static void test_en_passant(void) {
    SUITE("pawn — en passant");
    Board b;
    board_init(&b);
    clear_pieces(&b);
    b.turn = WHITE;

    /* White pawn on e5, black pawn just double-pushed to d5 */
    place(&b, 4, 4, PAWN);    /* e5 */
    place(&b, 4, 3, -PAWN);   /* d5 (just landed) */
    place(&b, 0, 4, KING);
    place(&b, 7, 4, -KING);
    b.ep_rank = 5;             /* en-passant target: d6 */
    b.ep_file = 3;

    CHECK(has_legal_move(&b, 4, 4, 5, 3)); /* white captures en passant */

    /* After en passant, captured pawn must be removed */
    Move m = { 4, 4, 5, 3, 0 };
    apply_move(&b, &m);
    CHECK_EQ(b.squares[4][3], EMPTY);  /* d5 pawn removed */
    CHECK_EQ(b.squares[5][3], PAWN);   /* white pawn on d6 */
}

static void test_en_passant_expires(void) {
    SUITE("pawn — en passant not available after one move");
    Board b;
    board_init(&b);
    clear_pieces(&b);

    place(&b, 4, 4, PAWN);
    place(&b, 4, 3, -PAWN);
    place(&b, 0, 4, KING);
    place(&b, 7, 4, -KING);
    b.ep_rank = 5;
    b.ep_file = 3;
    b.turn    = WHITE;

    /* White makes a different move (pawn push) */
    Move other = { 4, 4, 5, 4, 0 };  /* e5→e6 */
    apply_move(&b, &other);

    /* Now it's black's turn — ep target must have been cleared */
    CHECK_EQ(b.ep_rank, -1);
    CHECK_EQ(b.ep_file, -1);
}

static void test_promotion_generates_four_moves(void) {
    SUITE("pawn — promotion generates 4 variants");
    Board b;
    board_init(&b);
    clear_pieces(&b);
    b.turn = WHITE;

    place(&b, 6, 4, PAWN);    /* white pawn on e7, one push from promotion */
    place(&b, 0, 4, KING);
    place(&b, 7, 0, -KING);  /* a8 — keep e8 clear so the pawn can promote */

    int n = legal_moves_from(&b, 6, 4);
    CHECK_EQ(n, 4);  /* Q, R, B, N */
}

static void test_promotion_applies_correctly(void) {
    SUITE("pawn — promotion sets correct piece on board");
    Board b;
    board_init(&b);
    clear_pieces(&b);
    b.turn = WHITE;

    place(&b, 6, 0, PAWN);    /* a7 */
    place(&b, 0, 4, KING);
    place(&b, 7, 4, -KING);

    Move m = { 6, 0, 7, 0, QUEEN };
    apply_move(&b, &m);
    CHECK_EQ(b.squares[7][0], QUEEN);  /* white queen on a8 */
    CHECK_EQ(b.squares[6][0], EMPTY);

    /* Black promotion */
    clear_pieces(&b);
    b.turn = BLACK;
    place(&b, 1, 0, -PAWN);   /* a2 */
    place(&b, 0, 4, KING);
    place(&b, 7, 4, -KING);
    Move m2 = { 1, 0, 0, 0, KNIGHT };
    apply_move(&b, &m2);
    CHECK_EQ(b.squares[0][0], -KNIGHT); /* black knight on a1 */
}

/* ================================================================== */
/*  moves.c — castling                                                  */
/* ================================================================== */

static void test_castling_kingside_white(void) {
    SUITE("castling — white kingside");
    Board b;
    board_init(&b);
    clear_pieces(&b);
    b.turn = WHITE;

    /* Only king and rook, path clear */
    place(&b, 0, 4, KING);
    place(&b, 0, 7, ROOK);
    place(&b, 7, 4, -KING);

    CHECK(has_legal_move(&b, 0, 4, 0, 6)); /* castle kingside */

    Move m = { 0, 4, 0, 6, 0 };
    apply_move(&b, &m);
    CHECK_EQ(b.squares[0][6], KING); /* king on g1 */
    CHECK_EQ(b.squares[0][5], ROOK); /* rook on f1 */
    CHECK_EQ(b.squares[0][7], EMPTY);
    CHECK_EQ(b.squares[0][4], EMPTY);
}

static void test_castling_queenside_white(void) {
    SUITE("castling — white queenside");
    Board b;
    board_init(&b);
    clear_pieces(&b);
    b.turn = WHITE;

    place(&b, 0, 4, KING);
    place(&b, 0, 0, ROOK);
    place(&b, 7, 4, -KING);

    CHECK(has_legal_move(&b, 0, 4, 0, 2));

    Move m = { 0, 4, 0, 2, 0 };
    apply_move(&b, &m);
    CHECK_EQ(b.squares[0][2], KING);  /* king on c1 */
    CHECK_EQ(b.squares[0][3], ROOK);  /* rook on d1 */
    CHECK_EQ(b.squares[0][0], EMPTY);
}

static void test_castling_blocked(void) {
    SUITE("castling — blocked by piece between king and rook");
    Board b;
    board_init(&b);
    clear_pieces(&b);
    b.turn = WHITE;

    place(&b, 0, 4, KING);
    place(&b, 0, 7, ROOK);
    place(&b, 0, 5, BISHOP);  /* blocks f1 */
    place(&b, 7, 4, -KING);

    CHECK(!has_legal_move(&b, 0, 4, 0, 6));
}

static void test_castling_through_check(void) {
    SUITE("castling — cannot castle through attacked square");
    Board b;
    board_init(&b);
    clear_pieces(&b);
    b.turn = WHITE;

    place(&b, 0, 4, KING);
    place(&b, 0, 7, ROOK);
    place(&b, 7, 4, -KING);
    place(&b, 5, 5, -ROOK);   /* black rook attacks f1 (0,5) */

    CHECK(!has_legal_move(&b, 0, 4, 0, 6));
}

static void test_castling_out_of_check(void) {
    SUITE("castling — cannot castle while in check");
    Board b;
    board_init(&b);
    clear_pieces(&b);
    b.turn = WHITE;

    place(&b, 0, 4, KING);
    place(&b, 0, 7, ROOK);
    place(&b, 7, 4, -KING);
    place(&b, 5, 4, -ROOK);   /* black rook puts king in check on e1 */

    CHECK(!has_legal_move(&b, 0, 4, 0, 6));
}

static void test_castling_rights_revoked_after_king_moves(void) {
    SUITE("castling — rights revoked after king moves");
    Board b;
    board_init(&b);
    clear_pieces(&b);
    b.turn = WHITE;

    place(&b, 0, 4, KING);
    place(&b, 0, 7, ROOK);
    place(&b, 0, 0, ROOK);
    place(&b, 7, 4, -KING);

    /* King steps to f1 and back to e1 */
    Move m1 = { 0, 4, 0, 5, 0 };
    apply_move(&b, &m1);
    b.turn = WHITE; /* skip black's turn for this test */
    Move m2 = { 0, 5, 0, 4, 0 };
    apply_move(&b, &m2);
    b.turn = WHITE;

    CHECK(!has_legal_move(&b, 0, 4, 0, 6)); /* no kingside castle */
    CHECK(!has_legal_move(&b, 0, 4, 0, 2)); /* no queenside castle */
}

static void test_castling_black(void) {
    SUITE("castling — black kingside");
    Board b;
    board_init(&b);
    clear_pieces(&b);
    b.turn            = BLACK;
    b.black_castle_k  = 1;
    b.black_castle_q  = 1;

    place(&b, 7, 4, -KING);
    place(&b, 7, 7, -ROOK);
    place(&b, 0, 4,  KING);

    CHECK(has_legal_move(&b, 7, 4, 7, 6));

    Move m = { 7, 4, 7, 6, 0 };
    apply_move(&b, &m);
    CHECK_EQ(b.squares[7][6], -KING);
    CHECK_EQ(b.squares[7][5], -ROOK);
}

/* ================================================================== */
/*  moves.c — check, checkmate, stalemate                              */
/* ================================================================== */

static void test_is_in_check(void) {
    SUITE("is_in_check");
    Board b;
    board_init(&b);
    clear_pieces(&b);

    /* White king attacked by black rook on same file */
    place(&b, 0, 4,  KING);
    place(&b, 7, 4, -KING);
    place(&b, 5, 4, -ROOK);

    CHECK(is_in_check(&b, WHITE));
    CHECK(!is_in_check(&b, BLACK));
}

static void test_checkmate_back_rank(void) {
    SUITE("generate_legal_moves — checkmate (back-rank)");
    Board b;
    board_init(&b);
    clear_pieces(&b);
    b.turn = WHITE;

    /* White king trapped on h1, two black rooks cover all escapes */
    place(&b, 0, 7,  KING);
    place(&b, 7, 0, -KING);
    place(&b, 1, 0, -ROOK);   /* covers rank 1 */
    place(&b, 0, 0, -ROOK);   /* covers rank 0 (except where king is) */

    Move moves[MAX_MOVES];
    int n = generate_legal_moves(&b, moves);
    CHECK_EQ(n, 0);
    CHECK(is_in_check(&b, WHITE));
}

static void test_stalemate(void) {
    SUITE("generate_legal_moves — stalemate");
    Board b;
    board_init(&b);
    clear_pieces(&b);
    b.turn = BLACK;

    /* Classic stalemate: black king in corner, white controls all moves */
    place(&b, 7, 7, -KING);
    place(&b, 5, 6,  QUEEN);
    place(&b, 5, 7,  KING);

    Move moves[MAX_MOVES];
    int n = generate_legal_moves(&b, moves);
    CHECK_EQ(n, 0);
    CHECK(!is_in_check(&b, BLACK));
}

static void test_pinned_piece_cannot_move(void) {
    SUITE("legal moves — pinned piece cannot expose king");
    Board b;
    board_init(&b);
    clear_pieces(&b);
    b.turn = WHITE;

    /* White king e1, white rook e4, black rook e8 — rook is pinned */
    place(&b, 0, 4, KING);
    place(&b, 3, 4, ROOK);   /* white rook on e4 — pinned to king */
    place(&b, 7, 4, -ROOK);  /* black rook on e8 pins it */
    place(&b, 6, 0, -KING);

    /* Pinned rook may only move along the pin ray (same file) */
    int n = legal_moves_from(&b, 3, 4);
    /* Allowed: e2, e3, e5, e6, e7, e8(capture) = 6 squares along e-file */
    /* Not allowed: any move off the e-file */
    CHECK(has_legal_move(&b, 3, 4, 1, 4));   /* e2 — along pin */
    CHECK(has_legal_move(&b, 3, 4, 7, 4));   /* capture e8 — along pin */
    CHECK(!has_legal_move(&b, 3, 4, 3, 0));  /* a4 — breaks pin */
    CHECK(!has_legal_move(&b, 3, 4, 3, 7));  /* h4 — breaks pin */
    (void)n;
}

/* ================================================================== */
/*  moves.c — apply_move side effects                                  */
/* ================================================================== */

static void test_apply_move_halfmove_clock(void) {
    SUITE("apply_move — halfmove clock");
    Board b;
    board_init(&b);
    clear_pieces(&b);
    b.turn = WHITE;

    place(&b, 0, 4, KING);
    place(&b, 0, 0, ROOK);
    place(&b, 7, 4, -KING);

    /* Rook move (quiet) increments clock */
    Move m = { 0, 0, 0, 1, 0 };
    apply_move(&b, &m);
    CHECK_EQ(b.halfmove_clock, 1);

    /* Pawn move resets it */
    b.turn = WHITE;
    place(&b, 1, 0, PAWN);
    Move m2 = { 1, 0, 2, 0, 0 };
    apply_move(&b, &m2);
    CHECK_EQ(b.halfmove_clock, 0);
}

static void test_apply_move_fullmove_counter(void) {
    SUITE("apply_move — fullmove counter increments after black's move");
    Board b;
    board_init(&b);
    clear_pieces(&b);

    place(&b, 0, 4,  KING);
    place(&b, 7, 4, -KING);
    place(&b, 6, 0, -PAWN);

    CHECK_EQ(b.fullmove_number, 1);

    /* White move — counter stays */
    b.turn = WHITE;
    Move m1 = { 0, 4, 0, 3, 0 };
    apply_move(&b, &m1);
    CHECK_EQ(b.fullmove_number, 1);

    /* Black move — counter increments */
    Move m2 = { 6, 0, 5, 0, 0 };
    apply_move(&b, &m2);
    CHECK_EQ(b.fullmove_number, 2);
}

static void test_apply_move_turn_flips(void) {
    SUITE("apply_move — turn alternates");
    Board b;
    board_init(&b);
    clear_pieces(&b);
    b.turn = WHITE;

    place(&b, 0, 4,  KING);
    place(&b, 7, 4, -KING);

    Move m = { 0, 4, 0, 3, 0 };
    apply_move(&b, &m);
    CHECK_EQ(b.turn, BLACK);
    apply_move(&b, (Move[]){ {7, 4, 7, 3, 0} });
    CHECK_EQ(b.turn, WHITE);
}

/* ================================================================== */
/*  eval.c tests                                                       */
/* ================================================================== */

static void test_eval_starting_position_symmetric(void) {
    SUITE("evaluate — starting position is 0");
    Board b;
    board_init(&b);
    int score = evaluate(&b);
    CHECK_EQ(score, 0);
}

static void test_eval_material_advantage(void) {
    SUITE("evaluate — removing a piece shifts score");
    Board b;
    board_init(&b);

    /* Remove black queen → white advantage */
    b.squares[7][3] = EMPTY;
    int score = evaluate(&b);
    CHECK(score > 0);

    /* Remove white queen too → back to roughly balanced */
    b.squares[0][3] = EMPTY;
    int score2 = evaluate(&b);
    /* Should be close to 0 (small PST asymmetry possible) */
    CHECK(score2 > -50 && score2 < 50);
}

static void test_eval_extra_queen_large_advantage(void) {
    SUITE("evaluate — extra queen is a large material advantage");
    Board b;
    board_init(&b);
    clear_pieces(&b);

    place(&b, 0, 4, KING);
    place(&b, 7, 4, -KING);
    place(&b, 3, 3, QUEEN);   /* extra white queen */

    int score = evaluate(&b);
    CHECK(score > 800);  /* queen = ~900 cp; PST may adjust slightly */
}

static void test_eval_pst_center_pawn_better(void) {
    SUITE("evaluate — central pawn scores higher than edge pawn (PST)");
    Board b;
    board_init(&b);
    clear_pieces(&b);

    /* White pawn on e4 (rank 3, file 4) vs a2 (rank 1, file 0) */
    place(&b, 0, 4, KING);
    place(&b, 7, 4, -KING);

    place(&b, 3, 4, PAWN);    /* e4 */
    int score_center = evaluate(&b);

    b.squares[3][4] = EMPTY;
    place(&b, 1, 0, PAWN);    /* a2 */
    int score_edge = evaluate(&b);

    CHECK(score_center > score_edge);
}

/* ================================================================== */
/*  ai.c tests                                                         */
/* ================================================================== */

static void test_ai_no_moves_returns_zero(void) {
    SUITE("find_best_move — returns 0 in checkmate position");
    Board b;
    board_init(&b);
    clear_pieces(&b);
    b.turn = WHITE;

    /* White is in checkmate */
    place(&b, 0, 7,  KING);
    place(&b, 7, 0, -KING);
    place(&b, 1, 0, -ROOK);
    place(&b, 0, 0, -ROOK);

    Move best;
    int ok = find_best_move(&b, &best);
    CHECK_EQ(ok, 0);
}

static void test_ai_takes_free_piece(void) {
    SUITE("find_best_move — captures an undefended piece at depth 1");
    Board b;
    board_init(&b);
    clear_pieces(&b);
    b.turn    = WHITE;
    ai_depth  = 1;

    /* White rook can capture an undefended black queen */
    place(&b, 0, 4, KING);
    place(&b, 7, 4, -KING);
    place(&b, 3, 0, ROOK);     /* white rook on a4 */
    place(&b, 3, 7, -QUEEN);   /* black queen on h4 — free */

    Move best;
    int ok = find_best_move(&b, &best);
    CHECK_EQ(ok, 1);
    CHECK_EQ(best.from_rank, 3);
    CHECK_EQ(best.from_file, 0);
    CHECK_EQ(best.to_rank,   3);
    CHECK_EQ(best.to_file,   7); /* captured the queen */
}

static void test_ai_finds_checkmate_in_one(void) {
    SUITE("find_best_move — finds mate in 1");
    Board b;
    board_init(&b);
    clear_pieces(&b);
    b.turn   = WHITE;
    ai_depth = 2;

    /*
     * White to move.  Qh7# delivers checkmate:
     *   Black king on h8, white queen on g6, white rook on g1.
     *   Qh7 is checkmate (rook covers g-file, queen covers h7+h6).
     */
    place(&b, 7, 7, -KING);   /* h8 */
    place(&b, 5, 6,  QUEEN);  /* g6 */
    place(&b, 0, 6,  ROOK);   /* g1 */
    place(&b, 0, 0,  KING);   /* a1 */

    Move best;
    int ok = find_best_move(&b, &best);
    CHECK_EQ(ok, 1);
    /* Verify the chosen move delivers checkmate (don't hardcode which of
     * the possible mating moves the engine selects). */
    Board after_mate;
    copy_board(&after_mate, &b);
    apply_move(&after_mate, &best);
    Move black_replies[MAX_MOVES];
    int nm = generate_legal_moves(&after_mate, black_replies);
    CHECK(nm == 0 && is_in_check(&after_mate, BLACK));
}

static void test_ai_move_does_not_leave_king_in_check(void) {
    SUITE("find_best_move — chosen move never leaves own king in check");
    Board b;
    board_init(&b);
    clear_pieces(&b);
    b.turn   = WHITE;
    ai_depth = 3;

    /*
     * White king is attacked; AI must block or move king.
     * White: king e1, rook a1.  Black: king h8, rook e8 (giving check).
     */
    place(&b, 0, 4,  KING);
    place(&b, 0, 0,  ROOK);
    place(&b, 7, 7, -KING);
    place(&b, 7, 4, -ROOK);   /* check on e-file */

    Move best;
    int ok = find_best_move(&b, &best);
    CHECK_EQ(ok, 1);

    /* Apply the move and verify white king is no longer in check */
    Board after;
    copy_board(&after, &b);
    apply_move(&after, &best);
    CHECK(!is_in_check(&after, WHITE));
}

/* ================================================================== */
/*  main — register and run all tests                                  */
/* ================================================================== */

typedef void (*TestFn)(void);

static const TestFn tests[] = {
    /* board */
    test_board_init_piece_positions,
    test_board_init_metadata,
    test_copy_board,
    test_sq_str_roundtrip,
    test_board_color_and_type,
    /* is_attacked */
    test_pawn_attacks,
    test_knight_attacks,
    test_bishop_attacks,
    test_rook_attacks,
    test_queen_attacks,
    test_king_attacks,
    /* legal moves */
    test_starting_position_move_count,
    test_pawn_starting_double_push,
    test_pawn_blocked_no_double_push,
    test_pawn_capture,
    test_en_passant,
    test_en_passant_expires,
    test_promotion_generates_four_moves,
    test_promotion_applies_correctly,
    /* castling */
    test_castling_kingside_white,
    test_castling_queenside_white,
    test_castling_blocked,
    test_castling_through_check,
    test_castling_out_of_check,
    test_castling_rights_revoked_after_king_moves,
    test_castling_black,
    /* check / mate / stalemate */
    test_is_in_check,
    test_checkmate_back_rank,
    test_stalemate,
    test_pinned_piece_cannot_move,
    /* apply_move side effects */
    test_apply_move_halfmove_clock,
    test_apply_move_fullmove_counter,
    test_apply_move_turn_flips,
    /* eval */
    test_eval_starting_position_symmetric,
    test_eval_material_advantage,
    test_eval_extra_queen_large_advantage,
    test_eval_pst_center_pawn_better,
    /* ai */
    test_ai_no_moves_returns_zero,
    test_ai_takes_free_piece,
    test_ai_finds_checkmate_in_one,
    test_ai_move_does_not_leave_king_in_check,
};

int main(void) {
    int n = (int)(sizeof(tests) / sizeof(tests[0]));
    for (int i = 0; i < n; i++)
        tests[i]();

    printf("\n══════════════════════════════════\n");
    printf("  %d / %d passed", _passed, _total);
    if (_failed)
        printf("   (%d FAILED)", _failed);
    printf("\n══════════════════════════════════\n");

    return _failed ? 1 : 0;
}