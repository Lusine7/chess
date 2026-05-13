# Chess — ENGS110: Introduction to Programming Final Project

> A chess game with a C backend engine and a Python/Pygame frontend, built as a final project for ENGS110: Introduction to Programming.

---

## Features

- **AI Engine** — Minimax algorithm with alpha-beta pruning (adjustable search depth)
- **Difficulty Levels** — Easy (depth 2), Intermediate (depth 4), Hard (depth 6)
- **Color Selection** — Play as White or Black
- **Move Validation** — Full legal-move checking for both the player and the AI
- **Custom Protocol** — Frontend talks to the C engine via stdin/stdout as a subprocess

---

## Tech Stack

| Layer    | Technology            |
|----------|-----------------------|
| Backend  | C (gcc), Makefile     |
| Frontend | Python 3, Pygame      |
| Bridge   | stdin/stdout protocol |

---

## Requirements

- **GCC** (or any C11-compatible compiler)
- **Make**
- **Python 3.8+**
- **pip**

Python package dependencies are listed in [`requirements.txt`](requirements.txt):

```
pygame>=2.5.0
```

---

## Setup & Running

### 1. Install Python dependencies

```bash
cd backend
make setup
```

This runs `pip3 install -r ../requirements.txt` to install Pygame.

### 2. Build the C backend and launch the game

```bash
cd backend
make run
```

This compiles the engine and then starts the Python frontend automatically.

### Alternatively, build and run separately

```bash
# Build the backend
cd backend
make

# Run the frontend
cd ../frontend
python3 main.py
```

### Clean build artifacts

```bash
cd backend
make clean
```

---

## Project Structure

```
chess/
├── backend/
│   ├── main.c        # Entry point; handles stdin/stdout protocol
│   ├── board.c/h     # Board representation and state
│   ├── moves.c/h     # Legal move generation and validation
│   ├── eval.c/h      # Board evaluation (piece-square tables, material)
│   ├── ai.c/h        # Minimax with alpha-beta pruning
│   └── Makefile      # Build system (also: setup, run, clean targets)
├── frontend/
│   ├── main.py       # App entry point; game setup screen
│   ├── game.py       # Game loop and state management
│   ├── renderer.py   # Pygame rendering (board, pieces, UI)
│   └── protocol.py   # stdin/stdout communication with the C engine
├── requirements.txt  # Python dependencies (pygame)
└── README.md
```

---

## How It Works

1. The Python frontend launches the compiled C binary as a **subprocess**.
2. They communicate via a **custom text protocol** over stdin/stdout.
3. On the player's turn, the move is validated in Python before being sent to the engine.
4. On the AI's turn, the C engine runs **Minimax with alpha-beta pruning** and returns the best move.
5. The frontend renders the updated board state using **Pygame**.
