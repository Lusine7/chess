/*
 * test_chess.c — Unit tests for board.c, moves.c, and eval.c
 *
 * Build & run:
 *   make test
 *
 * Uses a minimal hand-rolled test framework — no external dependencies.
 */

#include <stdio.h>
#include <string.h>

#include "board.h"
#include "moves.h"
#include "eval.h"

/* ------------------------------------------------------------------ */
/*  Minimal test framework                                              */
/* ------------------------------------------------------------------ */

static int tests_run    = 0;
static int tests_passed = 0;
static int tests_failed = 0;

#define ASSERT(cond, msg) do {                                          \
    tests_run++;                                                        \
    if (cond) {                                                         \
        tests_passed++;                                                 \
        printf("  [PASS] %s\n", msg);                                  \
    } else {                                                            \
        tests_failed++;                                                 \
        printf("  [FAIL] %s  (line %d)\n", msg, __LINE__);            \
    }                                                                   \
} while (0)

#define SECTION(name) printf("\n=== %s ===\n", name)

/* ------------------------------------------------------------------ */
/*  Helper: count moves from a particular square                       */
/* ------------------------------------------------------------------ */
static int count_moves_from(Board *b, int rank, int file) {
    Move moves[MAX_MOVES];
    int n = generate_legal_moves(b, moves);
    int c = 0;
    for (int i = 0; i < n; i++)
        if (moves[i].from_rank == rank && moves[i].from_file == file)
            c++;
    return c;
}

/* ------------------------------------------------------------------ */
/*  Helper: find a legal move from->to                                 */
/* ------------------------------------------------------------------ */
static int has_legal_move(Board *b, int fr, int ff, int tr, int tf) {
    Move moves[MAX_MOVES];
    int n = generate_legal_moves(b, moves);
    for (int i = 0; i < n; i++)
        if (moves[i].from_rank == fr && moves[i].from_file == ff &&
            moves[i].to_rank   == tr && moves[i].to_file   == tf)
            return 1;
    return 0;
}

/* ================================================================== */
/*  1. board.c tests                                                   */
/* ================================================================== */

static void test_board_init(void) {
    SECTION("board_init");
    Board b;
    board_init(&b);

    ASSERT(b.turn == WHITE, "Initial turn is WHITE");
    ASSERT(b.white_castle_k == 1, "White kingside castling right set");
    ASSERT(b.white_castle_q == 1, "White queenside castling right set");
    ASSERT(b.black_castle_k == 1, "Black kingside castling right set");
    ASSERT(b.black_castle_q == 1, "Black queenside castling right set");
    ASSERT(b.ep_rank == -1, "No en-passant at start");
    ASSERT(b.ep_file == -1, "No en-passant file at start");
    ASSERT(b.halfmove_clock == 0, "Halfmove clock starts at 0");
    ASSERT(b.fullmove_number == 1, "Fullmove number starts at 1");

    /* Back ranks */
    ASSERT(b.squares[0][0] ==  ROOK,   "a1 = white rook");
    ASSERT(b.squares[0][1] ==  KNIGHT, "b1 = white knight");
    ASSERT(b.squares[0][2] ==  BISHOP, "c1 = white bishop");
    ASSERT(b.squares[0][3] ==  QUEEN,  "d1 = white queen");
    ASSERT(b.squares[0][4] ==  KING,   "e1 = white king");
    ASSERT(b.squares[7][4] == -KING,   "e8 = black king");
    ASSERT(b.squares[7][3] == -QUEEN,  "d8 = black queen");

    /* Pawns */
    for (int f = 0; f < 8; f++) {
        ASSERT(b.squares[1][f] ==  PAWN, "White pawn on rank 2");
        ASSERT(b.squares[6][f] == -PAWN, "Black pawn on rank 7");
    }

    /* Middle ranks empty */
    for (int r = 2; r <= 5; r++)
        for (int f = 0; f < 8; f++)
            ASSERT(b.squares[r][f] == EMPTY, "Middle squares empty");
}

static void test_board_color_type(void) {
    SECTION("board_color / board_type");
    ASSERT(board_color( ROOK)  == WHITE, "White rook -> WHITE");
    ASSERT(board_color(-ROOK)  == BLACK, "Black rook -> BLACK");
    ASSERT(board_color(EMPTY)  == 0,     "Empty square -> 0");
    ASSERT(board_type( QUEEN)  == QUEEN, "Positive piece type");
    ASSERT(board_type(-QUEEN)  == QUEEN, "Negative piece type");
    ASSERT(board_type(EMPTY)   == EMPTY, "Empty type");
}

static void test_sq_str_conversion(void) {
    SECTION("sq_to_str / str_to_rank / str_to_file");
    char buf[4];
    sq_to_str(0, 0, buf); ASSERT(strcmp(buf, "a1") == 0, "a1 round-trip");
    sq_to_str(7, 7, buf); ASSERT(strcmp(buf, "h8") == 0, "h8 round-trip");
    sq_to_str(3, 4, buf); ASSERT(strcmp(buf, "e4") == 0, "e4 round-trip");

    ASSERT(str_to_rank("e4") == 3, "str_to_rank e4 == 3");
    ASSERT(str_to_file("e4") == 4, "str_to_file e4 == 4");
    ASSERT(str_to_rank("a1") == 0, "str_to_rank a1 == 0");
    ASSERT(str_to_file("h8") == 7, "str_to_file h8 == 7");
}

static void test_copy_board(void) {
    SECTION("copy_board");
    Board src, dst;
    board_init(&src);
    src.squares[4][4] = QUEEN; /* mutate src */
    copy_board(&dst, &src);
    ASSERT(dst.squares[4][4] == QUEEN, "copy_board copies squares");
    ASSERT(dst.turn == src.turn,        "copy_board copies turn");
    /* Verify independence */
    dst.squares[4][4] = EMPTY;
    ASSERT(src.squares[4][4] == QUEEN, "copy_board deep copy (independent)");
}

/* ================================================================== */
/*  2. moves.c — move generation tests                                 */
/* ================================================================== */

static void test_opening_move_count(void) {
    SECTION("Opening position legal moves");
    Board b;
    board_init(&b);
    Move moves[MAX_MOVES];
    int n = generate_legal_moves(&b, moves);
    /* Standard chess: 20 legal opening moves for White */
    ASSERT(n == 20, "White has 20 legal moves at start");

    /* Make one pawn move then check Black */
    Move e2e4 = {1, 4, 3, 4, 0};
    apply_move(&b, &e2e4);
    n = generate_legal_moves(&b, moves);
    ASSERT(n == 20, "Black has 20 legal moves after 1.e4");
}

static void test_pawn_single_double_push(void) {
    SECTION("Pawn single/double push");
    Board b;
    board_init(&b);

    /* e2 pawn: 1 single push + 1 double push = 2 moves */
    ASSERT(count_moves_from(&b, 1, 4) == 2, "e2 pawn has 2 moves");
    ASSERT(has_legal_move(&b, 1, 4, 2, 4),  "e2-e3 legal");
    ASSERT(has_legal_move(&b, 1, 4, 3, 4),  "e2-e4 legal");
}

static void test_knight_moves(void) {
    SECTION("Knight moves");
    Board b;
    board_init(&b);
    /* b1 knight can go to a3 or c3 (2 moves in opening) */
    ASSERT(count_moves_from(&b, 0, 1) == 2, "b1 knight has 2 moves at start");
    ASSERT(has_legal_move(&b, 0, 1, 2, 0),  "Nb1-a3 legal");
    ASSERT(has_legal_move(&b, 0, 1, 2, 2),  "Nb1-c3 legal");
}

static void test_is_attacked(void) {
    SECTION("is_attacked");
    Board b;
    board_init(&b);

    /* e4 square is not attacked by black at start */
    ASSERT(!is_attacked(&b, 3, 4, BLACK), "e4 not attacked by black at start");

    /* After 1.e4, d5 is attacked by the white pawn on e4 */
    Move e4 = {1, 4, 3, 4, 0};
    apply_move(&b, &e4);
    ASSERT(is_attacked(&b, 4, 3, WHITE), "d5 attacked by white pawn on e4");
    ASSERT(is_attacked(&b, 4, 5, WHITE), "f5 attacked by white pawn on e4");
}

static void test_is_in_check(void) {
    SECTION("is_in_check");
    /* Manually construct Scholar's-mate position where Black is in checkmate */
    Board b;
    memset(&b, 0, sizeof(b));
    /* Place kings */
    b.squares[0][4] =  KING;
    b.squares[7][4] = -KING;
    /* White queen on f7 attacks black king */
    b.squares[6][5] =  QUEEN;
    b.turn = BLACK;

    ASSERT(is_in_check(&b, BLACK), "Black in check from queen on f7");
    ASSERT(!is_in_check(&b, WHITE), "White not in check");
}

static void test_en_passant(void) {
    SECTION("En-passant");
    Board b;
    board_init(&b);

    /* 1.e4 d5  2.e5  — now push f5 for black to allow ep */
    Move e4   = {1,4,3,4,0};  apply_move(&b, &e4);
    Move d5   = {6,3,4,3,0};  apply_move(&b, &d5);
    Move e5   = {3,4,4,4,0};  apply_move(&b, &e5);
    Move f5   = {6,5,4,5,0};  apply_move(&b, &f5);

    /* White pawn on e5 can capture en-passant on f6 */
    ASSERT(b.ep_rank == 5 && b.ep_file == 5, "EP target set to f6");
    ASSERT(has_legal_move(&b, 4,4, 5,5), "White can capture en-passant exf6");

    /* Apply ep capture and verify black pawn removed */
    Move ep = {4,4,5,5,0};
    apply_move(&b, &ep);
    ASSERT(b.squares[4][5] == EMPTY, "Captured pawn removed by en-passant");
    ASSERT(b.squares[5][5] == PAWN,  "White pawn moved to f6");
}

static void test_castling(void) {
    SECTION("Castling");
    Board b;
    board_init(&b);

    /* Clear squares for white kingside castle */
    b.squares[0][5] = EMPTY; /* f1 */
    b.squares[0][6] = EMPTY; /* g1 */

    ASSERT(has_legal_move(&b, 0,4, 0,6), "White kingside castle available");

    Move castle = {0,4,0,6,0};
    apply_move(&b, &castle);
    ASSERT(b.squares[0][6] ==  KING, "King moved to g1");
    ASSERT(b.squares[0][5] ==  ROOK, "Rook moved to f1");
    ASSERT(b.squares[0][7] == EMPTY, "h1 empty after castle");
    ASSERT(b.white_castle_k == 0,    "White kingside right revoked");
    ASSERT(b.white_castle_q == 0,    "White queenside right revoked");
}

static void test_promotion(void) {
    SECTION("Pawn promotion");
    Board b;
    memset(&b, 0, sizeof(b));
    b.squares[0][4] =  KING;
    b.squares[7][4] = -KING;
    /* White pawn one step from promotion */
    b.squares[6][0] = PAWN;
    b.turn = WHITE;

    Move moves[MAX_MOVES];
    int n = generate_legal_moves(&b, moves);
    /* Should produce 4 promotion moves */
    int promo_count = 0;
    for (int i = 0; i < n; i++)
        if (moves[i].from_rank == 6 && moves[i].from_file == 0 &&
            moves[i].to_rank   == 7)
            promo_count++;
    ASSERT(promo_count == 4, "Pawn at a7 generates 4 promotion moves");

    /* Apply queen promotion */
    Move promo_q = {6,0,7,0,QUEEN};
    apply_move(&b, &promo_q);
    ASSERT(b.squares[7][0] == QUEEN, "Pawn promoted to queen");
}

static void test_checkmate_no_moves(void) {
    SECTION("Checkmate / stalemate move count");
    /* Fool's mate position: Black is checkmated */
    Board b;
    board_init(&b);
    /* 1.f3 e5  2.g4 Qh4# */
    apply_move(&b, &(Move){1,5,2,5,0}); /* f3  (f2-f3) */
    apply_move(&b, &(Move){6,4,4,4,0}); /* e5  (e7-e5) */
    apply_move(&b, &(Move){1,6,3,6,0}); /* g4  (g2-g4) */
    apply_move(&b, &(Move){7,3,3,7,0}); /* Qh4 (d8-h4) — rank index 3 = chess rank 4 */

    /* Now it's White's turn and White is in checkmate */
    Move moves[MAX_MOVES];
    int n = generate_legal_moves(&b, moves);
    ASSERT(n == 0,                    "White has 0 moves in Fool's mate");
    ASSERT(is_in_check(&b, WHITE),    "White is in check in Fool's mate");
}

/* ================================================================== */
/*  3. eval.c tests                                                    */
/* ================================================================== */

static void test_eval_initial_symmetry(void) {
    SECTION("evaluate — initial position symmetry");
    Board b;
    board_init(&b);
    int score = evaluate(&b);
    ASSERT(score == 0, "Initial position evaluates to 0 (symmetric)");
}

static void test_eval_material_advantage(void) {
    SECTION("evaluate — material advantage");
    Board b;
    board_init(&b);

    /* Remove a black pawn — white should now have a positive score */
    b.squares[6][0] = EMPTY;
    int score = evaluate(&b);
    ASSERT(score > 0, "White ahead by one pawn: score > 0");

    /* Remove a white queen too — black should now be clearly ahead */
    b.squares[0][3] = EMPTY;
    score = evaluate(&b);
    ASSERT(score < 0, "Black ahead after white loses queen: score < 0");
}

static void test_eval_empty_board_kings(void) {
    SECTION("evaluate — symmetric kings-only board");
    Board b;
    memset(&b, 0, sizeof(b));
    b.squares[0][4] =  KING;
    b.squares[7][4] = -KING;
    b.turn = WHITE;
    /* Kings only — score depends only on PST mirroring, should be 0 */
    int score = evaluate(&b);
    ASSERT(score == 0, "Symmetric kings-only board scores 0");
}

/* ================================================================== */
/*  main                                                                */
/* ================================================================== */

int main(void) {
    printf("Chess Engine Unit Tests\n");
    printf("=======================\n");

    /* board.c */
    test_board_init();
    test_board_color_type();
    test_sq_str_conversion();
    test_copy_board();

    /* moves.c */
    test_opening_move_count();
    test_pawn_single_double_push();
    test_knight_moves();
    test_is_attacked();
    test_is_in_check();
    test_en_passant();
    test_castling();
    test_promotion();
    test_checkmate_no_moves();

    /* eval.c */
    test_eval_initial_symmetry();
    test_eval_material_advantage();
    test_eval_empty_board_kings();

    /* Summary */
    printf("\n----------------------------\n");
    printf("Results: %d/%d passed", tests_passed, tests_run);
    if (tests_failed)
        printf(", %d FAILED", tests_failed);
    printf("\n");

    return tests_failed > 0 ? 1 : 0;
}
