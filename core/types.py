# core/types.py
# ---------------------------------------------------------------------
# Types partagés entre la GUI et les IA : Shape, Player, Piece.
# ---------------------------------------------------------------------
from enum import Enum

class Shape(Enum):
    CIRCLE = "●"
    SQUARE = "■"
    TRIANGLE = "▲"
    DIAMOND = "♦️"

class Player(Enum):
    PLAYER1 = 1
    PLAYER2 = 2

class Piece:
    """
    Représente une pièce posée sur le plateau.
    - shape : la forme (Shape)
    - player : le propriétaire (Player)
    """
    def __init__(self, shape: Shape, player: Player):
        self.shape = shape
        self.player = player

    def __eq__(self, other):
        return (
            isinstance(other, Piece)
            and self.shape == other.shape
            and self.player == other.player
        )