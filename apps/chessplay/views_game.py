"""
Chess game API views for moves, board state, and game logic
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
import uuid

from apps.chessplay.models import ChessMatch, ChessMove
from apps.chessplay.services.chess_engine import ChessEngineService
from apps.chessplay.services.ai_engine import AIEngineService
from apps.rooms.models import GameRoom


class ChessGameViewSet(viewsets.ViewSet):
    """Chess game endpoints"""
    
    permission_classes = [IsAuthenticated]
    
    @action(detail=False, methods=["post"])
    def create_game(self, request):
        """Create a new chess game"""
        opponent_id = request.data.get('opponent_id')
        time_control = request.data.get('time_control', 'blitz')
        initial_time = request.data.get('initial_time', 5)  # minutes
        is_ai = request.data.get('is_ai', False)
        ai_level = request.data.get('ai_level', 1200)  # ELO rating
        
        try:
            # Create game room
            room = GameRoom.objects.create(
                room_code=str(uuid.uuid4())[:8],
                created_by=request.user,
            )
            
            # Create chess match
            match = ChessMatch.objects.create(
                room=room,
                white_player=request.user,
                status=ChessMatch.STATUS_WAITING,
            )
            
            if not is_ai:
                # Multiplayer game
                if opponent_id:
                    from apps.accounts.models import User
                    opponent = User.objects.get(id=opponent_id)
                    match.black_player = opponent
                    match.save()
            else:
                # AI game
                match.black_player = None  # AI has no user account
                match.save()
                request.ai_level = ai_level
            
            return Response(
                {
                    "message": "Game created",
                    "game_id": match.id,
                    "room_code": room.room_code,
                    "board_state": ChessEngineService().get_board_state(),
                },
                status=status.HTTP_201_CREATED
            )
        
        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=False, methods=["get"])
    def get_game(self, request):
        """Get current game state"""
        game_id = request.query_params.get('game_id')
        
        if not game_id:
            return Response({"error": "game_id required"}, status=400)
        
        try:
            match = ChessMatch.objects.get(id=game_id)
            engine = ChessEngineService(match.current_fen)
            
            return Response({
                "game_id": match.id,
                "status": match.status,
                "white_player": match.white_player.username if match.white_player else "AI",
                "black_player": match.black_player.username if match.black_player else "AI",
                "board_state": engine.get_board_state(),
                "move_history": [
                    {
                        "number": m.move_number,
                        "san": m.san,
                        "uci": m.uci,
                    }
                    for m in match.moves.all()
                ],
            })
        except ChessMatch.DoesNotExist:
            return Response({"error": "Game not found"}, status=404)
    
    @action(detail=False, methods=["post"])
    def make_move(self, request):
        """Make a move in the game"""
        game_id = request.data.get('game_id')
        uci_move = request.data.get('move')  # e.g., "e2e4"
        
        if not game_id or not uci_move:
            return Response(
                {"error": "game_id and move are required"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            match = ChessMatch.objects.get(id=game_id)
            
            # Initialize chess engine with current board state
            engine = ChessEngineService(match.current_fen)
            
            # Validate and make move
            success, message, move_info = engine.make_move(uci_move)
            
            if not success:
                return Response(
                    {"error": message},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Save move to database
            move = ChessMove.objects.create(
                match=match,
                move_number=len(match.moves.all()) + 1,
                player=request.user,
                side=ChessMove.SIDE_WHITE if match.white_player == request.user else ChessMove.SIDE_BLACK,
                from_square=uci_move[:2],
                to_square=uci_move[2:4],
                uci=uci_move,
                san=move_info.get('san', ''),
                fen_after=move_info['board_state']['fen'],
                is_capture=move_info.get('is_capture', False),
                is_check=move_info['board_state']['is_check'],
            )
            
            # Update match state
            match.current_fen = move_info['board_state']['fen']
            match.is_check = move_info['board_state']['is_check']
            match.is_checkmate = move_info['board_state']['is_checkmate']
            match.is_stalemate = move_info['board_state']['is_stalemate']
            
            # Check game end
            if match.is_checkmate:
                winner = match.white_player if match.white_player == request.user else match.black_player
                match.winner = winner
                match.status = ChessMatch.STATUS_FINISHED
                match.result_type = ChessMatch.RESULT_CHECKMATE
                match.result = ChessMatch.RESULT_WHITE_WIN if winner == match.white_player else ChessMatch.RESULT_BLACK_WIN
                match.ended_at = timezone.now()
            
            match.save()
            
            return Response(
                {
                    "message": "Move made",
                    "move": move_info,
                    "board_state": move_info['board_state'],
                },
                status=status.HTTP_200_OK
            )
        
        except ChessMatch.DoesNotExist:
            return Response({"error": "Game not found"}, status=404)
        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=False, methods=["get"])
    def legal_moves(self, request):
        """Get legal moves for current position"""
        game_id = request.query_params.get('game_id')
        square = request.query_params.get('square')  # optional, for specific square
        
        if not game_id:
            return Response({"error": "game_id required"}, status=400)
        
        try:
            match = ChessMatch.objects.get(id=game_id)
            engine = ChessEngineService(match.current_fen)
            
            if square:
                moves = engine.get_legal_moves_for_square(square)
            else:
                moves = engine.get_legal_moves()
            
            return Response({
                "moves": moves,
                "turn": engine.get_board_state()['turn'],
            })
        except ChessMatch.DoesNotExist:
            return Response({"error": "Game not found"}, status=404)
    
    @action(detail=False, methods=["get"])
    def get_ai_move(self, request):
        """Get AI engine move"""
        game_id = request.query_params.get('game_id')
        difficulty = request.query_params.get('difficulty', '1200')  # ELO rating
        
        if not game_id:
            return Response({"error": "game_id required"}, status=400)
        
        try:
            match = ChessMatch.objects.get(id=game_id)
            ai = AIEngineService(elo_rating=int(difficulty))
            
            best_move = ai.get_best_move(match.current_fen)
            
            if not best_move:
                return Response(
                    {"error": "Could not generate AI move"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            return Response({
                "move": best_move,
                "difficulty": difficulty,
            })
        
        except ChessMatch.DoesNotExist:
            return Response({"error": "Game not found"}, status=404)
        except Exception as e:
            return Response({"error": str(e)}, status=400)
    
    @action(detail=False, methods=["post"])
    def resign(self, request):
        """Resign from the game"""
        game_id = request.data.get('game_id')
        
        if not game_id:
            return Response({"error": "game_id required"}, status=400)
        
        try:
            match = ChessMatch.objects.get(id=game_id)
            
            # Determine winner (opponent)
            if match.white_player == request.user:
                match.winner = match.black_player
                match.result = ChessMatch.RESULT_BLACK_WIN
            else:
                match.winner = match.white_player
                match.result = ChessMatch.RESULT_WHITE_WIN
            
            match.status = ChessMatch.STATUS_FINISHED
            match.result_type = ChessMatch.RESULT_RESIGNATION
            match.ended_at = timezone.now()
            match.save()
            
            return Response({
                "message": "Game resigned",
                "winner": match.winner.username if match.winner else "Draw",
                "result": match.result,
            })
        
        except ChessMatch.DoesNotExist:
            return Response({"error": "Game not found"}, status=404)
