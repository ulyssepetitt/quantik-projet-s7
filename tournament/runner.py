# tournament/runner_multi.py
# ----------------------------------------------------------
# Tournoi IA vs IA avec agrégation multi-seeds.
# - Détecte automatiquement les IA dans ai_players/*/algorithme.py
# - Fait s'affronter chaque paire pour plusieurs seeds
# - Mélange qui commence (P1/P2) et agrège les résultats
# - Affiche taux de victoire et intervalle de confiance 95%
# ----------------------------------------------------------

import importlib, pkgutil, pathlib, random, math, time
from typing import List, Dict, Tuple
from core.types import Shape, Player, Piece
from core.rules import QuantikBoard


# ---------- Découverte des IA ----------
def discover_ais():
    base_pkg = "ai_players"
    base_path = pathlib.Path(__file__).resolve().parents[1] / base_pkg
    ais = []
    for pkg in pkgutil.iter_modules([str(base_path)]):
        mod_name = f"{base_pkg}.{pkg.name}.algorithme"
        try:
            mod = importlib.import_module(mod_name)
            ai_cls  = getattr(mod, "QuantikAI", None)
            ai_name = getattr(mod, "AI_NAME", pkg.name)
            if ai_cls:
                ais.append({"name": ai_name, "cls": ai_cls})
        except Exception as e:
            print(f"[AI DISCOVERY] Erreur pour {mod_name}: {e}")
    ais.sort(key=lambda x: x["name"].lower())
    return ais


# ---------- Moteur d’une partie (sans GUI) ----------
def play_one_game(aiA_cls, aiB_cls, first: Player, seed: int) -> Player:
    """
    Joue une partie IA vs IA.
    - aiA = côté logique Player1, aiB = côté logique Player2
    - first = qui commence effectivement (P1 ou P2)
    - seed = graine pour rendre le match reproductible
    Retourne le vainqueur (Player).
    """
    # graine globale (pour les IA qui utilisent random)
    random.seed(seed)

    board = QuantikBoard()
    pieces = {
        Player.PLAYER1: {s: 2 for s in Shape},
        Player.PLAYER2: {s: 2 for s in Shape},
    }
    aiA = aiA_cls(Player.PLAYER1)
    aiB = aiB_cls(Player.PLAYER2)

    current = first
    while True:
        ai = aiA if current == Player.PLAYER1 else aiB
        move = ai.get_move(board.raw(), pieces)
        if not move:
            # Aucun coup possible -> l’autre gagne
            return Player.PLAYER2 if current == Player.PLAYER1 else Player.PLAYER1

        r, c, shape = move
        ok = board.place_piece(r, c, Piece(shape, current))
        if not ok:
            # Coup illégal proposé -> perte immédiate
            return Player.PLAYER2 if current == Player.PLAYER1 else Player.PLAYER1

        # Décrémente le stock
        pieces[current][shape] -= 1

        # Victoire ?
        if board.check_victory():
            return current

        # Changement de joueur
        current = Player.PLAYER2 if current == Player.PLAYER1 else Player.PLAYER1


# ---------- Statistiques ----------
def ci95(p: float, n: int) -> Tuple[float, float]:
    """Intervalle de confiance 95% (approx. normale). Retourne (low, high)."""
    if n == 0:
        return (0.0, 0.0)
    err = 1.96 * math.sqrt(max(p * (1 - p) / n, 0.0))
    return (max(0.0, p - err), min(1.0, p + err))


# ---------- Tournoi multi-seeds ----------
def run_tournament(games_per_seed: int = 10, seeds: List[int] = None):
    """
    Pour chaque paire (A,B):
      - pour chaque seed:
          - joue `games_per_seed` parties
          - alterne le joueur qui commence (P1/P2)
      - agrège les résultats
    """
    if seeds is None:
        seeds = [101, 202, 303, 404, 505]  # modifiez/ajoutez si besoin

    ais = discover_ais()
    names = [a["name"] for a in ais]
    print(f"IAs découvertes ({len(ais)}): {names}")

    # tableau des résultats agrégés: (A,B) -> dict
    results: Dict[Tuple[str, str], Dict[str, int]] = {}

    for i in range(len(ais)):
        for j in range(i + 1, len(ais)):
            A, B = ais[i], ais[j]
            key = (A["name"], B["name"])
            stats = {"A_wins": 0, "B_wins": 0, "total": 0}
            t0 = time.time()

            # multi-seeds
            for seed in seeds:
                # on répartit le droit de commencer à parts égales
                for g in range(games_per_seed):
                    # pour reproductibilité par partie: mélange seed + indices
                    game_seed = seed * 10_000 + g

                    # partie 1: A commence
                    winner = play_one_game(A["cls"], B["cls"], Player.PLAYER1, game_seed + 1)
                    stats["total"] += 1
                    if winner == Player.PLAYER1:
                        stats["A_wins"] += 1
                    else:
                        stats["B_wins"] += 1

                    # partie 2: B commence
                    winner = play_one_game(A["cls"], B["cls"], Player.PLAYER2, game_seed + 2)
                    stats["total"] += 1
                    if winner == Player.PLAYER1:
                        stats["A_wins"] += 1
                    else:
                        stats["B_wins"] += 1

            results[key] = stats
            # Affichage pair par pair avec IC
            A_w, B_w, T = stats["A_wins"], stats["B_wins"], stats["total"]
            pA = A_w / T if T else 0.0
            lo, hi = ci95(pA, T)
            dt = time.time() - t0
            print(
                f"{A['name']} vs {B['name']} -> {A_w}-{B_w} sur {T} | "
                f"WR(A)={pA:.3f} (95% CI: {lo:.3f}-{hi:.3f}) | {dt:.1f}s"
            )

    # Résumé final style “classement” grossier : tri par winrate cumulé
    print("\n=== Résumé agrégé par IA (winrate cumulé) ===")
    cum = {name: {"wins": 0, "loss": 0} for name in names}
    for (a_name, b_name), st in results.items():
        A_w, B_w = st["A_wins"], st["B_wins"]
        cum[a_name]["wins"] += A_w
        cum[a_name]["loss"] += B_w
        cum[b_name]["wins"] += B_w
        cum[b_name]["loss"] += A_w

    table = []
    for name in names:
        w, l = cum[name]["wins"], cum[name]["loss"]
        t = w + l
        wr = w / t if t else 0.0
        table.append((wr, w, l, name))
    table.sort(reverse=True)

    for wr, w, l, name in table:
        lo, hi = ci95(wr, w + l)
        print(f"{name:25s}  {w:4d}-{l:<4d}  WR={wr:.3f}  (95% CI {lo:.3f}-{hi:.3f})")


if __name__ == "__main__":
    # Ajustez ces paramètres si nécessaire:
    # - games_per_seed = combien de *paires* de parties par seed (2 parties par paire: A commence / B commence)
    # - seeds = liste de graines pour stabiliser les résultats
    run_tournament(games_per_seed=5, seeds=[101, 202, 303, 404, 505])
