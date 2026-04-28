Chess Game as a Final Project for ENGS110: Introduction to Programming

This is a game which consists of a player and an engine (AI). 

If it is the player's turn, the move is first validated. The same move validation also exists for the Minimax algorithm for the AI move generation.

The AI move generation is a Minimax algorithm with alpha-beta pruning to optimize the search algorithm.

The backend is in C and the frontend is in Python, utilizing its pygame library to run C as a subprocess, talking to it via a custom stdin/stdout process.


