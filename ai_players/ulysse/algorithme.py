# ai_players/ulysse/algorithme.py
# -------------------------------------------------------------------
# Implémentation d'un algorithme MinMax avec élagage Alpha-Beta
# pour le jeu Quantik
# -------------------------------------------------------------------
from typing import Optional, Tuple, List, Dict
from core.ai_base import AIBase
from core.types import Shape, Player, Piece
from core.rules import QuantikBoard, zone_index
import math
import time
from collections import defaultdict

AI_NAME = "Ulysse – Optimized MinMax Alpha-Beta"
AI_AUTHOR = "Ulysse"
AI_VERSION = "2.0"

class QuantikAI(AIBase):
    def __init__(self, player: Player):
        super().__init__(player)
        self.opponent = Player.PLAYER1 if player == Player.PLAYER2 else Player.PLAYER2
        self.max_depth = 6
        self.transposition_table: Dict[str, Tuple[float, int, int]] = {}
        self.killer_moves: List[List[Optional[Tuple[int, int, Shape]]]] = [[None, None] for _ in range(15)]
        self.history_table: Dict[Tuple[int, int, Shape], int] = defaultdict(int)
        self.nodes_searched = 0
        self.max_time = 1.5
        self.position_cache = {}
    
    def get_move(self, board, pieces_count) -> Optional[Tuple[int, int, Shape]]:
        game_board = QuantikBoard()
        game_board.board = [row[:] for row in board]
        
        self.clear_tables()
        
        total_pieces = sum(sum(pieces_count[player].values()) for player in pieces_count)
        if total_pieces > 14:
            opening_move = self.get_opening_move(game_board, pieces_count)
            if opening_move:
                return opening_move
        
        start_time = time.time()
        self.nodes_searched = 0
        
        best_move = None
        for depth in range(1, min(self.max_depth + 1, 16)):
            if time.time() - start_time > self.max_time:
                break
            
            time_left = self.max_time - (time.time() - start_time)
            if time_left < 0.1:  # Less than 100ms left
                break
                
            try:
                score, move = self.minimax(game_board, pieces_count, depth, -math.inf, math.inf, True, start_time)
                if move:
                    best_move = move
                    if abs(score) > 900:  # Found winning/losing move
                        break
            except TimeoutError:
                break
        
        return best_move
    
    def get_opening_move(self, board: QuantikBoard, pieces_count) -> Optional[Tuple[int, int, Shape]]:
        empty_squares = sum(1 for row in board.board for cell in row if cell is None)
        
        if empty_squares == 16:
            return (1, 1, Shape.CIRCLE)
        
        if empty_squares >= 14:
            center_moves = [(1, 1), (1, 2), (2, 1), (2, 2)]
            for row, col in center_moves:
                if board.board[row][col] is None:
                    for shape in [Shape.CIRCLE, Shape.SQUARE, Shape.TRIANGLE, Shape.DIAMOND]:
                        if pieces_count[self.me][shape] > 0:
                            piece = Piece(shape, self.me)
                            if board.is_valid_move(row, col, piece):
                                return (row, col, shape)
        
        return None
    
    def minimax(self, board: QuantikBoard, pieces_count, depth: int, alpha: float, beta: float, maximizing: bool, start_time: float) -> Tuple[float, Optional[Tuple[int, int, Shape]]]:
        if time.time() - start_time > self.max_time:
            raise TimeoutError()
        
        self.nodes_searched += 1
        
        board_key = self.get_board_key(board, pieces_count, maximizing)
        if board_key in self.transposition_table:
            stored_score, stored_depth, flag = self.transposition_table[board_key]
            if stored_depth >= depth:
                if flag == 0 or (flag == 1 and stored_score <= alpha) or (flag == -1 and stored_score >= beta):
                    return stored_score, None
        
        victory = board.check_victory()
        if depth == 0 or victory:
            if victory:
                score = 1000.0 if self.is_winning_for_me(board) else -1000.0
            else:
                score = self.evaluate(board, pieces_count)
            self.transposition_table[board_key] = (score, depth, 0)
            return score, None
        
        if not self.has_moves(board, pieces_count):
            return 0, None
        
        best_move = None
        current_player = self.me if maximizing else self.opponent
        moves = self.get_ordered_moves(board, current_player, pieces_count, depth)
        
        if maximizing:
            max_eval = -math.inf
            
            for move in moves:
                row, col, shape = move
                
                old_piece = board.board[row][col]
                piece = Piece(shape, current_player)
                board.place_piece(row, col, piece)
                pieces_count[current_player][shape] -= 1
                
                eval_score, _ = self.minimax(board, pieces_count, depth - 1, alpha, beta, False, start_time)
                
                board.board[row][col] = old_piece
                pieces_count[current_player][shape] += 1
                
                if eval_score > max_eval:
                    max_eval = eval_score
                    best_move = move
                
                alpha = max(alpha, eval_score)
                if beta <= alpha:
                    if depth < len(self.killer_moves) and move not in self.killer_moves[depth]:
                        self.killer_moves[depth][1] = self.killer_moves[depth][0]
                        self.killer_moves[depth][0] = move
                    self.history_table[move] += depth * depth
                    break
            
            flag = 0 if alpha < max_eval < beta else (1 if max_eval <= alpha else -1)
            self.transposition_table[board_key] = (max_eval, depth, flag)
            return max_eval, best_move
        
        else:
            min_eval = math.inf
            
            for move in moves:
                row, col, shape = move
                
                old_piece = board.board[row][col]
                piece = Piece(shape, current_player)
                board.place_piece(row, col, piece)
                pieces_count[current_player][shape] -= 1
                
                eval_score, _ = self.minimax(board, pieces_count, depth - 1, alpha, beta, True, start_time)
                
                board.board[row][col] = old_piece
                pieces_count[current_player][shape] += 1
                
                if eval_score < min_eval:
                    min_eval = eval_score
                    best_move = move
                
                beta = min(beta, eval_score)
                if beta <= alpha:
                    if depth < len(self.killer_moves) and move not in self.killer_moves[depth]:
                        self.killer_moves[depth][1] = self.killer_moves[depth][0]
                        self.killer_moves[depth][0] = move
                    self.history_table[move] += depth * depth
                    break
            
            flag = 0 if alpha < min_eval < beta else (-1 if min_eval >= beta else 1)
            self.transposition_table[board_key] = (min_eval, depth, flag)
            return min_eval, best_move
    
    def get_possible_moves(self, board: QuantikBoard, player: Player, pieces_count) -> List[Tuple[int, int, Shape]]:
        moves = []
        for shape in Shape:
            if pieces_count[player][shape] > 0:
                for row in range(4):
                    for col in range(4):
                        if board.board[row][col] is None:
                            piece = Piece(shape, player)
                            if board.is_valid_move(row, col, piece):
                                moves.append((row, col, shape))
        return moves
    
    def get_ordered_moves(self, board: QuantikBoard, player: Player, pieces_count, depth: int) -> List[Tuple[int, int, Shape]]:
        moves = self.get_possible_moves(board, player, pieces_count)
        
        def move_priority(move):
            row, col, shape = move
            priority = 0
            
            if move in self.killer_moves[depth]:
                priority += 10000
            
            priority += self.history_table.get(move, 0)
            
            center_bonus = 0
            if (row, col) in [(1,1), (1,2), (2,1), (2,2)]:
                center_bonus = 50
            elif (row, col) in [(0,1), (0,2), (1,0), (1,3), (2,0), (2,3), (3,1), (3,2)]:
                center_bonus = 20
            priority += center_bonus
            
            old_piece = board.board[row][col]
            piece = Piece(shape, player)
            board.place_piece(row, col, piece)
            
            if board.check_victory():
                priority += 100000
            else:
                winning_lines = self.count_potential_wins(board, player, row, col)
                priority += winning_lines * 100
            
            board.board[row][col] = old_piece
            return -priority
        
        return sorted(moves, key=move_priority)
    
    def count_potential_wins(self, board: QuantikBoard, player: Player, row: int, col: int) -> int:
        count = 0
        
        line = [board.board[row][c] for c in range(4)]
        if self.can_complete_line(line, player):
            count += 1
        
        column = [board.board[r][col] for r in range(4)]
        if self.can_complete_line(column, player):
            count += 1
        
        zone_idx = zone_index(row, col)
        zones = [
            [(0,0), (0,1), (1,0), (1,1)],
            [(0,2), (0,3), (1,2), (1,3)],
            [(2,0), (2,1), (3,0), (3,1)],
            [(2,2), (2,3), (3,2), (3,3)]
        ]
        zone = [board.board[r][c] for (r, c) in zones[zone_idx]]
        if self.can_complete_line(zone, player):
            count += 1
            
        return count
    
    def can_complete_line(self, pieces: List[Optional[Piece]], player: Player) -> bool:
        my_pieces = [p for p in pieces if p is not None and p.player == player]
        opponent_pieces = [p for p in pieces if p is not None and p.player != player]
        
        if opponent_pieces:
            return False
        
        my_shapes = {p.shape for p in my_pieces}
        empty_count = sum(1 for p in pieces if p is None)
        
        return len(my_shapes) + empty_count == 4 and len(my_shapes) == len(my_pieces)
    
    def get_board_key(self, board: QuantikBoard, pieces_count, maximizing: bool) -> str:
        board_str = ''.join(''.join(f'{p.shape.value}{p.player.value}' if p else '0' for p in row) for row in board.board)
        pieces_str = ''.join(f'{player.value}:{sum(pieces_count[player].values())}' for player in [self.me, self.opponent])
        return f'{board_str}:{pieces_str}:{maximizing}'
    
    def has_moves(self, board: QuantikBoard, pieces_count) -> bool:
        """
        Vérifie si le joueur actuel a des coups possibles
        """
        return len(self.get_possible_moves(board, self.me, pieces_count)) > 0 or \
               len(self.get_possible_moves(board, self.opponent, pieces_count)) > 0
    
    def evaluate(self, board: QuantikBoard, pieces_count=None) -> float:
        score = 0
        my_threats = 0
        opponent_threats = 0
        
        # Évaluation rapide des lignes, colonnes et zones
        all_lines = [
            [board.board[r][c] for c in range(4)] for r in range(4)  # lignes
        ] + [
            [board.board[r][c] for r in range(4)] for c in range(4)  # colonnes  
        ] + [
            [board.board[r][c] for (r, c) in [(0,0), (0,1), (1,0), (1,1)]],
            [board.board[r][c] for (r, c) in [(0,2), (0,3), (1,2), (1,3)]],
            [board.board[r][c] for (r, c) in [(2,0), (2,1), (3,0), (3,1)]],
            [board.board[r][c] for (r, c) in [(2,2), (2,3), (3,2), (3,3)]]
        ]  # zones
        
        for line in all_lines:
            line_score = self.evaluate_line_fast(line)
            score += line_score
            
            if self.is_immediate_threat(line, self.me):
                my_threats += 1
            elif self.is_immediate_threat(line, self.opponent):
                opponent_threats += 1
        
        # Bonus menaces immédaites
        score += my_threats * 40 - opponent_threats * 50
        
        # Bonus centre
        for r, c in [(1,1), (1,2), (2,1), (2,2)]:
            piece = board.board[r][c]
            if piece:
                score += 2 if piece.player == self.me else -1
        
        return score
    
    def is_winning_for_me(self, board: QuantikBoard) -> bool:
        """
        Détermine si la position actuelle est gagnante pour notre IA
        """
        # Vérifier toutes les lignes gagnantes
        for r in range(4):
            line = [board.board[r][c] for c in range(4)]
            if self.is_winning_line(line):
                return True
        
        # Vérifier toutes les colonnes gagnantes
        for c in range(4):
            column = [board.board[r][c] for r in range(4)]
            if self.is_winning_line(column):
                return True
        
        # Vérifier toutes les zones gagnantes
        for zone in [[board.board[r][c] for (r, c) in zone_cells] for zone_cells in [[
            (0,0), (0,1), (1,0), (1,1)], [(0,2), (0,3), (1,2), (1,3)], 
            [(2,0), (2,1), (3,0), (3,1)], [(2,2), (2,3), (3,2), (3,3)]]]:
            if self.is_winning_line(zone):
                return True
        
        return False
    
    def is_winning_line(self, pieces: List[Optional[Piece]]) -> bool:
        """
        Vérifie si une ligne/colonne/zone est gagnante et appartient à notre IA
        """
        if any(p is None for p in pieces):
            return False
        
        shapes = {p.shape for p in pieces}
        if len(shapes) != 4:  # Pas 4 formes différentes
            return False
        
        # Vérifier que toutes les pièces appartiennent à notre IA
        return all(p.player == self.me for p in pieces)
    
    
    def evaluate_line_fast(self, pieces: List[Optional[Piece]]) -> float:
        my_pieces = [p for p in pieces if p and p.player == self.me]
        opponent_pieces = [p for p in pieces if p and p.player == self.opponent]
        empty_count = sum(1 for p in pieces if p is None)
        
        if not my_pieces and not opponent_pieces:
            return 0
        
        my_shapes = len({p.shape for p in my_pieces})
        opponent_shapes = len({p.shape for p in opponent_pieces})
        
        score = 0
        if my_pieces and not opponent_pieces:
            if my_shapes == len(my_pieces) and my_shapes + empty_count == 4:
                score = my_shapes * my_shapes * 2
                if my_shapes == 3:
                    score += 20
        elif opponent_pieces and not my_pieces:
            if opponent_shapes == len(opponent_pieces) and opponent_shapes + empty_count == 4:
                score = -(opponent_shapes * opponent_shapes * 2)
                if opponent_shapes == 3:
                    score -= 25
        
        return score
    
    def is_immediate_threat(self, pieces: List[Optional[Piece]], player: Player) -> bool:
        player_pieces = [p for p in pieces if p and p.player == player]
        other_pieces = [p for p in pieces if p and p.player != player]
        empty_count = sum(1 for p in pieces if p is None)
        
        if other_pieces or len(player_pieces) != 3 or empty_count != 1:
            return False
        
        shapes = {p.shape for p in player_pieces}
        return len(shapes) == 3
    
    def clear_tables(self):
        if len(self.transposition_table) > 50000:
            self.transposition_table.clear()
        if len(self.history_table) > 5000:
            self.history_table.clear()
        self.killer_moves = [[None, None] for _ in range(15)]
        self.position_cache.clear()