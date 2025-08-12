# tournament/runner.py
# ----------------------------------------------------------
# Tournoi IA vs IA (sans interface) avec métriques utiles :
#  - A est TOUJOURS Player1, B est TOUJOURS Player2
#  - On alterne qui COMMENCE la partie (starter)
#  - On affiche :
#       * taux de victoire de A (+ intervalle de confiance 95%)
#       * StartsWon(A) : victoires de A quand A commence
#       * RepliesWon(A) : victoires de A quand B commence (A répond)
#  - Résumé agrégé, ELO approximatif et matrice des confrontations
#  - Détection et exclusion d’IA “muettes” (aucun coup au départ)
#  - Export CSV laissé en commentaire (décommentez si besoin)
# ----------------------------------------------------------
from __future__ import annotations
import time, math, random, threading
from typing import List, Dict, Tuple, Optional
from core.types import Shape, Player, Piece
from core.rules import QuantikBoard
import importlib, pkgutil, pathlib

# -------- Utilitaires plateau --------
def raw_board(board: QuantikBoard):
    """Retourne la matrice 4x4 (compatibilité : .raw() ou .board)."""
    if hasattr(board, "raw"):
        return board.raw()
    return board.board

def empty_position():
    """Crée un plateau vide + stocks initiaux (pour tests/probes)."""
    b = QuantikBoard()
    pieces = {
        Player.PLAYER1: {s: 2 for s in Shape},
        Player.PLAYER2: {s: 2 for s in Shape},
    }
    return b, pieces

# -------- Découverte des IA disponibles --------
def discover_ais():
    """
    Cherche ai_players/*/algorithme.py, charge QuantikAI et AI_NAME.
    Exclut 'template' par convention.
    """
    base_pkg = "ai_players"
    base_path = pathlib.Path(__file__).resolve().parents[1] / base_pkg
    ais = []
    errors = []

    if not base_path.exists():
        return [], ["(ai_players manquant)"]

    for pkg in pkgutil.iter_modules([str(base_path)]):
        if pkg.name == "template":
            continue  # on ignore le modèle
        mod_name = f"{base_pkg}.{pkg.name}.algorithme"
        try:
            mod = importlib.import_module(mod_name)
            ai_cls  = getattr(mod, "QuantikAI", None)
            ai_name = getattr(mod, "AI_NAME", pkg.name)
            if ai_cls:
                ais.append({"name": ai_name, "cls": ai_cls})
            else:
                errors.append(f"{mod_name} (QuantikAI introuvable)")
        except Exception as e:
            errors.append(f"{mod_name} (erreur import: {e})")

    ais.sort(key=lambda x: x["name"].lower())
    return ais, errors

# -------- Probe rapide pour exclure IA “muettes” --------
def probe_ai_speaks(ai_cls, timeout: float = 2.0) -> bool:
    """
    Tente d’obtenir UN coup légal sur la position initiale.
    Retourne True si l’IA propose un coup; False si None / timeout / exception.
    """
    b, pieces = empty_position()
    board_raw = raw_board(b)
    result_container = {"ok": False}

    def worker():
        try:
            ai = ai_cls(Player.PLAYER1)
            mv = ai.get_move(board_raw, pieces)
            if mv is None:
                result_container["ok"] = False
                return
            r, c, sh = mv
            # Vérifie qu’on peut au moins tenter de jouer (pas besoin d’être parfait)
            ok = b.place_piece(r, c, Piece(sh, Player.PLAYER1))
            result_container["ok"] = bool(ok)
        except Exception:
            result_container["ok"] = False

    t = threading.Thread(target=worker, daemon=True)
    t.start()
    t.join(timeout)
    return result_container["ok"]

def filter_mute_ais(ais, do_filter: bool = True):
    """
    Si do_filter=True, élimine les IA qui ne “parlent” pas au probe.
    """
    if not do_filter:
        return ais, []
    kept, excluded = [], []
    for a in ais:
        if probe_ai_speaks(a["cls"]):
            kept.append(a)
        else:
            excluded.append(a["name"])
    return kept, excluded

# -------- Une partie IA vs IA --------
def play_one_game(aiA_cls, aiB_cls, starter: Player) -> Tuple[Player, Dict[str,int]]:
    """
    A = Player1, B = Player2.
    'starter' indique qui joue le PREMIER coup (peut être A (P1) ou B (P2)).
    Renvoie (winner, stats_locaux) où stats_locaux inclut:
      - 'A_started': 1 si A a commencé, sinon 0
      - 'A_won_start': 1 si A a commencé et a gagné, sinon 0
      - 'A_won_reply': 1 si B a commencé et A a gagné, sinon 0
    """
    board = QuantikBoard()
    pieces = {
        Player.PLAYER1: {s: 2 for s in Shape},
        Player.PLAYER2: {s: 2 for s in Shape},
    }
    aiA = aiA_cls(Player.PLAYER1)
    aiB = aiB_cls(Player.PLAYER2)

    current = starter
    A_started = 1 if starter == Player.PLAYER1 else 0
    A_won_start = 0
    A_won_reply = 0

    while True:
        ai = aiA if current == Player.PLAYER1 else aiB
        move = ai.get_move(raw_board(board), pieces)
        if not move:
            # pas de coup => l'autre gagne
            winner = Player.PLAYER2 if current == Player.PLAYER1 else Player.PLAYER1
            if winner == Player.PLAYER1:
                if A_started: A_won_start = 1
                else:         A_won_reply = 1
            return winner, {
                "A_started": A_started,
                "A_won_start": A_won_start,
                "A_won_reply": A_won_reply,
            }

        r, c, shape = move
        if not board.place_piece(r, c, Piece(shape, current)):
            # coup invalide proposé => perd
            winner = Player.PLAYER2 if current == Player.PLAYER1 else Player.PLAYER1
            if winner == Player.PLAYER1:
                if A_started: A_won_start = 1
                else:         A_won_reply = 1
            return winner, {
                "A_started": A_started,
                "A_won_start": A_won_start,
                "A_won_reply": A_won_reply,
            }

        pieces[current][shape] -= 1
        if board.check_victory():
            winner = current
            if winner == Player.PLAYER1:
                if A_started: A_won_start = 1
                else:         A_won_reply = 1
            return winner, {
                "A_started": A_started,
                "A_won_start": A_won_start,
                "A_won_reply": A_won_reply,
            }

        current = Player.PLAYER2 if current == Player.PLAYER1 else Player.PLAYER1

# -------- Statistiques / Affichages --------
def wilson_interval(wins: int, total: int, z: float = 1.96) -> Tuple[float,float]:
    if total == 0:
        return (0.0, 0.0)
    p = wins / total
    denom = 1 + z*z/total
    centre = p + z*z/(2*total)
    margin = z * math.sqrt((p*(1-p)+z*z/(4*total))/total)
    lo = (centre - margin)/denom
    hi = (centre + margin)/denom
    lo = max(0.0, lo)
    hi = min(1.0, hi)
    return lo, hi

def elo_update(ra: float, rb: float, sa: float, k: float = 16.0) -> Tuple[float,float]:
    """Mise à jour ELO simple, sa=1 si A gagne, 0 si A perd, 0.5 si nul (non utilisé ici)."""
    ea = 1 / (1 + 10 ** ((rb - ra) / 400))
    eb = 1 - ea
    ra2 = ra + k * (sa - ea)
    rb2 = rb + k * ((1 - sa) - eb)
    return ra2, rb2

# -------- Tournoi pairwise --------
def run_pair(iaA: Dict, iaB: Dict, games: int = 50, seed: Optional[int] = None):
    if seed is not None:
        random.seed(seed)

    Aname, Bname = iaA["name"], iaB["name"]
    wA = wB = 0
    A_starts_won = 0
    A_replies_won = 0

    t0 = time.time()
    for g in range(games):
        # Alternance du starter : parties paires => A commence, impaires => B commence
        starter = Player.PLAYER1 if (g % 2 == 0) else Player.PLAYER2
        winner, loc = play_one_game(iaA["cls"], iaB["cls"], starter)

        if winner == Player.PLAYER1:
            wA += 1
            A_starts_won  += loc["A_won_start"]
            A_replies_won += loc["A_won_reply"]
        else:
            wB += 1

    elapsed = time.time() - t0
    wr = wA / games if games > 0 else 0.0
    lo, hi = wilson_interval(wA, games)
    print(f"{Aname} vs {Bname} -> {wA}-{wB} sur {games} | "
          f"WR(A)={wr:.3f} (95% CI: {lo:.3f}-{hi:.3f}) | "
          f"StartsWon(A)={A_starts_won}, RepliesWon(A)={A_replies_won} | "
          f"{elapsed:.1f}s")

    return {
        "A": Aname, "B": Bname,
        "wA": wA, "wB": wB, "games": games,
        "wrA": wr, "ci_low": lo, "ci_high": hi,
        "time": elapsed,
        "A_starts_won": A_starts_won,
        "A_replies_won": A_replies_won,
    }

def aggregate(results: List[Dict]):
    # Totaux par IA
    totals: Dict[str, Dict] = {}
    for r in results:
        for side in ("A", "B"):
            name = r[side]
            if name not in totals:
                totals[name] = {"wins":0, "losses":0}
        totals[r["A"]]["wins"]  += r["wA"]
        totals[r["A"]]["losses"]+= r["wB"]
        totals[r["B"]]["wins"]  += r["wB"]
        totals[r["B"]]["losses"]+= r["wA"]

    print("\n=== Résumé agrégé par IA (winrate cumulé) ===")
    lines = []
    for name, t in totals.items():
        w, l = t["wins"], t["losses"]
        g = w + l
        wr = w/g if g>0 else 0.0
        lo, hi = wilson_interval(w, g)
        lines.append((name, w, l, wr, lo, hi))
    lines.sort(key=lambda x: x[3], reverse=True)
    for (name, w, l, wr, lo, hi) in lines:
        print(f"{name:28s} {w:4d}-{l:<4d}  WR={wr:.3f}  (95% CI {lo:.3f}-{hi:.3f})")

    # ELO approx. (round-robin, K fixe)
    elo = {name: 1000.0 for name in totals.keys()}
    for r in results:
        A, B = r["A"], r["B"]
        wA, wB = r["wA"], r["wB"]
        for _ in range(wA): elo[A], elo[B] = elo_update(elo[A], elo[B], 1.0)
        for _ in range(wB): elo[A], elo[B] = elo_update(elo[A], elo[B], 0.0)

    print("\n=== Classement ELO (approx.) ===")
    for name, rating in sorted(elo.items(), key=lambda kv: kv[1], reverse=True):
        print(f"{name:28s} ELO={rating:.1f}")

    # Matrice de confrontations
    names = sorted(totals.keys())
    idx = {n:i for i,n in enumerate(names)}
    M = [[None for _ in names] for _ in names]
    for r in results:
        i, j = idx[r["A"]], idx[r["B"]]
        M[i][j] = f"{r['wA']:>3d}-{r['wB']:<3d}"

    print("\n=== Matrice de confrontations (A bat B) ===")
    header = "                         | " + " | ".join(f"{n[:12]:>12s}" for n in names)
    print(header)
    print("-" * len(header))
    for i, ni in enumerate(names):
        row = f"{ni[:25]:<25} | "
        row += " | ".join(f"{(M[i][j] or ''):>12s}" for j in range(len(names)))
        print(row)

    # ----- Export CSV (optionnel) -----
    # Décommentez pour enregistrer un CSV détaillé.
    # import csv
    # with open("tournament_results.csv", "w", newline="", encoding="utf-8") as f:
    #     w = csv.writer(f)
    #     w.writerow(["A","B","wA","wB","games","wrA","ci_low","ci_high","time","A_starts_won","A_replies_won"])
    #     for r in results:
    #         w.writerow([r["A"], r["B"], r["wA"], r["wB"], r["games"], f"{r['wrA']:.3f}",
    #                     f"{r['ci_low']:.3f}", f"{r['ci_high']:.3f}", f"{r['time']:.2f}",
    #                     r["A_starts_won"], r["A_replies_won"]])

def main():
    # Paramètres du tournoi
    GAMES_PER_PAIR = 100
    SEED = 42      # fixez None pour tirage différent à chaque run
    FILTER_MUTE = True  # exclure automatiquement les IA “muettes”
    if SEED is not None:
        random.seed(SEED)

    ais, import_errors = discover_ais()
    ais, mute_excluded = filter_mute_ais(ais, do_filter=FILTER_MUTE)

    print(f"IAs découvertes ({len(ais)}): {[a['name'] for a in ais]}")
    if import_errors:
        print(f"⚠️  Erreurs d’import: {import_errors}")
    if FILTER_MUTE and mute_excluded:
        print(f"⚠️  Exclues (muettes au probe): {mute_excluded}")

    results = []
    for i in range(len(ais)):
        for j in range(i+1, len(ais)):
            r = run_pair(ais[i], ais[j], games=GAMES_PER_PAIR, seed=SEED)
            results.append(r)

    aggregate(results)

if __name__ == "__main__":
    main()
