"""
setup_pieces.py
---------------
Downloads pre-rendered chess piece PNGs from the chessboard.js npm package
via jsDelivr CDN — no Cairo / ImageMagick / GTK needed.

Run once before starting the game:
    python setup_pieces.py
"""

import urllib.request
import os
import sys

PIECES_DIR = os.path.join(os.path.dirname(__file__), "frontend", "assets", "pieces")
os.makedirs(PIECES_DIR, exist_ok=True)

# chessboard.js ships Wikipedia-style PNG pieces (pure PNG, no conversion needed)
BASE = "https://cdn.jsdelivr.net/npm/@chrisoakman/chessboardjs@1.0.0/img/chesspieces/wikipedia"

PIECES = [
    "wK", "wQ", "wR", "wB", "wN", "wP",
    "bK", "bQ", "bR", "bB", "bN", "bP",
]

headers = {
    "User-Agent": "chess-setup-script/1.0",
    "Accept": "image/png,image/*,*/*",
}

ok = fail = 0

for name in PIECES:
    dest = os.path.join(PIECES_DIR, f"{name}.png")

    if os.path.exists(dest) and os.path.getsize(dest) > 1000:
        print(f"  {name}.png  already exists — skipping")
        ok += 1
        continue

    url = f"{BASE}/{name}.png"
    print(f"  Downloading  {name}.png ...", end="  ", flush=True)
    try:
        req  = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=20) as resp:
            data = resp.read()
        with open(dest, "wb") as f:
            f.write(data)
        print(f"OK  ({len(data)//1024 or 1}KB)")
        ok += 1
    except Exception as exc:
        print(f"FAILED  ({exc})")
        fail += 1

print()
print(f"Done — {ok} pieces ready, {fail} failed.")
if fail:
    print("Tip: check your internet connection and try again.")
    sys.exit(1)
else:
    print(f"Piece assets saved to:  {PIECES_DIR}")
