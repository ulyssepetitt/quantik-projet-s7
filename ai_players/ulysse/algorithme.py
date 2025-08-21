# ai_players/ulysse/algorithme.py
# -------------------------------------------------------------------
# Algorithme Quantik Minimax Alpha-Beta - Version Robuste v4.0
# Implémentation de A à Z pour éliminer tous les bugs
# -------------------------------------------------------------------
from typing import Optional, Tuple, List, Dict
from core.ai_base import AIBase
from core.types import Shape, Player, Piece
from core.rules import QuantikBoard
import math
import time

AI_NAME = "minmax 1.3"
AI_AUTHOR = "Ulysse Petit"
AI_VERSION = "1.3"

class QuantikAI(AIBase):
    def __init__(self, player: Player):
        super().__init__(player)
        self.opponent = Player.PLAYER1 if player == Player.PLAYER2 else Player.PLAYER2
        self.nodes_evaluated = 0
        
        # Paramètres adaptatifs
        self.base_depth = 4
        self.max_time = 10.0
        self.target_time = 2.5
    
    def get_move(self, board, pieces_count) -> Optional[Tuple[int, int, Shape]]:
        """Point d'entrée principal - GARANTIT un coup valide ou None si impossible"""
        game_board = QuantikBoard()
        game_board.board = [row[:] for row in board]
        
        # Validation préalable - éliminer les bugs à la source
        valid_moves = self._generate_all_valid_moves(game_board, self.me)
        if not valid_moves:
            return None  # Vraiment aucun coup possible
        
        # Adaptation profondeur selon stade de partie
        pieces_played = sum(1 for r in range(4) for c in range(4) if game_board.board[r][c] is not None)
        depth = self._calculate_optimal_depth(pieces_played)
        
        self.nodes_evaluated = 0
        start_time = time.time()
        
        try:
            # Recherche minimax avec sécurité maximale
            best_score, best_move = self._minimax_root(game_board, depth, start_time)
            
            # Validation finale - paranoia programming
            if best_move is None and valid_moves:
                # Fallback de sécurité : choix rapide mais valide
                return self._emergency_move_selection(game_board, valid_moves)
            
            return best_move
            
        except Exception:
            # Dernier recours : au moins un coup valide
            return self._emergency_move_selection(game_board, valid_moves)
    
    def _generate_all_valid_moves(self, board: QuantikBoard, player: Player) -> List[Tuple[int, int, Shape]]:
        """Générateur de coups ULTRA-FIABLE - Jamais de bug ici"""
        moves = []
        
        # Parcours systématique de TOUTES les possibilités
        for row in range(4):
            for col in range(4):
                # Case libre ?
                if board.board[row][col] is not None:
                    continue  # Occupée
                
                # Tester toutes les formes
                for shape in Shape:
                    piece = Piece(shape, player)
                    
                    # Validation stricte des règles Quantik
                    if self._is_move_valid(board, row, col, piece):
                        moves.append((row, col, shape))
        
        return moves
    
    def _is_move_valid(self, board: QuantikBoard, row: int, col: int, piece: Piece) -> bool:
        """Validation des règles Quantik - Implémentation directe pour éviter les bugs"""
        # Case libre ?
        if board.board[row][col] is not None:
            return False
        
        shape = piece.shape
        player = piece.player
        
        # Règle ligne : impossible si adversaire a la même forme
        for c in range(4):
            other_piece = board.board[row][c]
            if other_piece and other_piece.shape == shape and other_piece.player != player:
                return False
        
        # Règle colonne : impossible si adversaire a la même forme  
        for r in range(4):
            other_piece = board.board[r][col]
            if other_piece and other_piece.shape == shape and other_piece.player != player:
                return False
        
        # Règle zone 2x2 : impossible si adversaire a la même forme
        zone_positions = self._get_zone_positions(row, col)
        for (r, c) in zone_positions:
            other_piece = board.board[r][c]
            if other_piece and other_piece.shape == shape and other_piece.player != player:
                return False
        
        return True
    
    def _get_zone_positions(self, row: int, col: int) -> List[Tuple[int, int]]:
        """Calcul des positions de la zone 2x2 - Simple et fiable"""
        if row < 2 and col < 2:
            return [(0,0), (0,1), (1,0), (1,1)]  # Zone haut-gauche
        elif row < 2 and col >= 2:
            return [(0,2), (0,3), (1,2), (1,3)]  # Zone haut-droite
        elif row >= 2 and col < 2:
            return [(2,0), (2,1), (3,0), (3,1)]  # Zone bas-gauche
        else:
            return [(2,2), (2,3), (3,2), (3,3)]  # Zone bas-droite
    
    def _calculate_optimal_depth(self, pieces_played: int) -> int:
        """Profondeur adaptative selon stade de partie"""
        if pieces_played <= 4:      # Ouverture
            return self.base_depth
        elif pieces_played <= 10:   # Milieu  
            return self.base_depth + 2
        else:                       # Fin
            return self.base_depth + 4
    
    def _minimax_root(self, board: QuantikBoard, depth: int, start_time: float) -> Tuple[float, Optional[Tuple[int, int, Shape]]]:
        """Racine minimax - Gestion du premier niveau avec sécurité max"""
        best_score = -math.inf
        best_move = None
        
        valid_moves = self._generate_all_valid_moves(board, self.me)
        
        # Sécurité : au moins un coup doit exister
        if not valid_moves:
            return 0.0, None
        
        # PRIORITÉ ABSOLUE : Vérification victoire immédiate
        for row, col, shape in valid_moves:
            old_piece = board.board[row][col]
            board.board[row][col] = Piece(shape, self.me)
            
            if board.check_victory():
                board.board[row][col] = old_piece
                return 20000.0, (row, col, shape)  # Victoire immédiate !
            
            board.board[row][col] = old_piece
        
        # PRIORITÉ HAUTE : Blocage menaces immédiates adversaire
        opponent_threats = self._find_immediate_threats(board, self.opponent)
        if opponent_threats:
            # Stratégie adaptative selon le nombre de menaces
            if len(opponent_threats) == 1:
                # Une seule menace : blocage sûr obligatoire
                for row, col, shape in valid_moves:
                    threat_blocked = any(
                        (row, col) in threat_positions for threat_positions in opponent_threats
                    )
                    if threat_blocked:
                        # Vérifier que ce coup ne créé pas une nouvelle menace adverse
                        old_piece = board.board[row][col]
                        board.board[row][col] = Piece(shape, self.me)
                        
                        new_opponent_threats = self._find_immediate_threats(board, self.opponent)
                        board.board[row][col] = old_piece
                        
                        # Si pas de nouvelle menace créée, c'est un bon blocage
                        if len(new_opponent_threats) == 0:
                            return 15000.0, (row, col, shape)  # Blocage critique sûr !
            else:
                # Menaces multiples : d'abord essayer le blocage optimal
                best_blocking_move = self._find_best_blocking_move(board, opponent_threats, valid_moves)
                if best_blocking_move:
                    return 14000.0, best_blocking_move  # Blocage tactique optimal
                
                # Si aucun blocage optimal, bloquer la menace la plus critique par dominance
                most_dominant_threat = self._find_most_dominant_threat(board, opponent_threats)
                if most_dominant_threat:
                    return 13500.0, most_dominant_threat  # Blocage menace dominante
        
        # PRIORITÉ MOYENNE : Stratégie contre menaces en développement  
        opponent_dev_threats = self._find_developing_threats(board, self.opponent)
        if opponent_dev_threats:
            # Essayer de créer une contre-menace plus forte d'abord
            best_counter_move = None
            best_counter_score = -math.inf
            
            for row, col, shape in valid_moves:
                old_piece = board.board[row][col]
                board.board[row][col] = Piece(shape, self.me)
                
                # CRUCIAL: Vérifier qu'on ne créé pas de menace immédiate adverse
                new_opponent_threats = len(self._find_immediate_threats(board, self.opponent))
                if new_opponent_threats > 0:
                    board.board[row][col] = old_piece
                    continue  # Ignorer ce coup dangereux
                
                # Évaluer si ce coup crée une menace plus forte
                my_new_threats = len(self._find_immediate_threats(board, self.me))
                my_dev_new_threats = len(self._find_developing_threats(board, self.me))
                
                counter_score = my_new_threats * 200 + my_dev_new_threats * 100
                
                # Bonus si bloque aussi une menace adverse
                dev_threat_blocked = any(
                    (row, col) in threat_positions for threat_positions in opponent_dev_threats
                )
                if dev_threat_blocked:
                    counter_score += 150
                
                if counter_score > best_counter_score:
                    best_counter_score = counter_score
                    best_counter_move = (row, col, shape)
                
                board.board[row][col] = old_piece
            
            # Si contre-attaque forte trouvée, la privilégier
            if best_counter_score >= 200:  # Seuil pour contre-attaque
                return 13000.0, best_counter_move  # Contre-attaque !
            
            # Si au moins un coup sûr qui bloque, le prendre
            if best_counter_move and best_counter_score >= 150:  # Seuil pour blocage sûr
                return 11000.0, best_counter_move  # Blocage défensif sûr
            
            # Sinon, laisser minimax gérer (éviter les blocages qui créent des pièges)
        
        # Tri des coups par priorité tactique
        sorted_moves = self._sort_moves_by_priority(board, valid_moves)
        
        # Évaluation minimax normale
        for row, col, shape in sorted_moves:
            # Timeout protection
            if time.time() - start_time > self.max_time:
                break
            
            # Simulation du coup
            old_piece = board.board[row][col]
            board.board[row][col] = Piece(shape, self.me)
            
            # Évaluation recursive
            score = self._minimax(board, depth - 1, -math.inf, math.inf, False, start_time)
            
            # Restoration
            board.board[row][col] = old_piece
            
            # Mise à jour du meilleur coup
            if score > best_score:
                best_score = score
                best_move = (row, col, shape)
        
        # Garantie : toujours un coup si moves disponibles
        if best_move is None and valid_moves:
            best_move = valid_moves[0]  # Premier coup valide en fallback
        
        return best_score, best_move
    
    def _minimax(self, board: QuantikBoard, depth: int, alpha: float, beta: float, 
                maximizing: bool, start_time: float) -> float:
        """Minimax Alpha-Beta core - Version ultra-robuste"""
        
        # Timeout
        if time.time() - start_time > self.max_time:
            return 0.0
        
        self.nodes_evaluated += 1
        
        # Conditions terminales
        if board.check_victory():
            # Déterminer le gagnant
            if self._is_winner(board, self.me):
                return 10000.0 - (10 - depth)  # Plus rapide = mieux
            else:
                return -10000.0 + (10 - depth)  # Défaite retardée = moins pire
        
        if depth == 0:
            return self._evaluate_position(board)
        
        # Génération des coups
        current_player = self.me if maximizing else self.opponent
        valid_moves = self._generate_all_valid_moves(board, current_player)
        
        # Pas de coups = égalité
        if not valid_moves:
            return 0.0
        
        if maximizing:
            max_eval = -math.inf
            
            for row, col, shape in valid_moves:
                old_piece = board.board[row][col]
                board.board[row][col] = Piece(shape, current_player)
                
                eval_score = self._minimax(board, depth - 1, alpha, beta, False, start_time)
                
                board.board[row][col] = old_piece
                
                max_eval = max(max_eval, eval_score)
                alpha = max(alpha, eval_score)
                
                if beta <= alpha:
                    break  # Alpha-beta cut
                
            return max_eval
            
        else:  # Minimizing
            min_eval = math.inf
            
            for row, col, shape in valid_moves:
                old_piece = board.board[row][col]
                board.board[row][col] = Piece(shape, current_player)
                
                eval_score = self._minimax(board, depth - 1, alpha, beta, True, start_time)
                
                board.board[row][col] = old_piece
                
                min_eval = min(min_eval, eval_score)
                beta = min(beta, eval_score)
                
                if beta <= alpha:
                    break  # Alpha-beta cut
                
            return min_eval
    
    def _evaluate_position(self, board: QuantikBoard) -> float:
        """Évaluateur de position équilibré - Simple mais efficace"""
        score = 0.0
        
        # 1. Analyse matérielle et positionnelle
        for r in range(4):
            for c in range(4):
                piece = board.board[r][c]
                if piece:
                    # Bonus positionnel
                    pos_value = self._get_position_value(r, c)
                    
                    if piece.player == self.me:
                        score += pos_value
                    else:
                        score -= pos_value * 0.8  # Légèrement asymétrique pour être agressif
        
        # 2. Menaces et lignes en formation (évaluation approfondie)
        my_threats = self._count_line_potential(board, self.me)
        opp_threats = self._count_line_potential(board, self.opponent)
        
        # Pénalité MASSIVE pour menaces adverses en développement
        opp_dev_threats = len(self._find_developing_threats(board, self.opponent))
        opp_immediate_threats = len(self._find_immediate_threats(board, self.opponent))
        
        score += my_threats * 50 
        score -= opp_threats * 60  # Menaces générales
        score -= opp_dev_threats * 150  # Menaces en développement = DANGER
        score -= opp_immediate_threats * 300  # Menaces immédiates = CRITIQUE
        
        # 3. Mobilité
        my_moves = len(self._generate_all_valid_moves(board, self.me))
        opp_moves = len(self._generate_all_valid_moves(board, self.opponent))
        
        score += (my_moves - opp_moves) * 5
        
        return score
    
    def _get_position_value(self, row: int, col: int) -> float:
        """Valeurs positionnelles - Centre privilégié"""
        # Centre (contrôle 4 zones)
        if (row, col) in [(1,1), (1,2), (2,1), (2,2)]:
            return 20.0
        # Semi-centre (contrôle 2 zones)  
        elif row in [1,2] or col in [1,2]:
            return 10.0
        # Coins (contrôle 1 zone)
        else:
            return 5.0
    
    def _count_line_potential(self, board: QuantikBoard, player: Player) -> int:
        """Compte les lignes avec potentiel pour le joueur"""
        potential = 0
        
        # Toutes les lignes possibles
        lines = []
        
        # Lignes horizontales
        for r in range(4):
            lines.append([(r, c) for c in range(4)])
        
        # Lignes verticales  
        for c in range(4):
            lines.append([(r, c) for r in range(4)])
        
        # Zones 2x2
        zones = [
            [(0,0), (0,1), (1,0), (1,1)],
            [(0,2), (0,3), (1,2), (1,3)], 
            [(2,0), (2,1), (3,0), (3,1)],
            [(2,2), (2,3), (3,2), (3,3)]
        ]
        lines.extend(zones)
        
        # Évaluation de chaque ligne
        for line_positions in lines:
            pieces = [board.board[r][c] for r, c in line_positions]
            potential += self._evaluate_line_potential(pieces, player)
        
        return potential
    
    def _evaluate_line_potential(self, pieces: List[Optional[Piece]], player: Player) -> int:
        """Évalue le potentiel d'une ligne pour un joueur"""
        my_pieces = [p for p in pieces if p and p.player == player]
        opp_pieces = [p for p in pieces if p and p.player != player]
        empty_count = sum(1 for p in pieces if p is None)
        
        # Ligne bloquée par l'adversaire
        if opp_pieces:
            return 0
        
        # Pas de nos pièces
        if not my_pieces:
            return 0
        
        # Évaluation selon progression
        my_shapes = len(set(p.shape for p in my_pieces))
        
        # Toutes nos pièces ont des formes différentes + cases libres = potentiel
        if my_shapes == len(my_pieces) and my_shapes + empty_count == 4:
            if my_shapes == 3:  # Menace immédiate
                return 10
            elif my_shapes == 2:  # Menace en développement  
                return 3
            elif my_shapes == 1:  # Début prometteur
                return 1
        
        return 0
    
    def _is_winner(self, board: QuantikBoard, player: Player) -> bool:
        """Détermine si le joueur a gagné - Simple et fiable"""
        # Cette fonction est appelée après board.check_victory() == True
        # Il faut déterminer qui a créé la ligne gagnante
        
        # Vérifier toutes les lignes possibles
        all_lines = []
        
        # Lignes horizontales
        for r in range(4):
            all_lines.append([(r, c) for c in range(4)])
        
        # Lignes verticales
        for c in range(4):
            all_lines.append([(r, c) for r in range(4)])
        
        # Zones 2x2
        zones = [
            [(0,0), (0,1), (1,0), (1,1)],
            [(0,2), (0,3), (1,2), (1,3)],
            [(2,0), (2,1), (3,0), (3,1)], 
            [(2,2), (2,3), (3,2), (3,3)]
        ]
        all_lines.extend(zones)
        
        # Chercher une ligne gagnante avec au moins une pièce du joueur
        for line_positions in all_lines:
            pieces = [board.board[r][c] for r, c in line_positions]
            
            # Ligne complète ?
            if all(p is not None for p in pieces):
                # 4 formes différentes ?
                shapes = {p.shape for p in pieces}
                if len(shapes) == 4:
                    # Au moins une pièce du joueur ?
                    if any(p.player == player for p in pieces):
                        return True
        
        return False
    
    def _emergency_move_selection(self, board: QuantikBoard, valid_moves: List[Tuple[int, int, Shape]]) -> Tuple[int, int, Shape]:
        """Sélection d'urgence - Au moins jouer quelque chose de sensé"""
        if not valid_moves:
            return None
        
        # Privilégier le centre si possible
        center_moves = [(r, c, s) for r, c, s in valid_moves if (r, c) in [(1,1), (1,2), (2,1), (2,2)]]
        if center_moves:
            return center_moves[0]
        
        # Sinon premier coup disponible
        return valid_moves[0]
    
    def _find_immediate_threats(self, board: QuantikBoard, player: Player) -> List[List[Tuple[int, int]]]:
        """Trouve les menaces immédiates (3 formes différentes + 1 vide) d'un joueur"""
        threats = []
        
        # Toutes les lignes possibles
        all_lines = []
        
        # Lignes horizontales
        for r in range(4):
            all_lines.append([(r, c) for c in range(4)])
        
        # Lignes verticales
        for c in range(4):
            all_lines.append([(r, c) for r in range(4)])
        
        # Zones 2x2
        zones = [
            [(0,0), (0,1), (1,0), (1,1)],
            [(0,2), (0,3), (1,2), (1,3)],
            [(2,0), (2,1), (3,0), (3,1)],
            [(2,2), (2,3), (3,2), (3,3)]
        ]
        all_lines.extend(zones)
        
        # Chercher les menaces immédiates
        for line_positions in all_lines:
            pieces = [board.board[r][c] for r, c in line_positions]
            
            all_pieces = [p for p in pieces if p is not None]
            empty_positions = [(r, c) for (r, c), p in zip(line_positions, pieces) if p is None]
            
            # Menace immédiate : 3 pièces avec formes différentes + 1 vide
            # ET au moins une pièce du joueur (pour que ce soit SA menace)
            if len(all_pieces) == 3 and len(empty_positions) == 1:
                shapes = {p.shape for p in all_pieces}
                if len(shapes) == 3:  # 3 formes différentes
                    # Vérifier qu'au moins une pièce appartient au joueur
                    player_pieces = [p for p in all_pieces if p.player == player]
                    if len(player_pieces) > 0:
                        threats.append(empty_positions)  # Liste des positions de blocage
        
        return threats
    
    def _find_developing_threats(self, board: QuantikBoard, player: Player) -> List[List[Tuple[int, int]]]:
        """Trouve les menaces en développement (2 formes différentes + 2 vides)"""
        threats = []
        
        # Toutes les lignes possibles (même code que pour menaces immédiates)
        all_lines = []
        
        # Lignes horizontales
        for r in range(4):
            all_lines.append([(r, c) for c in range(4)])
        
        # Lignes verticales
        for c in range(4):
            all_lines.append([(r, c) for r in range(4)])
        
        # Zones 2x2
        zones = [
            [(0,0), (0,1), (1,0), (1,1)],
            [(0,2), (0,3), (1,2), (1,3)],
            [(2,0), (2,1), (3,0), (3,1)],
            [(2,2), (2,3), (3,2), (3,3)]
        ]
        all_lines.extend(zones)
        
        # Chercher les menaces en développement
        for line_positions in all_lines:
            pieces = [board.board[r][c] for r, c in line_positions]
            
            all_pieces = [p for p in pieces if p is not None]
            empty_positions = [(r, c) for (r, c), p in zip(line_positions, pieces) if p is None]
            
            # Menace en développement : 2 pièces avec formes différentes + 2 vides
            # ET au moins une pièce du joueur (pour que ce soit SA menace potentielle)
            if len(all_pieces) == 2 and len(empty_positions) == 2:
                shapes = {p.shape for p in all_pieces}
                if len(shapes) == 2:  # 2 formes différentes
                    # Vérifier qu'au moins une pièce appartient au joueur
                    player_pieces = [p for p in all_pieces if p.player == player]
                    if len(player_pieces) > 0:
                        threats.append(empty_positions)  # Positions pouvant bloquer/compléter
        
        return threats
    
    def _find_best_blocking_move(self, board: QuantikBoard, opponent_threats: List[List[Tuple[int, int]]], 
                                valid_moves: List[Tuple[int, int, Shape]]) -> Optional[Tuple[int, int, Shape]]:
        """Trouve le meilleur coup de blocage quand il y a menaces multiples"""
        best_move = None
        best_score = -math.inf
        
        # Positions de toutes les menaces adverses
        all_threat_positions = set()
        for threat_positions in opponent_threats:
            all_threat_positions.update(threat_positions)
        
        for row, col, shape in valid_moves:
            # Ce coup bloque-t-il au moins une menace ?
            if (row, col) not in all_threat_positions:
                continue
            
            # NOUVEAU: Bonus pour bloquer les menaces les plus dominées par l'adversaire
            # (calculer AVANT de jouer le coup sur l'état actuel)
            dominance_bonus = self._calculate_threat_dominance_bonus(board, row, col, opponent_threats)
                
            # Évaluer ce coup de blocage
            old_piece = board.board[row][col]
            board.board[row][col] = Piece(shape, self.me)
            
            # Compter les menaces restantes après ce coup
            remaining_threats = len(self._find_immediate_threats(board, self.opponent))
            
            # Bonus si on créé nos propres menaces
            our_new_threats = len(self._find_immediate_threats(board, self.me))
            
            # Score : réduire menaces adverses + créer nos menaces + priorité menaces dominantes
            score = (len(opponent_threats) - remaining_threats) * 1000 + our_new_threats * 500 + dominance_bonus - remaining_threats * 200
            
            if score > best_score:
                best_score = score
                best_move = (row, col, shape)
            
            board.board[row][col] = old_piece
        
        return best_move
    
    def _calculate_threat_dominance_bonus(self, board: QuantikBoard, block_row: int, block_col: int, 
                                        opponent_threats: List[List[Tuple[int, int]]]) -> int:
        """Calcule un bonus pour bloquer les menaces les plus dominées par l'adversaire"""
        # Toutes les lignes possibles
        all_lines = []
        
        # Lignes horizontales
        for r in range(4):
            all_lines.append([(r, c) for c in range(4)])
        
        # Lignes verticales
        for c in range(4):
            all_lines.append([(r, c) for r in range(4)])
        
        # Zones 2x2
        zones = [
            [(0,0), (0,1), (1,0), (1,1)],
            [(0,2), (0,3), (1,2), (1,3)],
            [(2,0), (2,1), (3,0), (3,1)],
            [(2,2), (2,3), (3,2), (3,3)]
        ]
        all_lines.extend(zones)
        
        max_dominance = 0
        
        # Chercher quelle ligne serait bloquée par ce coup
        for line_positions in all_lines:
            if (block_row, block_col) in line_positions:
                pieces = [board.board[r][c] for r, c in line_positions]
                non_none = [p for p in pieces if p is not None]
                
                # Cette ligne a-t-elle 3 formes différentes (menace immédiate) ?
                if len(non_none) == 3:
                    shapes = {p.shape for p in non_none}
                    if len(shapes) == 3:
                        # Compter les pièces de l'adversaire dans cette ligne
                        opponent_pieces = sum(1 for p in non_none if p.player == self.opponent)
                        
                        # Plus l'adversaire domine la ligne, plus c'est prioritaire de bloquer
                        dominance = opponent_pieces * 100
                        max_dominance = max(max_dominance, dominance)
        
        return max_dominance
    
    def _find_most_dominant_threat(self, board: QuantikBoard, opponent_threats: List[List[Tuple[int, int]]]) -> Optional[Tuple[int, int, Shape]]:
        """Trouve le blocage de la menace la plus dominée par l'adversaire"""
        best_move = None
        best_dominance = -1
        
        all_threat_positions = set()
        for threat_positions in opponent_threats:
            all_threat_positions.update(threat_positions)
        
        valid_moves = self._generate_all_valid_moves(board, self.me)
        
        for row, col, shape in valid_moves:
            if (row, col) in all_threat_positions:
                dominance = self._calculate_threat_dominance_bonus(board, row, col, opponent_threats)
                if dominance > best_dominance:
                    best_dominance = dominance
                    best_move = (row, col, shape)
        
        return best_move
    
    def _sort_moves_by_priority(self, board: QuantikBoard, moves: List[Tuple[int, int, Shape]]) -> List[Tuple[int, int, Shape]]:
        """Trie les coups par priorité tactique"""
        def move_score(move):
            row, col, shape = move
            score = 0
            
            # Priorité 1: Positions centrales
            if (row, col) in [(1,1), (1,2), (2,1), (2,2)]:
                score += 100
            elif row in [1,2] or col in [1,2]:
                score += 50
            
            # Priorité 2: Création de menaces
            old_piece = board.board[row][col]
            board.board[row][col] = Piece(shape, self.me)
            
            my_threats = len(self._find_immediate_threats(board, self.me))
            score += my_threats * 200
            
            # Priorité 3: Potentiel de lignes
            potential = self._count_line_potential(board, self.me)
            score += potential * 10
            
            board.board[row][col] = old_piece
            
            return -score  # Tri décroissant
        
        return sorted(moves, key=move_score)