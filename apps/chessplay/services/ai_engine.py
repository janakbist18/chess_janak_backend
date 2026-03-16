"""
Stockfish AI engine service for playing against computer
"""
import chess
from typing import Optional, Dict, Tuple
from stockfish import Stockfish


class AIEngineService:
    """Service for handling AI moves using Stockfish"""
    
    def __init__(self, elo_rating: int = 1200, threads: int = 1):
        """Initialize AI engine with given difficulty"""
        self.elo_rating = elo_rating
        self.threads = threads
        self.depth = self._calculate_depth(elo_rating)
        self.stockfish = self._initialize_engine()
    
    def _calculate_depth(self, elo_rating: int) -> int:
        """Calculate engine depth based on ELO rating"""
        if elo_rating < 1000:
            return 6
        elif elo_rating < 1500:
            return 10
        elif elo_rating < 2000:
            return 15
        else:
            return 20
    
    def _initialize_engine(self) -> Optional[Stockfish]:
        """Initialize Stockfish engine"""
        try:
            params = {
                "Threads": self.threads,
                "Hash": 256,
                "UCI_EloRating": self.elo_rating,
            }
            engine = Stockfish()
            for param, value in params.items():
                engine.update_engine_parameters(param, value)
            return engine
        except Exception as e:
            print(f"Error initializing Stockfish: {e}")
            return None
    
    def get_best_move(self, fen: str, time_limit: int = 500) -> Optional[str]:
        """Get best move from current position"""
        if not self.stockfish:
            return None
        
        try:
            self.stockfish.set_fen_position(fen)
            best_move = self.stockfish.get_best_move_time(time_limit)
            return best_move
        except Exception as e:
            print(f"Error getting best move: {e}")
            return None
    
    def get_move_with_evaluation(self, fen: str, time_limit: int = 500) -> Dict:
        """Get best move with evaluation score"""
        if not self.stockfish:
            return {"move": None, "evaluation": None}
        
        try:
            self.stockfish.set_fen_position(fen)
            best_move = self.stockfish.get_best_move_time(time_limit)
            evaluation = self.stockfish.get_evaluation()
            
            return {
                "move": best_move,
                "evaluation": evaluation,
            }
        except Exception as e:
            print(f"Error: {e}")
            return {"move": None, "evaluation": None}
    
    def get_top_moves(self, fen: str, count: int = 5, time_limit: int = 500) -> list:
        """Get top N best moves"""
        if not self.stockfish:
            return []
        
        try:
            self.stockfish.set_fen_position(fen)
            # Note: Stockfish doesn't have direct top moves API, so we simulate
            moves = []
            for _ in range(min(count, 5)):
                move = self.stockfish.get_best_move_time(time_limit // count)
                if move:
                    moves.append(move)
            return moves
        except Exception as e:
            print(f"Error: {e}")
            return []
    
    def evaluate_position(self, fen: str) -> Dict:
        """Evaluate current position"""
        if not self.stockfish:
            return {"evaluation": None, "status": "Engine not available"}
        
        try:
            self.stockfish.set_fen_position(fen)
            evaluation = self.stockfish.get_evaluation()
            return {
                "evaluation": evaluation,
                "elo_rating": self.elo_rating,
            }
        except Exception as e:
            return {"evaluation": None, "error": str(e)}
    
    def is_mate_in(self, fen: str, moves: int = 3) -> Tuple[bool, Optional[int]]:
        """Check if there's a forced mate in N moves"""
        if not self.stockfish:
            return False, None
        
        try:
            self.stockfish.set_fen_position(fen)
            evaluation = self.stockfish.get_evaluation()
            
            if evaluation.get("type") == "cp":
                return False, None
            
            if evaluation.get("type") == "mate":
                mate_moves = evaluation.get("value")
                if mate_moves and abs(mate_moves) <= moves:
                    return True, mate_moves
            
            return False, None
        except Exception as e:
            print(f"Error: {e}")
            return False, None
    
    def shutdown(self):
        """Shutdown engine"""
        if self.stockfish:
            self.stockfish.quit()
