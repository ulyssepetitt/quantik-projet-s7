import random
from enum import Enum

# ---- Définitions attendues par l'interface graphique ----
class Shape(Enum):
    CIRCLE = "●"
    SQUARE = "■"
    TRIANGLE = "▲"
    DIAMOND = "♦️"

class Player(Enum):
    PLAYER1 = 1
    PLAYER2 = 2

class Piece:
    def __init__(self, shape: Shape, player: Player):
        self.shape = shape
        self.player = player

    def __eq__(self, other):
        return isinstance(other, Piece) and self.shape == other.shape and self.player == other.player

# ---- Zones 2×2 du plateau ----
ZONES = [
    [(0,0), (0,1), (1,0), (1,1)],  # Haut-gauche
    [(0,2), (0,3), (1,2), (1,3)],  # Haut-droite
    [(2,0), (2,1), (3,0), (3,1)],  # Bas-gauche
    [(2,2), (2,3), (3,2), (3,3)],  # Bas-droite
]

def zone_index(r: int, c: int) -> int:
    """Retourne l'indice de la zone (0 à 3) correspondant à la case (r, c)."""
    if r < 2 and c < 2:  return 0
    if r < 2 and c >= 2: return 1
    if r >= 2 and c < 2: return 2
    return 3

def is_valid_move(board, row: int, col: int, shape: Shape, me: Player) -> bool:
    """
    Vérifie si un coup est valide selon les règles du Quantik :
    - La case doit être vide
    - On ne peut pas placer une forme si l'adversaire a déjà cette forme
      dans la même ligne, colonne ou zone 2×2
    """
    # Case occupée → coup invalide
    if board[row][col] is not None:
        return False

    # Vérification de la ligne
    for c in range(4):
        p = board[row][c]
        if p is not None and p.shape == shape and p.player != me:
            return False

    # Vérification de la colonne
    for r in range(4):
        p = board[r][col]
        if p is not None and p.shape == shape and p.player != me:
            return False

    # Vérification de la zone 2×2
    z = zone_index(row, col)
    for (r, c) in ZONES[z]:
        p = board[r][c]
        if p is not None and p.shape == shape and p.player != me:
            return False

    return True

# ---- IA simple (choix aléatoire) ----
class QuantikAI:
    def __init__(self, player: Player):
        self.me = player

    def get_move(self, board, pieces_count):
        """
        Retourne un coup valide (row, col, shape) ou None.
        Cette version choisit simplement un coup valide au hasard,
        sans aucune stratégie.
        
        board : matrice 4×4 contenant None ou Piece
        pieces_count : dictionnaire {Player: {Shape: quantité_restante}}
        """
        valid_moves = []

        for shape in Shape:
            # Vérifie si j'ai encore des pièces de cette forme
            if pieces_count[self.me][shape] <= 0:
                continue
            # Parcours de toutes les cases
            for r in range(4):
                for c in range(4):
                    if is_valid_move(board, r, c, shape, self.me):
                        valid_moves.append((r, c, shape))

        # Pas de coups possibles → None
        if not valid_moves:
            return None

        # Choisit un coup au hasard
        return random.choice(valid_moves)
