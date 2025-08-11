# core/rules.py
# ---------------------------------------------------------------------
# Moteur du jeu Quantik : plateau, validation des coups, condition de
# victoire, et utilitaires (zones 2×2). Règle conforme au sujet :
# il est interdit de poser une forme si l'adversaire a déjà posé la
# même forme dans la même ligne/colonne/zone. Répéter sa propre forme
# est autorisé.
# ---------------------------------------------------------------------
from typing import List, Optional, Tuple
from core.types import Shape, Player, Piece

# Définition des zones 2×2 (indexées 0..3)
ZONES = [
    [(0,0), (0,1), (1,0), (1,1)],  # Haut-gauche
    [(0,2), (0,3), (1,2), (1,3)],  # Haut-droite
    [(2,0), (2,1), (3,0), (3,1)],  # Bas-gauche
    [(2,2), (2,3), (3,2), (3,3)],  # Bas-droite
]

def zone_index(r: int, c: int) -> int:
    if r < 2 and c < 2:  return 0
    if r < 2 and c >= 2: return 1
    if r >= 2 and c < 2: return 2
    return 3

class QuantikBoard:
    """Plateau 4×4 et règles de placement/victoire."""

    def __init__(self) -> None:
        # Matrice 4×4 de Piece ou None
        self.board: List[List[Optional[Piece]]] = [[None for _ in range(4)] for _ in range(4)]

    # --- Validation des coups ---
    def is_valid_move(self, row: int, col: int, piece: Piece) -> bool:
        # Case occupée
        if self.board[row][col] is not None:
            return False
        shape = piece.shape
        me = piece.player
        # Ligne
        for c in range(4):
            p = self.board[row][c]
            if p is not None and p.shape == shape and p.player != me:
                return False
        # Colonne
        for r in range(4):
            p = self.board[r][col]
            if p is not None and p.shape == shape and p.player != me:
                return False
        # Zone 2×2
        z = zone_index(row, col)
        for (r, c) in ZONES[z]:
            p = self.board[r][c]
            if p is not None and p.shape == shape and p.player != me:
                return False
        return True

    def place_piece(self, row: int, col: int, piece: Piece) -> bool:
        if not self.is_valid_move(row, col, piece):
            return False
        self.board[row][col] = piece
        return True

    # --- Victoire : 4 formes différentes sur une ligne/colonne/zone ---
    @staticmethod
    def _all_diff(pieces: List[Optional[Piece]]) -> bool:
        if any(p is None for p in pieces):
            return False
        shapes = {p.shape for p in pieces}
        return len(shapes) == 4

    def check_victory(self) -> bool:
        # Lignes
        for r in range(4):
            if self._all_diff([self.board[r][c] for c in range(4)]):
                return True
        # Colonnes
        for c in range(4):
            if self._all_diff([self.board[r][c] for r in range(4)]):
                return True
        # Zones
        for cells in ZONES:
            if self._all_diff([self.board[r][c] for (r, c) in cells]):
                return True
        return False

    # --- Utilitaires ---
    def has_valid_moves(self, player: Player) -> bool:
        for shape in Shape:
            for r in range(4):
                for c in range(4):
                    if self.board[r][c] is None:
                        if self.is_valid_move(r, c, Piece(shape, player)):
                            return True
        return False

    def raw(self) -> List[List[Optional[Piece]]]:
        """Retourne la matrice brute (pour les IA)."""
        return self.board