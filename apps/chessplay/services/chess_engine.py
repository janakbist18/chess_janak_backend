"""
Chess engine logic service using python-chess library
Handles move validation, board state, and game logic
"""
import chess
import json
from typing import Dict, List, Tuple, Optional
from datetime import datetime


class ChessEngineService:
    """Service for handling chess game logic and moves"""
    
    def __init__(self, fen: str = chess.STARTING_FEN):
        """Initialize chess board with given FEN"""
        try:
            self.board = chess.Board(fen)
        except:
            self.board = chess.Board()
    
    def get_board_state(self) -> Dict:
        """Get current board state as dictionary"""
        return {
            "fen": self.board.fen(),
            "is_check": self.board.is_check(),
            "is_checkmate": self.board.is_checkmate(),
            "is_stalemate": self.board.is_stalemate(),
            "is_game_over": self.board.is_game_over(),
            "turn": "white" if self.board.turn else "black",
            "legal_moves": self.get_legal_moves(),
            "halfmove_clock": self.board.halfmove_clock,
            "fullmove_number": self.board.fullmove_number,
        }
    
    def get_legal_moves(self) -> List[str]:
        """Get list of legal moves in UCI notation"""
        return [move.uci() for move in self.board.legal_moves]
    
    def get_legal_moves_for_square(self, square: str) -> List[str]:
        """Get legal moves for a specific square"""
        try:
            sq = chess.parse_square(square)
            moves = [move.uci() for move in self.board.legal_moves if move.from_square == sq]
            return moves
        except:
            return []
    
    def make_move(self, uci_move: str) -> Tuple[bool, str, Dict]:
        """
        Make a move on the board
        Returns: (success, message, board_state)
        """
        try:
            move = chess.Move.from_uci(uci_move)
            
            if move not in self.board.legal_moves:
                return False, "Illegal move", self.get_board_state()
            
            # Get move details before making move
            piece = self.board.piece_at(move.from_square)
            capture = self.board.is_capture(move)
            
            # Make the move
            self.board.push(move)
            
            # Prepare move info
            move_info = {
                "uci": uci_move,
                "san": self.board.san(move),
                "piece": piece.symbol() if piece else None,
                "is_capture": capture,
                "is_check": self.board.is_check(),
                "is_checkmate": self.board.is_checkmate(),
                "is_stalemate": self.board.is_stalemate(),
            }
            
            return True, "Move made successfully", {
                **move_info,
                "board_state": self.get_board_state()
            }
        
        except Exception as e:
            return False, f"Error making move: {str(e)}", self.get_board_state()
    
    def unmake_move(self) -> Tuple[bool, Dict]:
        """Undo the last move"""
        try:
            if self.board.move_stack:
                self.board.pop()
                return True, self.get_board_state()
            return False, self.get_board_state()
        except Exception as e:
            return False, self.get_board_state()
    
    def is_valid_move(self, uci_move: str) -> bool:
        """Check if move is legal"""
        try:
            move = chess.Move.from_uci(uci_move)
            return move in self.board.legal_moves
        except:
            return False
    
    def get_game_result(self) -> Optional[Dict]:
        """Get game result if game is over"""
        if not self.board.is_game_over():
            return None
        
        result = None
        result_type = None
        
        if self.board.is_checkmate():
            result = "0-1" if self.board.turn else "1-0"
            result_type = "checkmate"
        elif self.board.is_stalemate():
            result = "1/2-1/2"
            result_type = "stalemate"
        elif self.board.is_insufficient_material():
            result = "1/2-1/2"
            result_type = "insufficient_material"
        elif self.board.is_seventyfive_moves():
            result = "1/2-1/2"
            result_type = "seventy_five_move_rule"
        elif self.board.is_fivefold_repetition():
            result = "1/2-1/2"
            result_type = "fivefold_repetition"
        
        return {
            "result": result,
            "result_type": result_type,
            "is_game_over": True
        }
    
    def get_pgn(self) -> str:
        """Get game in PGN format"""
        game = chess.pgn.GameNode()
        
        # Set headers
        game.headers["Event"] = "Online Chess Game"
        game.headers["Date"] = datetime.now().strftime("%Y.%m.%d")
        game.headers["Result"] = "*"
        
        # Add moves
        node = game
        for move in self.board.move_stack:
            node = node.add_variation(move)
        
        return str(game)
    
    def get_bitboard_state(self) -> Dict:
        """Get bitboard representation of position"""
        return {
            "white_pawns": self.board.occupied_co[chess.WHITE] & self.board.pawns,
            "white_knights": self.board.occupied_co[chess.WHITE] & self.board.knights,
            "white_bishops": self.board.occupied_co[chess.WHITE] & self.board.bishops,
            "white_rooks": self.board.occupied_co[chess.WHITE] & self.board.rooks,
            "white_queens": self.board.occupied_co[chess.WHITE] & self.board.queens,
            "white_king": self.board.occupied_co[chess.WHITE] & self.board.kings,
            "black_pawns": self.board.occupied_co[chess.BLACK] & self.board.pawns,
            "black_knights": self.board.occupied_co[chess.BLACK] & self.board.knights,
            "black_bishops": self.board.occupied_co[chess.BLACK] & self.board.bishops,
            "black_rooks": self.board.occupied_co[chess.BLACK] & self.board.rooks,
            "black_queens": self.board.occupied_co[chess.BLACK] & self.board.queens,
            "black_king": self.board.occupied_co[chess.BLACK] & self.board.kings,
        }
    
    def reset_board(self):
        """Reset board to starting position"""
        self.board = chess.Board()
    
    def load_fen(self, fen: str) -> bool:
        """Load position from FEN"""
        try:
            self.board = chess.Board(fen)
            return True
        except:
            return False
