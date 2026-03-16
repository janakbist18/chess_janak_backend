# Chess Janak Backend - Complete API Documentation

## Base URL
```
http://localhost:8000/api/v1/
https://your-domain.com/api/v1/  (production)
```

---

## Ì¥ê Authentication Endpoints

### 1. Send OTP
**Endpoint:** `POST /accounts/auth/send_otp/`

**Purpose:** Send OTP code to email

**Request:**
```json
{
  "email": "user@example.com",
  "purpose": "login"  // or "registration"
}
```

**Response (200):**
```json
{
  "message": "OTP sent to user@example.com",
  "email": "user@example.com",
  "purpose": "login"
}
```

**Errors:**
- 400: Email is required
- 404: Email not found (for login)

---

### 2. Verify OTP & Login/Register
**Endpoint:** `POST /accounts/auth/verify_otp/`

**Purpose:** Verify OTP and authenticate user

**Request:**
```json
{
  "email": "user@example.com",
  "otp_code": "123456",
  "username": "username",     // for registration
  "name": "User Name",        // for registration
  "purpose": "login"          // or "registration"
}
```

**Response (200):**
```json
{
  "message": "Authentication successful",
  "user": {
    "id": 1,
    "email": "user@example.com",
    "username": "username",
    "name": "User Name",
    "is_verified": true,
    "profile_image": null,
    "online_status": "offline"
  },
  "tokens": {
    "access": "eyJ0eXAiOiJKV1QiLCJhbGc...",
    "refresh": "eyJ0eXAiOiJKV1QiLCJhbGc..."
  }
}
```

**Errors:**
- 400: Invalid OTP or expired
- 401: Authentication failed

---

### 3. Resend OTP
**Endpoint:** `POST /accounts/auth/resend_otp/`

**Request:**
```json
{
  "email": "user@example.com",
  "purpose": "login"
}
```

**Response (200):**
```json
{
  "message": "OTP sent to user@example.com"
}
```

---

### 4. Refresh Token
**Endpoint:** `POST /accounts/auth/refresh_token/`

**Request:**
```json
{
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGc..."
}
```

**Response (200):**
```json
{
  "access": "eyJ0eXAiOiJKV1QiLCJhbGc..."
}
```

---

### 5. Logout
**Endpoint:** `POST /accounts/auth/logout/`

**Headers:**
```
Authorization: Bearer {access_token}
```

**Response (200):**
```json
{
  "message": "Logged out successfully"
}
```

---

## ‚öôÔ∏è User Preferences Endpoints

### 1. Get User Preferences
**Endpoint:** `GET /preferences/preferences/`

**Headers:**
```
Authorization: Bearer {access_token}
```

**Response (200):**
```json
{
  "theme": "auto",
  "sound_enabled": true,
  "move_sound": true,
  "capture_sound": true,
  "check_sound": true,
  "notifications_enabled": true,
  "language": "en"
}
```

---

### 2. Update User Preferences
**Endpoint:** `POST /preferences/preferences/`

**Headers:**
```
Authorization: Bearer {access_token}
Content-Type: application/json
```

**Request:**
```json
{
  "theme": "dark",            // light, dark, auto
  "sound_enabled": false,
  "move_sound": true,
  "language": "en"
}
```

**Response (200):**
```json
{
  "message": "Preferences updated",
  "preferences": {
    "theme": "dark",
    "sound_enabled": false,
    "language": "en"
  }
}
```

---

## ‚ôüÔ∏è Chess Game Endpoints

### 1. Create Game
**Endpoint:** `POST /chess/games/create_game/`

**Headers:**
```
Authorization: Bearer {access_token}
```

**Request:**
```json
{
  "opponent_id": 2,
  "time_control": "blitz",
  "initial_time": 5,
  "is_ai": false,
  "ai_level": 1200
}
```

**Response (201):**
```json
{
  "message": "Game created",
  "game_id": 1,
  "room_code": "abc12345",
  "board_state": {
    "fen": "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
    "is_check": false,
    "is_checkmate": false,
    "turn": "white",
    "legal_moves": ["a2a3", "a2a4", "b2b3", "..."]
  }
}
```

---

### 2. Get Game State
**Endpoint:** `GET /chess/games/get_game/?game_id=1`

**Headers:**
```
Authorization: Bearer {access_token}
```

**Response (200):**
```json
{
  "game_id": 1,
  "status": "in_progress",
  "white_player": "player1",
  "black_player": "player2",
  "board_state": {
    "fen": "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
    "is_check": false,
    "turn": "white",
    "legal_moves": [...]
  },
  "move_history": [
    {
      "number": 1,
      "san": "e4",
      "uci": "e2e4"
    }
  ]
}
```

---

### 3. Make Move
**Endpoint:** `POST /chess/games/make_move/`

**Headers:**
```
Authorization: Bearer {access_token}
```

**Request:**
```json
{
  "game_id": 1,
  "move": "e2e4"  // UCI notation
}
```

**Response (200):**
```json
{
  "message": "Move made",
  "move": {
    "uci": "e2e4",
    "san": "e4",
    "piece": "P",
    "is_capture": false,
    "is_check": false,
    "is_checkmate": false
  },
  "board_state": {
    "fen": "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e3 0 1",
    "turn": "black",
    "legal_moves": [...]
  }
}
```

**Errors:**
- 400: Illegal move

---

### 4. Get Legal Moves
**Endpoint:** `GET /chess/games/legal_moves/?game_id=1&square=e2`

**Response (200):**
```json
{
  "moves": ["e2e3", "e2e4"],
  "turn": "white"
}
```

---

### 5. Get AI Move
**Endpoint:** `GET /chess/games/get_ai_move/?game_id=1&difficulty=1200`

**Response (200):**
```json
{
  "move": "e2e4",
  "difficulty": "1200"
}
```

---

### 6. Resign
**Endpoint:** `POST /chess/games/resign/`

**Request:**
```json
{
  "game_id": 1
}
```

**Response (200):**
```json
{
  "message": "Game resigned",
  "winner": "player2",
  "result": "0-1"
}
```

---

## Ì≥® Game Invitation Endpoints

### 1. Create Invitation
**Endpoint:** `POST /rooms/invitations/create_invitation/`

**Headers:**
```
Authorization: Bearer {access_token}
```

**Request:**
```json
{
  "invitee_id": 2,
  "time_control": "blitz",
  "message": "Let's play a quick game!"
}
```

**Response (201):**
```json
{
  "message": "Invitation created",
  "invitation_id": 1,
  "join_code": "ABC12345"
}
```

---

### 2. Get My Invitations
**Endpoint:** `GET /rooms/invitations/my_invitations/`

**Headers:**
```
Authorization: Bearer {access_token}
```

**Response (200):**
```json
{
  "invitations": [
    {
      "id": 1,
      "inviter": "player1",
      "inviter_id": 1,
      "time_control": "blitz",
      "message": "Let's play!",
      "join_code": "ABC12345",
      "created_at": "2026-03-12T10:30:00Z"
    }
  ]
}
```

---

### 3. Accept Invitation
**Endpoint:** `POST /rooms/invitations/accept_invitation/`

**Request:**
```json
{
  "invitation_id": 1
}
```

**Response (200):**
```json
{
  "message": "Invitation accepted",
  "game_id": 1,
  "room_code": "ABC12345"
}
```

---

### 4. Decline Invitation
**Endpoint:** `POST /rooms/invitations/decline_invitation/`

**Request:**
```json
{
  "invitation_id": 1
}
```

**Response (200):**
```json
{
  "message": "Invitation declined"
}
```

---

### 5. Join Game with Code
**Endpoint:** `GET /rooms/invitations/join_game/?code=ABC12345`

**Response (200):**
```json
{
  "game_id": 1,
  "room_code": "ABC12345",
  "status": "accepted"
}
```

---

## Ì≥π Video Call Endpoints

### 1. Initiate Call
**Endpoint:** `POST /rooms/calls/initiate_call/`

**Headers:**
```
Authorization: Bearer {access_token}
```

**Request:**
```json
{
  "receiver_id": 2,
  "game_match_id": 1  // optional
}
```

**Response (201):**
```json
{
  "message": "Call initiated",
  "session_id": "uuid-here",
  "call_id": 1
}
```

---

### 2. Answer Call
**Endpoint:** `POST /rooms/calls/answer_call/`

**Request:**
```json
{
  "session_id": "uuid-here",
  "answer_sdp": "v=0\no=..."  // WebRTC SDP answer
}
```

**Response (200):**
```json
{
  "message": "Call answered",
  "offer_sdp": "v=0\no=..."  // WebRTC SDP offer
}
```

---

### 3. Add ICE Candidate
**Endpoint:** `POST /rooms/calls/add_ice_candidate/`

**Request:**
```json
{
  "session_id": "uuid-here",
  "candidate": "candidate:...",
  "sdp_mline_index": 0
}
```

**Response (200):**
```json
{
  "message": "ICE candidate added"
}
```

---

### 4. End Call
**Endpoint:** `POST /rooms/calls/end_call/`

**Request:**
```json
{
  "session_id": "uuid-here"
}
```

**Response (200):**
```json
{
  "message": "Call ended",
  "duration": 300  // seconds
}
```

---

## Ì¥å WebSocket Connection

### Connect to Game Room
```
ws://localhost:8000/ws/chess/game/{room_id}/
wss://your-domain.com/ws/chess/game/{room_id}/  (production)
```

### Message Types

#### Send Move
```json
{
  "type": "make_move",
  "game_id": 1,
  "move": "e2e4"
}
```

#### Receive Move
```json
{
  "type": "move_made",
  "move": "e2e4",
  "player": "player1",
  "board_state": {...}
}
```

#### Request Draw
```json
{
  "type": "request_draw",
  "game_id": 1
}
```

#### Chat Message
```json
{
  "type": "chat_message",
  "message": "Good game!"
}
```

#### Resign
```json
{
  "type": "resign",
  "game_id": 1
}
```

---

## ‚úÖ Authentication

All protected endpoints require Bearer token in Authorization header:

```bash
Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGc...
```

Tokens are obtained from `/accounts/auth/verify_otp/` endpoint.

---

## Ì¥Ñ Error Responses

All errors follow this format:

```json
{
  "error": "Error message",
  "details": "Additional details if available"
}
```

**Common Status Codes:**
- 200: Success
- 201: Created
- 400: Bad Request
- 401: Unauthorized
- 403: Forbidden
- 404: Not Found
- 500: Server Error

---

## Ì≥± Flutter Integration Example

```dart
// Login with OTP
final response = await http.post(
  Uri.parse('http://localhost:8000/api/v1/accounts/auth/send_otp/'),
  headers: {'Content-Type': 'application/json'},
  body: jsonEncode({'email': 'user@example.com', 'purpose': 'login'}),
);

// Verify OTP
final verifyResponse = await http.post(
  Uri.parse('http://localhost:8000/api/v1/accounts/auth/verify_otp/'),
  headers: {'Content-Type': 'application/json'},
  body: jsonEncode({
    'email': 'user@example.com',
    'otp_code': '123456',
    'purpose': 'login',
  }),
);

// Store tokens
final tokens = jsonDecode(verifyResponse.body)['tokens'];
// Save tokens to secure storage

// Make API call with token
final gameResponse = await http.post(
  Uri.parse('http://localhost:8000/api/v1/chess/games/create_game/'),
  headers: {
    'Content-Type': 'application/json',
    'Authorization': 'Bearer ${tokens['access']}',
  },
  body: jsonEncode({'opponent_id': 2, 'time_control': 'blitz'}),
);
```

---

## Ì≥ö Additional Resources

- See `IMPLEMENTATION_GUIDE.md` for setup instructions
- See specific service files for implementation details
- Check models for database schema

Created: 2026-03-12
Last Updated: 2026-03-12
