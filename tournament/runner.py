# tournament/runner.py
# ----------------------------------------------------------
# Tournoi IA vs IA en batch (sans interface graphique)
# - Découvre automatiquement les IA dans ai_players/*/algorithme.py
# - Joue des séries de parties en alternant les rôles (qui est P1/P2)
#   et en alternant qui commence (équité)
# - Comptage des points robuste (pas d’inversion due au joueur qui commence)
# - Options CLI: --games, --seed, --include-template
# ----------------------------------------------------------

import argparse
import importlib
import pkgutil
import pathlib
import random
from typing import List, Dict, Any, Optional, Tuple

from core.types import Shape, Player, Piece
from core.rules import QuantikBoard


# ---------------------------
# Découverte des IA disponibles
# ---------------------------
def discover_ais(include_template: bool = False) -> List[Dict[str, Any]]:
    """
    Parcourt ai_players/* et charge chaque module .../algorithme.py
    Retourne une liste de dicts: {"name": str, "cls": type}
    - Si include_template=False, on ignore le template de départ.
    """
    base_pkg = "ai_players"
    base_path = pathlib.Path(__file__).resolve().parents[1] / base_pkg
    ais = []
    if not base_path.exists():
        return ais

    for pkg in pkgutil.iter_modules([str(base_path)]):
        # saute le template si demandé
        if not include_template and pkg.name == "template":
            continue

        mod_name = f"{base_pkg}.{pkg.name}.algorithme"
        try:
            mod = importlib.import_module(mod_name)
            ai_cls = getattr(mod, "QuantikAI", None)
            ai_name = getattr(mod, "AI_NAME", pkg.name)
            if ai_cls:
                ais.append({"name": ai_name, "cls": ai_cls})
        except Exception as e:
            print(f"[AI DISCOVERY] Erreur pour {mod_name}: {e}")

    ais.sort(key=lambda x: x["name"].lower())
    return ais


# ---------------------------
# Helpers plateau / API
# ---------------------------
def get_raw_board(board: QuantikBoard):
    """
    Certaines implémentations exposent .board (liste 4x4),
    d’autres fournissent .raw(). On gère les deux.
    """
    if hasattr(board, "board"):
        return board.board
    if hasattr(board, "raw"):
        return board.raw()
    # fallback très improbable
    raise AttributeError("QuantikBoard ne fournit ni .board ni .raw()")


def other(p: Player) -> Player:
    """Renvoie l’autre joueur (utile si besoin)."""
    return Player.PLAYER1 if p == Player.PLAYER2 else Player.PLAYER2


# ---------------------------
# Partie unique IA vs IA
# ---------------------------
def play_one_game_with_sides(
    aiA_cls,
    aiB_cls,
    A_side: Player = Player.PLAYER1,
    first: Player = Player.PLAYER1,
) -> Player:
    """
    Joue UNE partie entre deux classes d’IA.
    - A_side indique quel côté (P1/P2) sera contrôlé par aiA.
    - first indique quel joueur commence la partie.
    Retourne le Player gagnant.
    Rappels:
      * Un coup invalide proposé => défaite immédiate de l’IA fautive.
      * Si un joueur ne peut pas jouer => l’autre gagne.
      * La victoire standard suit la règle "4 formes toutes différentes".
    """
    board = QuantikBoard()
    pieces = {
        Player.PLAYER1: {s: 2 for s in Shape},
        Player.PLAYER2: {s: 2 for s in Shape},
    }

    # Attribue les côtés
    B_side = other(A_side)
    aiA = aiA_cls(A_side)
    aiB = aiB_cls(B_side)

    current = first
    while True:
        ai = aiA if current == A_side else aiB
        raw = get_raw_board(board)
        move = ai.get_move(raw, pieces)

        if not move:
            # Aucun coup renvoyé => l’autre gagne
            return other(current)

        r, c, shape = move

        # Applique le coup: si invalide => défaite immédiate de l’IA fautive
        ok = board.place_piece(r, c, Piece(shape, current))
        if not ok:
            return other(current)

        # Décrémente le stock de la forme jouée
        pieces[current][shape] -= 1

        # Victoire standard ?
        if board.check_victory():
            return current

        # À l’autre de jouer
        current = other(current)


# ---------------------------
# Boucle de tournoi
# ---------------------------
def run_tournament(
    games: int = 20,
    seed: Optional[int] = 42,
    include_template: bool = False,
) -> None:
    """
    Fait s’affronter toutes les IA pairwise (A vs B).
    - games: nombre de parties par duel (doit être pair pour l’équité)
    - seed : reproductibilité des choix aléatoires (IA random, MCTS, etc.)
    - include_template : inclure ou ignorer l’IA "template"
    Affiche les résultats au fur et à mesure.
    """
    if seed is not None:
        random.seed(seed)

    ais = discover_ais(include_template=include_template)
    names = [a["name"] for a in ais]
    print(f"IAs découvertes ({len(ais)}): {names}")

    if len(ais) < 2:
        print("Pas assez d'IA pour lancer un tournoi (minimum 2).")
        return

    # on s’assure que games est pair pour alterner les rôles proprement
    if games % 2 != 0:
        games += 1
        print(f"[NOTE] Nombre de parties arrondi à pair: {games}")

    for i in range(len(ais)):
        for j in range(i + 1, len(ais)):
            A, B = ais[i], ais[j]
            wA = wB = 0

            for g in range(games):
                # Alternance des rôles:
                #  - Sur les parties paires: A = P1, B = P2, et P1 commence
                #  - Sur les parties impaires: A = P2, B = P1, et P2 commence
                if g % 2 == 0:
                    A_side = Player.PLAYER1
                    first = Player.PLAYER1
                else:
                    A_side = Player.PLAYER2
                    first = Player.PLAYER2

                winner = play_one_game_with_sides(
                    A["cls"], B["cls"], A_side=A_side, first=first
                )

                # Comptage simple et correct:
                # - Si le gagnant == côté de A cette partie → point pour A, sinon pour B.
                if winner == A_side:
                    wA += 1
                else:
                    wB += 1

            print(f"{A['name']} vs {B['name']} -> {wA}-{wB} sur {games}")


# ---------------------------
# Entrée CLI
# ---------------------------
def parse_args():
    p = argparse.ArgumentParser(description="Tournoi IA Quantik (batch, sans GUI)")
    p.add_argument("--games", type=int, default=20,
                   help="Nombre de parties par duel (pair recommandé)")
    p.add_argument("--seed", type=int, default=42,
                   help="Graine aléatoire pour la reproductibilité (utiliser --seed -1 pour désactiver)")
    p.add_argument("--include-template", action="store_true",
                   help="Inclure l’IA 'template' dans le tournoi")
    return p.parse_args()


def main():
    args = parse_args()
    seed = None if args.seed == -1 else args.seed
    run_tournament(games=args.games, seed=seed, include_template=args.include_template)


if __name__ == "__main__":
    main()
