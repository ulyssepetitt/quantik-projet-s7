# tournament/runner.py
# ----------------------------------------------------------
# Tournoi IA vs IA (incluant self-play) sans interface GUI.
# - Découverte automatique des IA dans ai_players/*/algorithme.py
# - Matchs en aller/retour (alternance du premier joueur)
# - Inclut les confrontations IA identiques (self-play)
# - Seme aléatoire par match pour reproductibilité
# - Statistiques: winrate + intervalle de confiance de Wilson
# - Classement Elo approximatif
# - Matrice de confrontations
# - Export CSV optionnel (désactivé par défaut)
# ----------------------------------------------------------

from __future__ import annotations
import importlib, pkgutil, pathlib, random, time, math, csv
from typing import List, Dict, Tuple
from core.types import Shape, Player, Piece
from core.rules import QuantikBoard

# =======================
# Paramètres du tournoi
# =======================
GAMES_PER_PAIR = 50          # nb de parties par confrontation (au total A vs B)
INCLUDE_SELF_PLAY = True     # True => inclure IA vs elle-même
BASE_SEED = 42               # graine globale
CSV_LOG = False              # True => export CSV, sinon laissé commenté plus bas
CSV_PATH = "tournament_results.csv"

# =======================
# Découverte des IA
# =======================
def discover_ais():
    """Retourne une liste [{name, cls}] des IA trouvées."""
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

# =======================
# Utilitaires statistiques
# =======================
def wilson_interval(k: int, n: int, z: float = 1.96) -> Tuple[float, float, float]:
    """Intervalle de Wilson pour une proportion k/n (95% si z=1.96)."""
    if n == 0:
        return 0.0, 0.0, 0.0
    phat = k / n
    denom = 1 + z*z/n
    center = (phat + z*z/(2*n)) / denom
    margin = (z * math.sqrt((phat*(1-phat) + z*z/(4*n)) / n)) / denom
    return phat, max(0.0, center - margin), min(1.0, center + margin)

def expected_score(elo_a: float, elo_b: float) -> float:
    return 1.0 / (1.0 + 10 ** ((elo_b - elo_a) / 400.0))

def update_elo(elo_a: float, elo_b: float, score_a: float, k: float = 20.0) -> Tuple[float,float]:
    ea = expected_score(elo_a, elo_b)
    eb = 1.0 - ea
    return elo_a + k*(score_a - ea), elo_b + k*((1.0 - score_a) - eb)

# =======================
# Moteur de match
# =======================
def play_one_game(aiA_cls, aiB_cls, first: Player = Player.PLAYER1, seed: int = None) -> Player:
    """
    Joue une partie:
      - aiA = Player1, aiB = Player2 (peu importe 'first', on alterne le droit de commencer)
      - 'first' indique qui joue le premier coup effectif
      - on passe 'board.board' aux IA (compatible GUI)
    """
    if seed is not None:
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
        # NOTE: si votre QuantikBoard expose board.raw(), remplacez ci-dessous par board.raw()
        move = ai.get_move(board.board, pieces)
        if not move:
            # pas de coup => l'autre gagne
            return Player.PLAYER2 if current == Player.PLAYER1 else Player.PLAYER1

        r, c, shape = move
        if not board.place_piece(r, c, Piece(shape, current)):
            # coup invalide => défaite immédiate
            return Player.PLAYER2 if current == Player.PLAYER1 else Player.PLAYER1

        pieces[current][shape] -= 1
        if board.check_victory():
            return current

        # Alternance du joueur
        current = Player.PLAYER2 if current == Player.PLAYER1 else Player.PLAYER1

def play_pair(iaA, iaB, games: int, base_seed: int) -> Tuple[int,int,float]:
    """
    Joue 'games' parties entre iaA et iaB, en alternant le premier joueur.
    Retourne (winsA, winsB, elapsed_seconds).
    """
    t0 = time.time()
    winsA = winsB = 0
    for g in range(games):
        first = Player.PLAYER1 if (g % 2 == 0) else Player.PLAYER2
        # Seed reprod. dépendante des noms + index de partie
        seed = (hash((iaA["name"], iaB["name"])) ^ (base_seed + g)) & 0x7FFFFFFF
        winner = play_one_game(iaA["cls"], iaB["cls"], first, seed)
        # Attribution: si winner == côté qui a "l'identité" de A ?
        # Ici, A est toujours Player1 par construction du moteur play_one_game,
        # mais 'first' peut être P1 ou P2. On s'en moque: winner est un Player.
        if winner == Player.PLAYER1:
            # Player1 est l'IA A
            winsA += 1
        else:
            winsB += 1
    elapsed = time.time() - t0
    return winsA, winsB, elapsed

# =======================
# Tournoi complet
# =======================
def main():
    random.seed(BASE_SEED)

    ais = discover_ais()
    names = [a["name"] for a in ais]
    print(f"IAs découvertes ({len(ais)}): {names}")

    if CSV_LOG:
        # Entête CSV (désactivez CSV_LOG=False si vous voulez réellement écrire le fichier)
        with open(CSV_PATH, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["A", "B", "games", "winsA", "winsB", "wrA", "ci_low", "ci_high", "seconds"])

    # Stats cumulées
    agg = {a["name"]: {"W": 0, "L": 0} for a in ais}
    # Elo
    elo = {a["name"]: 1000.0 for a in ais}
    # Matrice (A bat B)
    matrix = {a["name"]: {b["name"]: (0,0) for b in ais} for a in ais}

    # Boucle de confrontations (y compris self-play si demandé)
    for i in range(len(ais)):
        for j in range(len(ais)):
            if i < j or (i == j and INCLUDE_SELF_PLAY):
                A, B = ais[i], ais[j]
                winsA, winsB, elapsed = play_pair(A, B, GAMES_PER_PAIR, BASE_SEED)

                # Winrate + IC
                wr, lo, hi = wilson_interval(winsA, winsA + winsB)

                # Elo (mise à jour bilatérale, score = wins/total)
                # NB: sur un batch, on peut faire une seule mise à jour agrégée
                scoreA = winsA / max(1, (winsA + winsB))
                elo[A["name"]], elo[B["name"]] = update_elo(elo[A["name"]], elo[B["name"]], scoreA, k=24.0)

                # Agrégation
                agg[A["name"]]["W"] += winsA
                agg[A["name"]]["L"] += winsB
                agg[B["name"]]["W"] += winsB
                agg[B["name"]]["L"] += winsA

                # Matrice
                matrix[A["name"]][B["name"]] = (winsA, winsB)

                # Affichage par duel
                print(f"{A['name']} vs {B['name']} -> {winsA}-{winsB} sur {GAMES_PER_PAIR} "
                      f"| WR(A)={wr:.3f} (95% CI: {lo:.3f}-{hi:.3f}) | {elapsed:.1f}s")

                # CSV (optionnel)
                if CSV_LOG:
                    with open(CSV_PATH, "a", newline="", encoding="utf-8") as f:
                        w = csv.writer(f)
                        w.writerow([A["name"], B["name"], GAMES_PER_PAIR, winsA, winsB,
                                    f"{wr:.3f}", f"{lo:.3f}", f"{hi:.3f}", f"{elapsed:.3f}"])

    # Résumé agrégé
    print("\n=== Résumé agrégé par IA (winrate cumulé) ===")
    rows = []
    for name in names:
        W, L = agg[name]["W"], agg[name]["L"]
        wr, lo, hi = wilson_interval(W, W+L) if (W+L)>0 else (0.0,0.0,0.0)
        rows.append((name, W, L, wr, lo, hi))
    rows.sort(key=lambda x: x[3], reverse=True)
    for (name, W, L, wr, lo, hi) in rows:
        print(f"{name:<28} {W:>4}-{L:<4}  WR={wr:.3f}  (95% CI {lo:.3f}-{hi:.3f})")

    # Classement Elo (approx.)
    print("\n=== Classement ELO (approx.) ===")
    for name, rating in sorted(elo.items(), key=lambda x: x[1], reverse=True):
        print(f"{name:<26} ELO={rating:.1f}")

    # Matrice
    print("\n=== Matrice de confrontations (A bat B) ===")
    # En-tête
    header = "                         | " + " | ".join(f"{n[:12]:>12}" for n in names)
    print(header)
    print("-" * len(header))
    for a in names:
        line = f"{a[:25]:<25} | "
        for b in names:
            wA, wB = matrix[a][b]
            if a == b and not INCLUDE_SELF_PLAY:
                cell = "   —   "
            else:
                cell = f"{wA:>2}-{wB:<2}"
            line += f"{cell:>12} | "
        print(line)

if __name__ == "__main__":
    main()
