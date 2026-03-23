#!/usr/bin/env python
"""
Simple chess board demonstration (no Django required)
"""
import chess

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

print("\n" + "="*70)
print("CHESS RULES IMPLEMENTED")
print("="*70)

print("""
✓ Legal move validation - Only valid moves accepted
✓ Position tracking - FEN notation support
✓ Turn management - Alternating white/black moves
✓ Check detection - Detects when king is in check
✓ Checkmate detection - Game ending condition
✓ Stalemate detection - Draw condition
✓ Move notation - Supports UCI and SAN notation
✓ Piece positions - Full board state tracking
✓ Move history - Complete move recording
✓ Pawn promotion - Supports pawn queens, rooks, bishops, knights
""")

print("="*70)
print("API ENDPOINTS AVAILABLE")
print("="*70)

print("""
1. GET /api/chess/room/<room_id>/board/
   - Get current board state with piece positions
   - Returns ASCII board, FEN, legal moves, turn info

2. POST /api/chess/room/<room_id>/move/
   - Make a move in the game
   - Body: {"from_square": "e2", "to_square": "e4"}
   - Returns updated board state

3. GET /api/chess/room/<room_id>/moves/
   - Get complete move history
   - Returns all moves with player, notation, timestamp

4. GET /api/chess/room/<room_id>/
   - Get match details and status
   - Returns white/black players, result, started/ended times

All endpoints require JWT authentication!
""")

print("="*70 + "\n")
