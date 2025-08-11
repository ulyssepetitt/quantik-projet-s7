# tournament/runner.py
# ----------------------------------------------------------
# Lance des matchs IA vs IA en batch (sans interface graphique).
# Utilise le même moteur et la même API que la GUI.
# ----------------------------------------------------------
from core.types import Shape, Player, Piece
from core.rules import QuantikBoard
import importlib, pkgutil, pathlib

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

def play_one_game(aiA_cls, aiB_cls, first: Player = Player.PLAYER1) -> Player:
    board = QuantikBoard()
    pieces = {Player.PLAYER1: {s: 2 for s in Shape}, Player.PLAYER2: {s: 2 for s in Shape}}
    aiA = aiA_cls(Player.PLAYER1)
    aiB = aiB_cls(Player.PLAYER2)
    current = first

    while True:
        ai = aiA if current == Player.PLAYER1 else aiB
        move = ai.get_move(board.raw(), pieces)
        if not move:
            # pas de coup => l'autre gagne
            return Player.PLAYER2 if current == Player.PLAYER1 else Player.PLAYER1
        r, c, shape = move
        if not board.place_piece(r, c, Piece(shape, current)):
            # coup invalide proposé => perd
            return Player.PLAYER2 if current == Player.PLAYER1 else Player.PLAYER1
        pieces[current][shape] -= 1
        if board.check_victory():
            return current
        current = Player.PLAYER2 if current == Player.PLAYER1 else Player.PLAYER1

def main():
    ais = discover_ais()
    print(f"IAs découvertes: {[a['name'] for a in ais]}")
    GAMES = 20
    for i in range(len(ais)):
        for j in range(i+1, len(ais)):
            A, B = ais[i], ais[j]
            wA = wB = 0
            for g in range(GAMES):
                first = Player.PLAYER1 if g % 2 == 0 else Player.PLAYER2
                winner = play_one_game(A["cls"], B["cls"], first)
                if (winner == Player.PLAYER1 and first == Player.PLAYER1) or \
                   (winner == Player.PLAYER2 and first == Player.PLAYER2):
                    wA += 1
                else:
                    wB += 1
            print(f"{A['name']} vs {B['name']} -> {wA}-{wB} sur {GAMES}")

if __name__ == "__main__":
    main()