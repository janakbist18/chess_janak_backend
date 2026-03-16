# Chess Game Backend - Complete Implementation Guide

## Overview
This guide covers all the newly implemented features for the chess game backend.

## ‚úÖ Features Implemented

### 1. **Complete Chess Engine Logic**
- **File**: `apps/chessplay/services/chess_engine.py`
- Full move validation using python-chess library
- FEN position tracking
- Legal move generation
- Check/checkmate/stalemate detection
- Game state management
- PGN generation

### 2. **AI Chess Engine (Stockfish)**
- **File**: `apps/chessplay/services/ai_engine.py`
- Configurable difficulty levels (ELO rating)
- Best move generation
- Position evaluation
- Mate detection
- Adaptive depth based on difficulty

### 3. **Email-based OTP Authentication**
- **File**: `apps/accounts/services/otp_service.py`
- Secure 6-digit OTP generation
- Email delivery via Gmail/SMTP
- OTP validation and expiration
- Purpose-based OTP (login, registration, email verify)
- Resend functionality
- Automatic cleanup of expired OTPs

### 4. **JWT Token Management**
- **File**: `apps/accounts/services/jwt_service.py`
- Access & refresh token generation
- Customizable token lifetime
- Token verification and validation
- User extraction from tokens
- Token refreshing

### 5. **User Preferences and Settings**
- **File**: `apps/accounts/models_preferences.py`
- `UserPreferences`: Theme (light/dark/auto), sounds, notifications
- `SoundSettings`: Custom sound URLs and volume control
- Privacy settings (online status, friend requests)
- Game preferences (coordinates, legal moves display)

### 6. **Game Invitations with Join Codes**
- **File**: `apps/rooms/models_invitations.py`
- `GameInvitation`: Invitation system with unique join codes
- Time control configuration (rapid, blitz, bullet, classical)
- Invitation status tracking (pending, accepted, declined, expired)
- Auto-expiring invitations (24 hours)
- Custom messages

### 7. **WebRTC Video/Audio Calls**
- **File**: `apps/rooms/models_invitations.py`
- `VideoCallSession`: Full call session management
- `ICECandidate`: WebRTC ICE candidate handling
- Session initiation and answer protocols
- Call duration tracking
- Integration with chess games

### 8. **API Endpoints**

#### Authentication (`apps/accounts/views_auth.py`)
```
POST   /api/auth/send_otp/           - Send OTP to email
POST   /api/auth/verify_otp/         - Verify OTP and login
POST   /api/auth/resend_otp/         - Resend OTP
POST   /api/auth/logout/             - Logout user
POST   /api/auth/refresh_token/      - Refresh access token
GET    /api/preferences/preferences/ - Get user preferences
POST   /api/preferences/preferences/ - Update preferences
```

#### Chess Game (`apps/chessplay/views_game.py`)
```
POST   /api/games/create_game/       - Create new game
GET    /api/games/get_game/          - Get game state
POST   /api/games/make_move/         - Make chess move
GET    /api/games/legal_moves/       - Get legal moves
GET    /api/games/get_ai_move/       - Get AI move
POST   /api/games/resign/            - Resign from game
```

#### Invitations (`apps/rooms/views_invitations.py`)
```
POST   /api/invitations/create_invitation/  - Create invitation
GET    /api/invitations/my_invitations/     - Get pending invitations
POST   /api/invitations/accept_invitation/  - Accept invitation
POST   /api/invitations/decline_invitation/ - Decline invitation
GET    /api/invitations/join_game/         - Join with code
```

#### Video Calls (`apps/rooms/views_invitations.py`)
```
POST   /api/calls/initiate_call/     - Start video call
POST   /api/calls/answer_call/       - Answer incoming call
POST   /api/calls/add_ice_candidate/ - Add WebRTC ICE candidate
POST   /api/calls/end_call/          - End video call
```

### 9. **WebSocket Consumer for Real-time Games**
- **File**: `apps/chessplay/consumers_game.py`
- Real-time move synchronization across players
- Player presence tracking (joined/left)
- Draw offers and resignations
- In-game chat messaging
- Game state broadcasting

## Ì∫Ä Setup Instructions

### 1. Install Dependencies
```bash
cd /c/Users/ACER/OneDrive/Desktop/chess_janak_backend/chess_janak_backend
pip install -r requirements.txt
```

### 2. Database Migrations

Add models to your `apps/accounts/models.py` and `apps/rooms/models.py`:

```bash
python manage.py makemigrations accounts rooms chessplay
python manage.py migrate
```

### 3. Configure Settings

Update `config/settings/base.py`:

```python
# Email Configuration
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = 'your-email@gmail.com'
EMAIL_HOST_PASSWORD = 'your-app-password'
DEFAULT_FROM_EMAIL = 'your-email@gmail.com'

# Channels Configuration
ASGI_APPLICATION = 'config.asgi.application'

CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels_redis.core.RedisChannelLayer',
        'CONFIG': {
            "hosts": [('127.0.0.1', 6379)],
        },
    }
}

# WebSocket Routing
WEBSOCKET_ACCEPT_ALL = True
```

### 4. Update URL Configuration

In `config/urls.py`:

```python
from django.urls import path, include

urlpatterns = [
    # ... existing patterns ...
    path('api/v1/', include([
        path('accounts/', include('apps.accounts.urls_auth')),
        path('chess/', include('apps.chessplay.urls_game')),
        path('rooms/', include('apps.rooms.urls_invitations')),
    ])),
]
```

### 5. Create __init__.py files for services (if needed)

```bash
touch apps/accounts/services/__init__.py
touch apps/chessplay/services/__init__.py
```

### 6. Configure WebSocket Routing

In `config/routing.py`:

```python
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from django.urls import re_path
from apps.chessplay.consumers_game import ChessGameConsumer

websocket_urlpatterns = [
    re_path(r'ws/chess/game/(?P<room_id>\w+)/$', ChessGameConsumer.as_asgi()),
]

application = ProtocolTypeRouter({
    'websocket': AuthMiddlewareStack(
        URLRouter(websocket_urlpatterns)
    ),
})
```

## Ì≥± Flutter App Integration

### Authentication Flow
```
1. User enters email
2. Backend sends OTP via Gmail
3. User enters OTP
4. Backend verifies and returns JWT tokens
5. Flutter stores tokens securely
6. Use access token for subsequent API calls
```

### Game Flow
```
1. Create invitation with game settings
2. Opponent accepts invitation
3. WebSocket connection established
4. Real-time moves synchronized
5. Optional: Initiate video/audio call
6. Game ends with result
```

### WebRTC Setup for Video Calls
```
1. POST /api/calls/initiate_call/ - Get session_id
2. Create WebRTC PeerConnection in Flutter
3. POST /api/calls/answer_call/ - Exchange SDP
4. POST /api/calls/add_ice_candidate/ - Add ICE candidates
5. WebRTC connection established
6. Audio/Video streaming
7. POST /api/calls/end_call/ - End session
```

## Ì¥å API Usage Examples

### Register with OTP
```bash
# Send OTP
curl -X POST http://localhost:8000/api/v1/accounts/auth/send_otp/ \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "purpose": "registration"}'

# Verify OTP and register
curl -X POST http://localhost:8000/api/v1/accounts/auth/verify_otp/ \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "otp_code": "123456",
    "username": "username",
    "name": "User Name",
    "purpose": "registration"
  }'
```

### Create and Play Game
```bash
# Create game
curl -X POST http://localhost:8000/api/v1/chess/games/create_game/ \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{"opponent_id": 2, "time_control": "blitz"}'

# Make move
curl -X POST http://localhost:8000/api/v1/chess/games/make_move/ \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{"game_id": 1, "move": "e2e4"}'
```

### Send Game Invitation
```bash
curl -X POST http://localhost:8000/api/v1/rooms/invitations/create_invitation/ \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "invitee_id": 2,
    "time_control": "blitz",
    "message": "Let's play!"
  }'
```

## Ìæµ Sound and Theme Features

Users can customize:
- **Theme**: Light, Dark, or Auto (system preference)
- **Move sounds**: Move, capture, check, victory, defeat
- **Sound volume**: 0-100 range
- **Notifications**: Email and push notifications
- **Game display**: Show/hide coordinates, legal moves, last move

## Ì¥í Security Features

- OTP-based authentication (no passwords stored for this flow)
- JWT tokens with configurable expiration
- User verification before sensitive operations
- Permission checks on all protected endpoints
- WebSocket authentication via token
- Rate limiting recommended for OTP endpoints

## Ì≥ä Database Models

### New Models Included:
- EmailOTP - OTP records for authentication
- UserPreferences - User theme and notification settings
- SoundSettings - Custom sound configurations
- GameInvitation - Game invitations with join codes
- VideoCallSession - WebRTC call sessions
- ICECandidate - WebRTC connectivity information

## Ì∞õ Debugging

### Check OTP email delivery:
```python
python manage.py shell
from apps.accounts.services.otp_service import OTPService
OTPService.send_otp_email('test@example.com')
```

### Test chess engine:
```python
from apps.chessplay.services.chess_engine import ChessEngineService
engine = ChessEngineService()
print(engine.get_board_state())
```

### Test AI engine:
```python
from apps.chessplay.services.ai_engine import AIEngineService
ai = AIEngineService(elo_rating=1600)
move = ai.get_best_move('rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1')
```

## Ì¥Ñ Next Steps

1. Migrate all new models
2. Configure email settings in .env
3. Test OTP flow locally
4. Test chess move validation
5. Configure Redis for Channels
6. Test WebSocket connections
7. Integrate Flutter frontend
8. Deploy to production

## Ì≥ù Notes

- Stockfish engine requires 64-bit system
- Redis required for production WebSocket support
- Email configuration must be set for OTP delivery
- Make migrations before running tests
- Test WebRTC in HTTPS environment only

---
Created: 2026-03-12
Updated: 2026-03-12
