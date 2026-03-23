#!/usr/bin/env python
"""
Complete chess game test flow:
1. Create two users
2. Create a room
3. Both players join
4. Display board
5. Make moves
6. Show final board state
"""
import os
import django
import requests
import json

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.dev')
django.setup()

from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import RefreshToken
from apps.rooms.models import GameRoom
from apps.accounts.models import User

User = get_user_model()
BASE_URL = "http://127.0.0.1:8000/api"

print("\n" + "="*70)
print("CHESS GAME TEST FLOW")
print("="*70)

# Step 1: Create/Get two test users
print("\n[STEP 1] Create/Get Test Users")
print("-" * 70)

white_user, _ = User.objects.get_or_create(
    email="white@chess.test",
    defaults={"username": "white_player", "first_name": "White", "last_name": "Player"}
)
white_user.set_password("password123")
white_user.is_email_verified = True
white_user.save()

black_user, _ = User.objects.get_or_create(
    email="black@chess.test",
    defaults={"username": "black_player", "first_name": "Black", "last_name": "Player"}
)
black_user.set_password("password123")
black_user.is_email_verified = True
black_user.save()

print(f"✓ White Player: {white_user.email}")
print(f"✓ Black Player: {black_user.email}")

# Step 2: Generate tokens for both users
print("\n[STEP 2] Generate JWT Tokens")
print("-" * 70)

white_refresh = RefreshToken.for_user(white_user)
white_token = str(white_refresh.access_token)

black_refresh = RefreshToken.for_user(black_user)
black_token = str(black_refresh.access_token)

print(f"✓ White Token: {white_token[:30]}...")
print(f"✓ Black Token: {black_token[:30]}...")

# Step 3: Create a room
print("\n[STEP 3] Create a Room")
print("-" * 70)

room_data = {
    "room_name": "Chess Match",
    "description": "Test chess game",
    "game_mode": "Blitz"
}

headers = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {white_token}",
}

response = requests.post(
    f"{BASE_URL}/rooms/create/",
    json=room_data,
    headers=headers
)

if response.status_code != 201:
    print(f"✗ Failed to create room: {response.json()}")
    exit(1)

room = response.json()['room']
room_id = room['id']
room_code = room['invite_code']

print(f"✓ Room Created: {room_id}")
print(f"✓ Invite Code: {room_code}")

# Step 4: Both players join the room
print("\n[STEP 4] Players Join the Room")
print("-" * 70)

# White player joins
join_data = {"room_id": str(room_id)}
response = requests.post(
    f"{BASE_URL}/rooms/join/",
    json=join_data,
    headers={"Content-Type": "application/json", "Authorization": f"Bearer {white_token}"}
)

if response.status_code == 200:
    print("✓ White player joined")
else:
    print(f"✗ White player join failed: {response.json()}")

# Black player joins with invite code
join_data = {"invite_code": room_code}
response = requests.post(
    f"{BASE_URL}/rooms/join/",
    json=join_data,
    headers={"Content-Type": "application/json", "Authorization": f"Bearer {black_token}"}
)

if response.status_code == 200:
    print("✓ Black player joined")
else:
    print(f"✗ Black player join failed: {response.json()}")

# Step 5: Get initial board state
print("\n[STEP 5] Initial Board State")
print("-" * 70)

response = requests.get(
    f"{BASE_URL}/chess/room/{room_id}/board/",
    headers={"Authorization": f"Bearer {white_token}"}
)

if response.status_code == 200:
    board_data = response.json()
    print("\nBoard Position:")
    print(board_data['board_ascii'])
    print(f"\nFEN: {board_data['current_fen']}")
    print(f"Turn: {board_data['current_turn']}")
    print(f"Legal Moves (first 10): {board_data['legal_moves'][:10]}")
else:
    print(f"✗ Failed to get board: {response.json()}")

# Step 6: Make some example moves
print("\n[STEP 6] Play Sample Moves")
print("-" * 70)

# Define some sample moves (these are valid opening moves)
sample_moves = [
    {"from_square": "e2", "to_square": "e4", "player": "white", "token": white_token},
    {"from_square": "e7", "to_square": "e5", "player": "black", "token": black_token},
    {"from_square": "g1", "to_square": "f3", "player": "white", "token": white_token},
    {"from_square": "b8", "to_square": "c6", "player": "black", "token": black_token},
]

for i, move_data in enumerate(sample_moves, 1):
    move_info = {
        "from_square": move_data["from_square"],
        "to_square": move_data["to_square"],
    }

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {move_data['token']}"
    }

    response = requests.post(
        f"{BASE_URL}/chess/room/{room_id}/move/",
        json=move_info,
        headers=headers
    )

    if response.status_code == 200:
        result = response.json()
        move = result['move']
        print(f"✓ Move {i}: {move_data['player'].upper()} played {move['san']}")
        print(f"   From: {move_data['from_square']} → To: {move_data['to_square']}")
    else:
        error = response.json()
        print(f"✗ Move {i} failed: {error.get('detail', error)}")
        break

# Step 7: Get final board state
print("\n[STEP 7] Final Board State")
print("-" * 70)

response = requests.get(
    f"{BASE_URL}/chess/room/{room_id}/board/",
    headers={"Authorization": f"Bearer {white_token}"}
)

if response.status_code == 200:
    board_data = response.json()
    print("\nBoard Position After Moves:")
    print(board_data['board_ascii'])
    print(f"\nFEN: {board_data['current_fen']}")
    print(f"Turn: {board_data['current_turn']}")
    print(f"Is Check: {board_data['is_check']}")
    print(f"Is Checkmate: {board_data['is_checkmate']}")
    print(f"Is Stalemate: {board_data['is_stalemate']}")
else:
    print(f"✗ Failed to get board: {response.json()}")

# Step 8: Get move history
print("\n[STEP 8] Move History")
print("-" * 70)

response = requests.get(
    f"{BASE_URL}/chess/room/{room_id}/moves/",
    headers={"Authorization": f"Bearer {white_token}"}
)

if response.status_code == 200:
    moves = response.json()['moves']
    print(f"\nTotal Moves: {len(moves)}")
    for move in moves:
        player_name = move['player']['first_name'] if move['player'] else 'Unknown'
        print(f"  {move['move_number']}. {move['san']} ({player_name})")
else:
    print(f"✗ Failed to get moves: {response.json()}")

# Step 9: Get match details
print("\n[STEP 9] Match Details")
print("-" * 70)

response = requests.get(
    f"{BASE_URL}/chess/room/{room_id}/",
    headers={"Authorization": f"Bearer {white_token}"}
)

if response.status_code == 200:
    match_data = response.json()['match']
    print(f"\nMatch Status: {match_data['status']}")
    print(f"Result: {match_data['result']}")
    print(f"White: {match_data['white_player']['first_name'] if match_data['white_player'] else 'N/A'}")
    print(f"Black: {match_data['black_player']['first_name'] if match_data['black_player'] else 'N/A'}")
    print(f"Fullmove Number: {match_data['fullmove_number']}")
else:
    print(f"✗ Failed to get match details: {response.json()}")

print("\n" + "="*70)
print("TEST COMPLETE!")
print("="*70)
print(f"\nYou can test manually with:")
print(f"  Room ID: {room_id}")
print(f"  Room Code: {room_code}")
print(f"  White Email: white@chess.test")
print(f"  Black Email: black@chess.test")
print(f"  Password: password123")
print("\n" + "="*70)
