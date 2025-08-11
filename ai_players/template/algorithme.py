# ai_players/template/algorithme.py
# -------------------------------------------------------------------
# Modèle de départ pour chaque membre de l'équipe. Copiez ce dossier
# sous ai_players/<votre_nom>/ et implémentez votre stratégie.
# -------------------------------------------------------------------
from typing import Optional, Tuple
from core.ai_base import AIBase
from core.types import Shape, Player, Piece

AI_NAME = "<VotreNom> – <NomDeVotreIA>"
AI_AUTHOR = "<Votre Nom>"
AI_VERSION = "0.1"

class QuantikAI(AIBase):
    def get_move(self, board, pieces_count) -> Optional[Tuple[int, int, Shape]]:
        # TODO: Implémentez votre logique ici
        # Exemple minimal (à remplacer) : renvoyer None => pas de coup
        return None