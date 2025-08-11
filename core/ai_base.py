# core/ai_base.py
# ------------------------------------------------------------
# Contrat minimal pour toutes les IA (plugins).
# ------------------------------------------------------------
from abc import ABC, abstractmethod
from typing import Optional, Tuple
from core.types import Shape, Player

class AIBase(ABC):
    def __init__(self, player: Player):
        self.me = player

    @abstractmethod
    def get_move(self, board, pieces_count) -> Optional[Tuple[int, int, Shape]]:
        """
        Retourne (row, col, shape) ou None s'il n'y a aucun coup.
        - board : liste 4×4 de Piece ou None (état courant)
        - pieces_count : {Player: {Shape: int}}
        """
        ...