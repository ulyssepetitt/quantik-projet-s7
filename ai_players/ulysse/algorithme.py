# ai_players/ulysse/algorithme.py
# -------------------------------------------------------------------
# Implémentation d'un algorithme MinMax avec élagage Alpha-Beta
# pour le jeu Quantik
# -------------------------------------------------------------------
from typing import Optional, Tuple, List
from core.ai_base import AIBase
from core.types import Shape, Player, Piece
from core.rules import QuantikBoard, zone_index
import copy
import math

AI_NAME = "Ulysse – MinMax Alpha-Beta"
AI_AUTHOR = "Ulysse"
AI_VERSION = "1.0"

class QuantikAI(AIBase):
    def __init__(self, player: Player):
        super().__init__(player)
        self.opponent = Player.PLAYER1 if player == Player.PLAYER2 else Player.PLAYER2
        self.max_depth = 4  # Profondeur maximale de recherche
    
    def get_move(self, board, pieces_count) -> Optional[Tuple[int, int, Shape]]:
        # Créer une copie du plateau pour les simulations
        game_board = QuantikBoard()
        game_board.board = [row[:] for row in board]
        
        # Trouver le meilleur coup avec MinMax Alpha-Beta
        _, best_move = self.minimax(game_board, pieces_count, self.max_depth, -math.inf, math.inf, True)
        
        return best_move
    
    def minimax(self, board: QuantikBoard, pieces_count, depth: int, alpha: float, beta: float, maximizing: bool) -> Tuple[float, Optional[Tuple[int, int, Shape]]]:
        """
        Algorithme MinMax avec élagage Alpha-Beta
        """
        # Condition d'arrêt : victoire ou profondeur maximale atteinte
        if depth == 0 or board.check_victory() or not self.has_moves(board, pieces_count):
            return self.evaluate(board, pieces_count), None
        
        best_move = None
        current_player = self.me if maximizing else self.opponent
        
        if maximizing:
            max_eval = -math.inf
            
            # Parcourir tous les coups possibles
            for move in self.get_possible_moves(board, current_player, pieces_count):
                row, col, shape = move
                
                # Simuler le coup
                new_board = copy.deepcopy(board)
                new_pieces = copy.deepcopy(pieces_count)
                
                piece = Piece(shape, current_player)
                new_board.place_piece(row, col, piece)
                new_pieces[current_player][shape] -= 1
                
                # Récursion
                eval_score, _ = self.minimax(new_board, new_pieces, depth - 1, alpha, beta, False)
                
                # Mise à jour du meilleur score
                if eval_score > max_eval:
                    max_eval = eval_score
                    best_move = move
                
                # Élagage Alpha-Beta
                alpha = max(alpha, eval_score)
                if beta <= alpha:
                    break  # Élagage
            
            return max_eval, best_move
        
        else:  # Minimizing
            min_eval = math.inf
            
            # Parcourir tous les coups possibles
            for move in self.get_possible_moves(board, current_player, pieces_count):
                row, col, shape = move
                
                # Simuler le coup
                new_board = copy.deepcopy(board)
                new_pieces = copy.deepcopy(pieces_count)
                
                piece = Piece(shape, current_player)
                new_board.place_piece(row, col, piece)
                new_pieces[current_player][shape] -= 1
                
                # Récursion
                eval_score, _ = self.minimax(new_board, new_pieces, depth - 1, alpha, beta, True)
                
                # Mise à jour du meilleur score
                if eval_score < min_eval:
                    min_eval = eval_score
                    best_move = move
                
                # Élagage Alpha-Beta
                beta = min(beta, eval_score)
                if beta <= alpha:
                    break  # Élagage
            
            return min_eval, best_move
    
    def get_possible_moves(self, board: QuantikBoard, player: Player, pieces_count) -> List[Tuple[int, int, Shape]]:
        """
        Génère tous les coups possibles pour un joueur
        """
        moves = []
        
        for shape in Shape:
            # Vérifier si le joueur a encore des pièces de cette forme
            if pieces_count[player][shape] > 0:
                for row in range(4):
                    for col in range(4):
                        if board.board[row][col] is None:
                            piece = Piece(shape, player)
                            if board.is_valid_move(row, col, piece):
                                moves.append((row, col, shape))
        
        return moves
    
    def has_moves(self, board: QuantikBoard, pieces_count) -> bool:
        """
        Vérifie si le joueur actuel a des coups possibles
        """
        return len(self.get_possible_moves(board, self.me, pieces_count)) > 0 or \
               len(self.get_possible_moves(board, self.opponent, pieces_count)) > 0
    
    def evaluate(self, board: QuantikBoard, pieces_count) -> float:
        """
        Fonction d'évaluation de la position
        Plus le score est élevé, mieux c'est pour notre IA
        """
        # Vérification de victoire immédiate
        if board.check_victory():
            # Déterminer qui a gagné en vérifiant le dernier coup
            return 1000.0 if self.is_winning_for_me(board) else -1000.0
        
        score = 0.0
        
        # 1. Évaluation des lignes, colonnes et zones potentielles
        score += self.evaluate_lines(board)
        score += self.evaluate_columns(board)
        score += self.evaluate_zones(board)
        
        # 2. Bonus pour contrôler le centre
        score += self.evaluate_center_control(board)
        
        # 3. Pénalité si on a moins de pièces disponibles
        score += self.evaluate_pieces_balance(pieces_count)
        
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
    
    def evaluate_lines(self, board: QuantikBoard) -> float:
        """
        Évalue les opportunités sur les lignes
        """
        score = 0.0
        for r in range(4):
            line = [board.board[r][c] for c in range(4)]
            score += self.evaluate_line_potential(line)
        return score
    
    def evaluate_columns(self, board: QuantikBoard) -> float:
        """
        Évalue les opportunités sur les colonnes
        """
        score = 0.0
        for c in range(4):
            column = [board.board[r][c] for r in range(4)]
            score += self.evaluate_line_potential(column)
        return score
    
    def evaluate_zones(self, board: QuantikBoard) -> float:
        """
        Évalue les opportunités dans les zones 2x2
        """
        score = 0.0
        zones = [
            [(0,0), (0,1), (1,0), (1,1)],
            [(0,2), (0,3), (1,2), (1,3)],
            [(2,0), (2,1), (3,0), (3,1)],
            [(2,2), (2,3), (3,2), (3,3)]
        ]
        
        for zone_cells in zones:
            zone = [board.board[r][c] for (r, c) in zone_cells]
            score += self.evaluate_line_potential(zone)
        
        return score
    
    def evaluate_line_potential(self, pieces: List[Optional[Piece]]) -> float:
        """
        Évalue le potentiel d'une ligne/colonne/zone
        """
        my_pieces = [p for p in pieces if p is not None and p.player == self.me]
        opponent_pieces = [p for p in pieces if p is not None and p.player == self.opponent]
        empty_count = sum(1 for p in pieces if p is None)
        
        # Si l'adversaire peut bloquer (même forme dans la ligne)
        my_shapes = {p.shape for p in my_pieces}
        opponent_shapes = {p.shape for p in opponent_pieces}
        
        # Intersection des formes : formes bloquées
        blocked_shapes = my_shapes & opponent_shapes
        
        score = 0.0
        
        # Bonus selon le nombre de nos pièces
        if len(my_pieces) > 0:
            unique_my_shapes = len(my_shapes)
            # Plus on a de formes différentes, mieux c'est
            score += unique_my_shapes * 2.0
            
            # Bonus si on peut potentiellement gagner (4 formes différentes possibles)
            if unique_my_shapes + empty_count >= 4 and len(blocked_shapes) == 0:
                score += 5.0
        
        # Pénalité selon le nombre de pièces adverses
        if len(opponent_pieces) > 0:
            unique_opponent_shapes = len(opponent_shapes)
            score -= unique_opponent_shapes * 1.5
        
        return score
    
    def evaluate_center_control(self, board: QuantikBoard) -> float:
        """
        Bonus pour contrôler les cases centrales
        """
        center_positions = [(1,1), (1,2), (2,1), (2,2)]
        score = 0.0
        
        for r, c in center_positions:
            piece = board.board[r][c]
            if piece is not None:
                if piece.player == self.me:
                    score += 1.0
                else:
                    score -= 0.5
        
        return score
    
    def evaluate_pieces_balance(self, pieces_count) -> float:
        """
        Évalue l'équilibre des pièces disponibles
        """
        my_total = sum(pieces_count[self.me].values())
        opponent_total = sum(pieces_count[self.opponent].values())
        
        # Léger bonus si on a plus de pièces disponibles
        return (my_total - opponent_total) * 0.1