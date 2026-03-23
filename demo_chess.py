#!/usr/bin/env python
"""
Quick demo of chess logic and board visualization
"""
import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.dev')
django.setup()

import chess
from apps.chessplay.models import ChessMatch
from apps.rooms.models import GameRoom

print("\n" + "="*70)
print("CHESS BOARD DEMONSTRATION")
print("="*70)

# Create initial board
board = chess.Board()

print("\n[Initial Chess Board]")
print(board)

print("\n[Game Info]")
print(f"FEN: {board.fen()}")
print(f"Turn: {'White' if board.turn else 'Black'}")
print(f"Is Check: {board.is_check()}")
print(f"Is Checkmate: {board.is_checkmate()}")
print(f"Is Stalemate: {board.is_stalemate()}")

print("\n[Legal Moves for White (first 10)]")
legal_moves = list(board.legal_moves)[:10]
for move in legal_moves:
    print(f"  - {board.san(move)}")

# Make some sample moves
print("\n" + "="*70)
print("PLAYING SAMPLE GAME")
print("="*70)

moves = [
    "e2e4",  # 1. e4
    "e7e5",  # 1... e5
    "g1f3",  # 2. Nf3
    "b8c6",  # 2... Nc6
]

for i, uci_move in enumerate(moves, 1):
    move = chess.Move.from_uci(uci_move)
    san = board.san(move)
    board.push(move)

    move_num = (i + 1) // 2
    side = "White" if i % 2 == 1 else "Black"

    print(f"\nMove {move_num}: {side} played {san}")
    print(f"FEN: {board.fen()}")

print("\n[Board After Moves]")
print(board)

print(f"\nTurn: {'White' if board.turn else 'Black'}")
print(f"Legal Moves Available: {len(list(board.legal_moves))}")

# Show piece positions
print("\n" + "="*70)
print("BOARD ANALYSIS")
print("="*70)

print("\n[Piece Positions]")
positions = {}
for square in chess.SQUARES:
    piece = board.piece_at(square)
    if piece:
        square_name = chess.square_name(square)
        piece_name = chess.piece_name(piece.piece_type).title()
        color = "White" if piece.color == chess.WHITE else "Black"
        positions[square_name] = f"{color} {piece_name}"

for square_name in sorted(positions.keys()):
    print(f"  {square_name.upper()}: {positions[square_name]}")

# Database models example
print("\n" + "="*70)
print("DATABASE MODELS")
print("="*70)

print(f"\nChessMatch fields:")
print(f"  - room (OneToOne)")
print(f"  - white_player (ForeignKey)")
print(f"  - black_player (ForeignKey)")
print(f"  - status: {' | '.join([c[0] for c in ChessMatch.STATUS_CHOICES])}")
print(f"  - current_fen (TextField)")
print(f"  - pgn (TextField)")
print(f"  - is_check, is_checkmate, is_stalemate (BooleanField)")

print(f"\nChessMove fields:")
print(f"  - match (ForeignKey)")
print(f"  - move_number (PositiveInteger)")
print(f"  - player (ForeignKey)")
print(f"  - side: {' | '.join([c[0] for c in [('white', 'White'), ('black', 'Black')]])}")
print(f"  - from_square, to_square (CharField)")
print(f"  - uci, san (CharField)")
print(f"  - is_capture, is_check (BooleanField)")

print("\n" + "="*70)
print("API ENDPOINTS")
print("="*70)

print("""
Available Chess API endpoints:

1. GET /api/chess/room/<room_id>/
   - Get match details for a room
   - Returns: match info, white_player, black_player, status, result, moves

2. GET /api/chess/room/<room_id>/moves/
   - Get all moves in the game
   - Returns: list of moves with player, san, fen_after, etc.

3. GET /api/chess/room/<room_id>/board/
   - Get current board state and visualization
   - Returns: board_ascii, board_position, legal_moves, current_fen, turn info

4. POST /api/chess/room/<room_id>/move/
   - Make a move in the game
   - Body: {"from_square": "e2", "to_square": "e4", "promotion": "q"}
   - Returns: move info + updated match + room status
""")

print("\n" + "="*70)
print("NEXT STEPS")
print("="*70)

print("""
To use the chess game:

1. Create a room via: POST /api/rooms/create/
2. Both players join the room
3. Get board state: GET /api/chess/room/<room_id>/board/
4. Make moves: POST /api/chess/room/<room_id>/move/
5. View move history: GET /api/chess/room/<room_id>/moves/
6. Get match details: GET /api/chess/room/<room_id>/

All endpoints require authentication with JWT tokens!
""")

print("="*70 + "\n")
