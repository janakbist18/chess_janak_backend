"""
WebSocket consumers for real-time chess game
"""
import json
import asyncio
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.utils import timezone

from apps.chessplay.models import ChessMatch, ChessMove
from apps.chessplay.services.chess_engine import ChessEngineService
from apps.accounts.models import User


class ChessGameConsumer(AsyncWebsocketConsumer):
    """WebSocket consumer for chess game real-time communication"""
    
    async def connect(self):
        """Handle WebSocket connection"""
        self.room_id = self.scope['url_route']['kwargs']['room_id']
        self.room_group_name = f'chess_game_{self.room_id}'
        self.user = self.scope["user"]
        
        # Join room group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        
        await self.accept()
        
        # Notify others that player joined
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'player_joined',
                'player': self.user.username,
                'user_id': self.user.id,
            }
        )
    
    async def disconnect(self, close_code):
        """Handle WebSocket disconnect"""
        # Leave room group
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )
        
        # Notify others player left
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'player_left',
                'player': self.user.username,
                'user_id': self.user.id,
            }
        )
    
    async def receive(self, text_data):
        """Receive message from WebSocket"""
        try:
            data = json.loads(text_data)
            message_type = data.get('type')
            
            if message_type == 'make_move':
                await self.handle_move(data)
            
            elif message_type == 'request_draw':
                await self.handle_draw_request(data)
            
            elif message_type == 'resign':
                await self.handle_resign(data)
            
            elif message_type == 'chat_message':
                await self.handle_chat(data)
                
            elif message_type == 'game_state_request':
                await self.handle_game_state_request(data)
        
        except json.JSONDecodeError:
            await self.send(json.dumps({
                'type': 'error',
                'message': 'Invalid JSON'
            }))
    
    async def handle_move(self, data):
        """Handle chess move"""
        game_id = data.get('game_id')
        move = data.get('move')
        
        match = await self.get_match(game_id)
        if not match:
            await self.send(json.dumps({
                'type': 'error',
                'message': 'Game not found'
            }))
            return
        
        # Validate move
        engine = ChessEngineService(match.current_fen)
        success, message, move_info = engine.make_move(move)
        
        if not success:
            await self.send(json.dumps({
                'type': 'error',
                'message': f'Invalid move: {message}'
            }))
            return
        
        # Save move to database
        await self.save_move(match, move, move_info)
        
        # Update match
        await self.update_match_state(match, move_info)
        
        # Broadcast move to all players in room
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'move_made',
                'move': move,
                'from_square': move[:2],
                'to_square': move[2:4],
                'player': self.user.username,
                'board_state': move_info['board_state'],
                'game_id': game_id,
            }
        )
    
    async def handle_draw_request(self, data):
        """Handle draw offer"""
        game_id = data.get('game_id')
        
        match = await self.get_match(game_id)
        if not match:
            return
        
        # Update match
        await self.update_match_draw_offer(match, self.user.id)
        
        # Broadcast draw request
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'draw_offered',
                'player': self.user.username,
                'game_id': game_id,
            }
        )
    
    async def handle_resign(self, data):
        """Handle resignation"""
        game_id = data.get('game_id')
        
        match = await self.get_match(game_id)
        if not match:
            return
        
        # Determine loser and winner
        winner_id = match.black_player_id if match.white_player_id == self.user.id else match.white_player_id
        
        await self.update_match_resign(match, winner_id)
        
        # Broadcast resignation
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'game_resigned',
                'resigner': self.user.username,
                'game_id': game_id,
            }
        )
    
    async def handle_chat(self, data):
        """Handle chat message"""
        message = data.get('message')
        
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'chat_message_send',
                'player': self.user.username,
                'message': message,
                'timestamp': str(timezone.now()),
            }
        )
    
    async def handle_game_state_request(self, data):
        """Handle game state request"""
        game_id = data.get('game_id')
        match = await self.get_match(game_id)
        
        if not match:
            return
        
        engine = ChessEngineService(match.current_fen)
        
        await self.send(json.dumps({
            'type': 'game_state',
            'board_state': engine.get_board_state(),
            'moves': await self.get_match_moves(match),
        }))
    
    # Group message handlers
    async def player_joined(self, event):
        """Send player joined message"""
        await self.send(json.dumps({
            'type': 'player_joined',
            'player': event['player'],
            'user_id': event['user_id'],
        }))
    
    async def player_left(self, event):
        """Send player left message"""
        await self.send(json.dumps({
            'type': 'player_left',
            'player': event['player'],
        }))
    
    async def move_made(self, event):
        """Send move made message"""
        await self.send(json.dumps({
            'type': 'move_made',
            'move': event['move'],
            'player': event['player'],
            'board_state': event['board_state'],
        }))
    
    async def draw_offered(self, event):
        """Send draw offer message"""
        await self.send(json.dumps({
            'type': 'draw_offered',
            'player': event['player'],
        }))
    
    async def game_resigned(self, event):
        """Send resignation message"""
        await self.send(json.dumps({
            'type': 'game_resigned',
            'resigner': event['resigner'],
        }))
    
    async def chat_message_send(self, event):
        """Send chat message to WebSocket"""
        await self.send(json.dumps({
            'type': 'chat_message',
            'player': event['player'],
            'message': event['message'],
            'timestamp': event['timestamp'],
        }))
    
    # Database operations
    @database_sync_to_async
    def get_match(self, game_id):
        """Get ChessMatch from database"""
        try:
            return ChessMatch.objects.get(id=game_id)
        except ChessMatch.DoesNotExist:
            return None
    
    @database_sync_to_async
    def save_move(self, match, uci_move, move_info):
        """Save move to database"""
        from apps.chessplay.services.chess_engine import ChessEngineService
        engine = ChessEngineService(match.current_fen)
        
        move_number = match.moves.count() + 1
        
        ChessMove.objects.create(
            match=match,
            move_number=move_number,
            player=self.user,
            side='white' if self.user == match.white_player else 'black',
            from_square=uci_move[:2],
            to_square=uci_move[2:4],
            uci=uci_move,
            san=move_info.get('san', ''),
            fen_after=move_info['board_state']['fen'],
            is_capture=move_info.get('is_capture', False),
            is_check=move_info['board_state']['is_check'],
        )
    
    @database_sync_to_async
    def update_match_state(self, match, move_info):
        """Update match state"""
        match.current_fen = move_info['board_state']['fen']
        match.is_check = move_info['board_state']['is_check']
        match.is_checkmate = move_info['board_state']['is_checkmate']
        match.is_stalemate = move_info['board_state']['is_stalemate']
        match.save()
    
    @database_sync_to_async
    def update_match_draw_offer(self, match, user_id):
        """Update match with draw offer"""
        match.draw_offered_by_id = user_id
        match.save()
    
    @database_sync_to_async
    def update_match_resign(self, match, winner_id):
        """Update match with resignation"""
        match.status = ChessMatch.STATUS_FINISHED
        match.winner_id = winner_id
        match.result_type = ChessMatch.RESULT_RESIGNATION
        match.ended_at = timezone.now()
        match.save()
    
    @database_sync_to_async
    def get_match_moves(self, match):
        """Get all moves for match"""
        moves = match.moves.all().order_by('move_number')
        return [
            {
                'number': m.move_number,
                'san': m.san,
                'uci': m.uci,
                'player': m.player.username,
            }
            for m in moves
        ]
