"""
test_protocol.py — Unit tests for the ChessProtocol class.

All tests use unittest.mock to fake the subprocess, so no compiled chess
binary is required.  The suite exercises every public method, including
normal replies, edge cases, and graceful error handling.

Run from the project root:
    python -m unittest frontend/test_protocol.py -v
  or simply:
    make test_py
"""

import unittest
from unittest.mock import MagicMock, patch
import sys
import os

# Allow running from the project root or from inside frontend/
sys.path.insert(0, os.path.dirname(__file__))
from protocol import ChessProtocol


# ------------------------------------------------------------------ #
#  Helper                                                             #
# ------------------------------------------------------------------ #

def _make_protocol(responses: list) -> ChessProtocol:
    """
    Build a ChessProtocol backed by a mock subprocess.

    `responses` is a list of strings the fake engine will return, one per
    readline() call (newline is added automatically).
    """
    mock_proc = MagicMock()
    mock_proc.stdin  = MagicMock()
    mock_proc.stdout.readline.side_effect = [r + "\n" for r in responses]

    with patch("os.path.exists", return_value=True), \
         patch("subprocess.Popen", return_value=mock_proc):
        proto = ChessProtocol("/fake/chess")

    return proto


# ================================================================== #
#  __init__                                                           #
# ================================================================== #

class TestInit(unittest.TestCase):

    def test_raises_when_binary_missing(self):
        """FileNotFoundError if the binary path does not exist."""
        with patch("os.path.exists", return_value=False):
            with self.assertRaises(FileNotFoundError):
                ChessProtocol("/nonexistent/chess")

    def test_launches_subprocess_with_correct_binary(self):
        """Popen is called with the exact binary path supplied."""
        mock_proc = MagicMock()
        mock_proc.stdin = MagicMock()
        with patch("os.path.exists", return_value=True), \
             patch("subprocess.Popen", return_value=mock_proc) as mock_popen:
            ChessProtocol("/my/chess")
            args, _ = mock_popen.call_args
            self.assertEqual(args[0], ["/my/chess"])


# ================================================================== #
#  init()                                                             #
# ================================================================== #

class TestInitCommand(unittest.TestCase):

    def test_returns_true_on_ok(self):
        proto = _make_protocol(["OK"])
        self.assertTrue(proto.init())

    def test_returns_false_on_error_reply(self):
        proto = _make_protocol(["ERROR"])
        self.assertFalse(proto.init())

    def test_sends_init_command(self):
        proto = _make_protocol(["OK"])
        proto.init()
        proto.proc.stdin.write.assert_called_with("INIT\n")


# ================================================================== #
#  set_depth()                                                        #
# ================================================================== #

class TestSetDepth(unittest.TestCase):

    def test_returns_true_on_ok(self):
        proto = _make_protocol(["OK"])
        self.assertTrue(proto.set_depth(4))

    def test_returns_false_on_non_ok(self):
        proto = _make_protocol(["ERROR"])
        self.assertFalse(proto.set_depth(4))

    def test_sends_correct_depth_value(self):
        proto = _make_protocol(["OK"])
        proto.set_depth(6)
        proto.proc.stdin.write.assert_called_with("DEPTH 6\n")

    def test_depth_1_easy(self):
        proto = _make_protocol(["OK"])
        proto.set_depth(2)
        proto.proc.stdin.write.assert_called_with("DEPTH 2\n")


# ================================================================== #
#  get_moves()                                                        #
# ================================================================== #

class TestGetMoves(unittest.TestCase):

    def test_returns_list_of_squares(self):
        proto = _make_protocol(["MOVES e3 e4"])
        self.assertEqual(proto.get_moves("e2"), ["e3", "e4"])

    def test_returns_single_move(self):
        proto = _make_protocol(["MOVES a4"])
        self.assertEqual(proto.get_moves("a3"), ["a4"])

    def test_returns_empty_when_pawn_has_no_moves(self):
        proto = _make_protocol(["MOVES"])
        self.assertEqual(proto.get_moves("e5"), [])

    def test_returns_empty_on_unexpected_reply(self):
        """Non-MOVES prefix → empty list (graceful degradation)."""
        proto = _make_protocol(["ERROR unknown square"])
        self.assertEqual(proto.get_moves("z9"), [])

    def test_sends_correct_command(self):
        proto = _make_protocol(["MOVES d4 d5"])
        proto.get_moves("d3")
        proto.proc.stdin.write.assert_called_with("MOVES d3\n")


# ================================================================== #
#  make_move()                                                        #
# ================================================================== #

class TestMakeMove(unittest.TestCase):

    def test_success_returns_true_and_reply(self):
        proto = _make_protocol(["MOVED e2e4"])
        ok, reply = proto.make_move("e2", "e4")
        self.assertTrue(ok)
        self.assertEqual(reply, "MOVED e2e4")

    def test_illegal_move_returns_false(self):
        proto = _make_protocol(["ILLEGAL"])
        ok, reply = proto.make_move("e2", "e5")
        self.assertFalse(ok)
        self.assertEqual(reply, "ILLEGAL")

    def test_sends_correct_move_string(self):
        proto = _make_protocol(["MOVED e2e4"])
        proto.make_move("e2", "e4")
        proto.proc.stdin.write.assert_called_with("MOVE e2e4\n")

    def test_promotion_appended_to_command(self):
        proto = _make_protocol(["MOVED e7e8q"])
        proto.make_move("e7", "e8", promotion="q")
        proto.proc.stdin.write.assert_called_with("MOVE e7e8q\n")

    def test_no_promotion_suffix_when_none(self):
        proto = _make_protocol(["MOVED d2d4"])
        proto.make_move("d2", "d4", promotion=None)
        proto.proc.stdin.write.assert_called_with("MOVE d2d4\n")

    def test_all_promotion_pieces_formatted(self):
        """Each promotion letter is forwarded verbatim to the engine."""
        for piece in ("q", "r", "b", "n"):
            proto = _make_protocol([f"MOVED a7a8{piece}"])
            proto.make_move("a7", "a8", promotion=piece)
            proto.proc.stdin.write.assert_called_with(f"MOVE a7a8{piece}\n")


# ================================================================== #
#  ai_move()                                                          #
# ================================================================== #

class TestAiMove(unittest.TestCase):

    def test_parses_normal_move(self):
        proto = _make_protocol(["AI_MOVED e2e4"])
        ok, fr, to, promo = proto.ai_move()
        self.assertTrue(ok)
        self.assertEqual(fr, "e2")
        self.assertEqual(to, "e4")
        self.assertIsNone(promo)

    def test_parses_promotion_move(self):
        proto = _make_protocol(["AI_MOVED e7e8q"])
        ok, fr, to, promo = proto.ai_move()
        self.assertTrue(ok)
        self.assertEqual(fr, "e7")
        self.assertEqual(to, "e8")
        self.assertEqual(promo, "q")

    def test_parses_knight_promotion(self):
        proto = _make_protocol(["AI_MOVED a2a1n"])
        ok, fr, to, promo = proto.ai_move()
        self.assertTrue(ok)
        self.assertEqual(promo, "n")

    def test_returns_false_tuple_on_failure(self):
        proto = _make_protocol(["NOMOVE"])
        ok, fr, to, promo = proto.ai_move()
        self.assertFalse(ok)
        self.assertIsNone(fr)
        self.assertIsNone(to)
        self.assertIsNone(promo)

    def test_sends_ai_move_command(self):
        proto = _make_protocol(["AI_MOVED a1a2"])
        proto.ai_move()
        proto.proc.stdin.write.assert_called_with("AI_MOVE\n")


# ================================================================== #
#  status()                                                           #
# ================================================================== #

class TestStatus(unittest.TestCase):

    def test_parses_playing_status(self):
        proto = _make_protocol(["STATUS white playing"])
        turn, state = proto.status()
        self.assertEqual(turn, "white")
        self.assertEqual(state, "playing")

    def test_parses_black_turn(self):
        proto = _make_protocol(["STATUS black playing"])
        turn, state = proto.status()
        self.assertEqual(turn, "black")
        self.assertEqual(state, "playing")

    def test_parses_checkmate(self):
        proto = _make_protocol(["STATUS black checkmate"])
        turn, state = proto.status()
        self.assertEqual(turn, "black")
        self.assertEqual(state, "checkmate")

    def test_parses_stalemate(self):
        proto = _make_protocol(["STATUS white stalemate"])
        turn, state = proto.status()
        self.assertEqual(turn, "white")
        self.assertEqual(state, "stalemate")

    def test_returns_none_on_malformed_reply(self):
        proto = _make_protocol(["GARBAGE"])
        turn, state = proto.status()
        self.assertIsNone(turn)
        self.assertIsNone(state)

    def test_returns_none_on_partial_reply(self):
        """STATUS with only 2 tokens (missing state) → (None, None)."""
        proto = _make_protocol(["STATUS white"])
        turn, state = proto.status()
        self.assertIsNone(turn)
        self.assertIsNone(state)

    def test_sends_status_command(self):
        proto = _make_protocol(["STATUS white playing"])
        proto.status()
        proto.proc.stdin.write.assert_called_with("STATUS\n")


# ================================================================== #
#  quit()                                                             #
# ================================================================== #

class TestQuit(unittest.TestCase):

    def test_sends_quit_command(self):
        proto = _make_protocol(["OK"])
        proto.quit()
        proto.proc.stdin.write.assert_called_with("QUIT\n")

    def test_tolerates_broken_pipe(self):
        """quit() must not raise even if the process is already dead."""
        proto = _make_protocol([])
        proto.proc.stdin.write.side_effect = BrokenPipeError
        try:
            proto.quit()   # must not propagate the exception
        except Exception as exc:
            self.fail(f"quit() raised unexpectedly: {exc}")

    def test_calls_terminate_on_process(self):
        """proc.terminate() is always called for cleanup."""
        proto = _make_protocol(["OK"])
        proto.quit()
        proto.proc.terminate.assert_called_once()


# ================================================================== #
#  Entry point                                                        #
# ================================================================== #

if __name__ == "__main__":
    unittest.main(verbosity=2)
