# ai_players/ulysse/test_suite.py
# -------------------------------------------------------------------
# Suite de tests automatisés pour l'algorithme Quantik v4.0
# Tests de régression et validation complète
# -------------------------------------------------------------------
import sys
import time
import traceback
from pathlib import Path

# Ajouter le répertoire racine au path pour les imports
sys.path.append(str(Path(__file__).resolve().parents[2]))

from core.types import Shape, Player, Piece
from core.rules import QuantikBoard
from ai_players.ulysse.algorithme import QuantikAI
from ai_players.random.algorithme import QuantikAI as RandomAI

class TestResults:
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.errors = []
    
    def pass_test(self, test_name):
        self.passed += 1
        print(f"✅ {test_name}")
    
    def fail_test(self, test_name, reason):
        self.failed += 1
        self.errors.append(f"{test_name}: {reason}")
        print(f"❌ {test_name} - {reason}")
    
    def summary(self):
        total = self.passed + self.failed
        print(f"\n📊 RÉSULTATS: {self.passed}/{total} tests réussis")
        if self.errors:
            print("\n🚨 ERREURS:")
            for error in self.errors:
                print(f"   - {error}")
        return self.failed == 0

class QuantikTestSuite:
    def __init__(self):
        self.results = TestResults()
    
    def run_all_tests(self):
        """Lance tous les tests automatisés"""
        print("🔬 SUITE DE TESTS QUANTIK v4.0")
        print("=" * 50)
        
        # Tests de base
        self.test_move_generation()
        self.test_rule_validation()
        self.test_position_evaluation()
        
        # Tests de régression
        self.test_bug_regression_case1()  # Cas qui causait le bug
        self.test_bug_regression_case2()  # Autre cas problématique
        
        # Tests tactiques
        self.test_immediate_victory()
        self.test_threat_blocking()
        self.test_depth_adaptation()
        
        # Tests de performance
        self.test_timeout_handling()
        self.test_emergency_fallback()
        
        # Simulation de parties
        self.test_vs_random_games()
        
        return self.results.summary()
    
    def test_move_generation(self):
        """Test du générateur de coups"""
        print("\n🔍 Tests générateur de coups:")
        
        try:
            ai = QuantikAI(Player.PLAYER1)
            
            # Test 1: Plateau vide
            board = QuantikBoard()
            moves = ai._generate_all_valid_moves(board, Player.PLAYER1)
            
            expected_moves = 4 * 4 * 4  # 16 cases × 4 formes
            if len(moves) == expected_moves:
                self.results.pass_test("Plateau vide - 64 coups")
            else:
                self.results.fail_test("Plateau vide", f"Attendu {expected_moves}, obtenu {len(moves)}")
            
            # Test 2: Avec contraintes
            board.place_piece(0, 0, Piece(Shape.CIRCLE, Player.PLAYER2))
            moves = ai._generate_all_valid_moves(board, Player.PLAYER1)
            
            # Vérifier qu'aucun coup CIRCLE n'est possible ligne 0, colonne 0, zone 0
            invalid_circles = [
                (r, c, s) for r, c, s in moves 
                if s == Shape.CIRCLE and (r == 0 or c == 0 or (r < 2 and c < 2))
            ]
            
            if len(invalid_circles) == 0:
                self.results.pass_test("Contraintes règles appliquées")
            else:
                self.results.fail_test("Contraintes règles", f"{len(invalid_circles)} coups invalides trouvés")
                
        except Exception as e:
            self.results.fail_test("Générateur coups", f"Exception: {str(e)}")
    
    def test_rule_validation(self):
        """Test de validation des règles Quantik"""
        print("\n📏 Tests validation règles:")
        
        try:
            ai = QuantikAI(Player.PLAYER1)
            board = QuantikBoard()
            
            # Placer une pièce adversaire
            board.place_piece(1, 1, Piece(Shape.SQUARE, Player.PLAYER2))
            
            # Test ligne
            is_valid = ai._is_move_valid(board, 1, 2, Piece(Shape.SQUARE, Player.PLAYER1))
            if not is_valid:
                self.results.pass_test("Règle ligne - interdit même forme adversaire")
            else:
                self.results.fail_test("Règle ligne", "Devrait être invalide")
            
            # Test même joueur autorisé
            is_valid = ai._is_move_valid(board, 1, 2, Piece(Shape.SQUARE, Player.PLAYER2))
            if is_valid:
                self.results.pass_test("Même joueur - autorisé même forme")
            else:
                self.results.fail_test("Même joueur", "Devrait être valide")
                
        except Exception as e:
            self.results.fail_test("Validation règles", f"Exception: {str(e)}")
    
    def test_position_evaluation(self):
        """Test de l'évaluateur de position"""
        print("\n⚖️ Tests évaluation position:")
        
        try:
            ai = QuantikAI(Player.PLAYER1)
            
            # Position neutre
            board = QuantikBoard()
            score = ai._evaluate_position(board)
            
            if score == 0.0:
                self.results.pass_test("Position neutre = 0")
            else:
                self.results.fail_test("Position neutre", f"Score {score}, attendu 0")
            
            # Position avantageuse (centre)
            board.place_piece(1, 1, Piece(Shape.CIRCLE, Player.PLAYER1))
            score_center = ai._evaluate_position(board)
            
            if score_center > 0:
                self.results.pass_test("Centre avantageux > 0")
            else:
                self.results.fail_test("Centre avantageux", f"Score {score_center} <= 0")
                
        except Exception as e:
            self.results.fail_test("Évaluation position", f"Exception: {str(e)}")
    
    def test_bug_regression_case1(self):
        """Test du cas qui causait le bug critique"""
        print("\n🐛 Test régression bug critique:")
        
        try:
            # Reconstruire la position exacte du bug
            board = QuantikBoard()
            board.place_piece(0, 1, Piece(Shape.CIRCLE, Player.PLAYER1))      # 1R(0,1)
            board.place_piece(1, 0, Piece(Shape.SQUARE, Player.PLAYER2))      # 2C(1,0)  
            board.place_piece(1, 1, Piece(Shape.TRIANGLE, Player.PLAYER1))    # 1T(1,1)
            board.place_piece(0, 0, Piece(Shape.DIAMOND, Player.PLAYER2))     # 2L(0,0)
            
            # L'IA ne doit PAS être bloquée
            ai = QuantikAI(Player.PLAYER2)
            pieces_count = {Player.PLAYER1: {s: 2 for s in Shape}, Player.PLAYER2: {s: 2 for s in Shape}}
            
            # Vérifier qu'elle trouve des coups
            valid_moves = ai._generate_all_valid_moves(board, Player.PLAYER2)
            if len(valid_moves) > 0:
                self.results.pass_test(f"Coups disponibles: {len(valid_moves)}")
            else:
                self.results.fail_test("Coups disponibles", "Aucun coup trouvé")
                return
            
            # Vérifier qu'elle retourne un coup
            ai.max_time = 2.0  # Test rapide
            move = ai.get_move(board.board, pieces_count)
            
            if move is not None:
                self.results.pass_test("IA retourne un coup valide")
                
                # Vérifier que le coup est vraiment valide
                row, col, shape = move
                if ai._is_move_valid(board, row, col, Piece(shape, Player.PLAYER2)):
                    self.results.pass_test("Coup retourné est valide selon règles")
                else:
                    self.results.fail_test("Coup retourné", "Invalide selon règles Quantik")
            else:
                self.results.fail_test("IA retourne coup", "None retourné malgré coups disponibles")
                
        except Exception as e:
            self.results.fail_test("Bug régression", f"Exception: {str(e)}")
            traceback.print_exc()
    
    def test_bug_regression_case2(self):
        """Test d'un autre cas problématique"""
        print("\n🐛 Test régression cas général:")
        
        try:
            # Position en fin de partie
            board = QuantikBoard()
            # Remplir presque tout le plateau
            pieces = [
                (0, 0, Shape.CIRCLE, Player.PLAYER1),
                (0, 1, Shape.SQUARE, Player.PLAYER2),
                (0, 2, Shape.TRIANGLE, Player.PLAYER1),
                # (0, 3) libre
                (1, 0, Shape.SQUARE, Player.PLAYER1),
                (1, 1, Shape.TRIANGLE, Player.PLAYER2),
                (1, 2, Shape.DIAMOND, Player.PLAYER1),
                (1, 3, Shape.CIRCLE, Player.PLAYER2),
                (2, 0, Shape.TRIANGLE, Player.PLAYER2),
                (2, 1, Shape.DIAMOND, Player.PLAYER1),
                (2, 2, Shape.CIRCLE, Player.PLAYER2),
                (2, 3, Shape.SQUARE, Player.PLAYER1),
                (3, 0, Shape.DIAMOND, Player.PLAYER2),
                (3, 1, Shape.CIRCLE, Player.PLAYER1),
                (3, 2, Shape.SQUARE, Player.PLAYER2),
                # (3, 3) libre
            ]
            
            for row, col, shape, player in pieces:
                board.place_piece(row, col, Piece(shape, player))
            
            # Test que l'IA trouve encore des coups
            ai = QuantikAI(Player.PLAYER1)
            pieces_count = {Player.PLAYER1: {s: 2 for s in Shape}, Player.PLAYER2: {s: 2 for s in Shape}}
            
            valid_moves = ai._generate_all_valid_moves(board, Player.PLAYER1)
            ai.max_time = 1.0
            move = ai.get_move(board.board, pieces_count)
            
            if valid_moves and move:
                self.results.pass_test("Fin de partie - IA fonctionne")
            elif not valid_moves and move is None:
                self.results.pass_test("Fin de partie - Aucun coup correctement détecté")
            else:
                self.results.fail_test("Fin de partie", f"Incohérence: {len(valid_moves)} coups, move={move}")
                
        except Exception as e:
            self.results.fail_test("Cas fin de partie", f"Exception: {str(e)}")
    
    def test_immediate_victory(self):
        """Test détection victoire immédiate"""
        print("\n🏆 Test victoire immédiate:")
        
        try:
            board = QuantikBoard()
            # Configuration: J2 peut gagner en (0,3)
            board.place_piece(0, 0, Piece(Shape.CIRCLE, Player.PLAYER2))
            board.place_piece(0, 1, Piece(Shape.SQUARE, Player.PLAYER2))  
            board.place_piece(0, 2, Piece(Shape.TRIANGLE, Player.PLAYER2))
            # (0,3) libre pour DIAMOND
            
            ai = QuantikAI(Player.PLAYER2)
            pieces_count = {Player.PLAYER1: {s: 2 for s in Shape}, Player.PLAYER2: {s: 2 for s in Shape}}
            ai.max_time = 1.0
            
            move = ai.get_move(board.board, pieces_count)
            
            if move and move[0] == 0 and move[1] == 3 and move[2] == Shape.DIAMOND:
                self.results.pass_test("Détecte et joue victoire immédiate")
            elif move:
                self.results.fail_test("Victoire immédiate", f"Joue {move} au lieu de (0,3,DIAMOND)")
            else:
                self.results.fail_test("Victoire immédiate", "Aucun coup retourné")
                
        except Exception as e:
            self.results.fail_test("Victoire immédiate", f"Exception: {str(e)}")
    
    def test_threat_blocking(self):
        """Test blocage des menaces"""
        print("\n🛡️ Test blocage menaces:")
        
        try:
            board = QuantikBoard()
            # J1 menace sur colonne 1
            board.place_piece(0, 1, Piece(Shape.CIRCLE, Player.PLAYER1))
            board.place_piece(2, 1, Piece(Shape.TRIANGLE, Player.PLAYER1))
            # Menace en (1,1) ou (3,1)
            
            ai = QuantikAI(Player.PLAYER2)
            pieces_count = {Player.PLAYER1: {s: 2 for s in Shape}, Player.PLAYER2: {s: 2 for s in Shape}}
            ai.max_time = 1.0
            
            move = ai.get_move(board.board, pieces_count)
            
            if move and move[1] == 1:  # Bloque colonne 1
                self.results.pass_test("Bloque menace en développement")
            elif move:
                self.results.fail_test("Blocage menace", f"Joue {move} au lieu de bloquer colonne 1")
            else:
                self.results.fail_test("Blocage menace", "Aucun coup retourné")
                
        except Exception as e:
            self.results.fail_test("Blocage menace", f"Exception: {str(e)}")
    
    def test_depth_adaptation(self):
        """Test adaptation profondeur selon stade"""
        print("\n📊 Test profondeur adaptative:")
        
        try:
            ai = QuantikAI(Player.PLAYER1)
            
            # Ouverture (0-4 pièces)
            depth_opening = ai._calculate_optimal_depth(2)
            
            # Milieu (5-10 pièces)  
            depth_middle = ai._calculate_optimal_depth(7)
            
            # Fin (11+ pièces)
            depth_endgame = ai._calculate_optimal_depth(13)
            
            if depth_opening < depth_middle < depth_endgame:
                self.results.pass_test(f"Profondeur croissante: {depth_opening} → {depth_middle} → {depth_endgame}")
            else:
                self.results.fail_test("Profondeur adaptative", f"Non croissante: {depth_opening}, {depth_middle}, {depth_endgame}")
                
        except Exception as e:
            self.results.fail_test("Profondeur adaptative", f"Exception: {str(e)}")
    
    def test_timeout_handling(self):
        """Test gestion timeout"""
        print("\n⏱️ Test gestion timeout:")
        
        try:
            ai = QuantikAI(Player.PLAYER1)
            ai.max_time = 0.1  # Très court
            
            board = QuantikBoard()
            pieces_count = {Player.PLAYER1: {s: 2 for s in Shape}, Player.PLAYER2: {s: 2 for s in Shape}}
            
            start_time = time.time()
            move = ai.get_move(board.board, pieces_count)
            elapsed = time.time() - start_time
            
            if move and elapsed <= 0.5:  # Marge de sécurité
                self.results.pass_test(f"Timeout respecté: {elapsed:.3f}s")
            elif move:
                self.results.fail_test("Timeout", f"Trop long: {elapsed:.3f}s")
            else:
                self.results.fail_test("Timeout", "Aucun coup retourné")
                
        except Exception as e:
            self.results.fail_test("Gestion timeout", f"Exception: {str(e)}")
    
    def test_emergency_fallback(self):
        """Test fallback d'urgence"""
        print("\n🚨 Test fallback urgence:")
        
        try:
            ai = QuantikAI(Player.PLAYER1)
            board = QuantikBoard()
            
            # Simuler une situation où minimax échoue
            valid_moves = [(1, 1, Shape.CIRCLE), (1, 2, Shape.SQUARE)]
            
            emergency_move = ai._emergency_move_selection(board, valid_moves)
            
            if emergency_move in valid_moves:
                self.results.pass_test("Fallback retourne coup valide")
            else:
                self.results.fail_test("Fallback", f"Coup invalide: {emergency_move}")
                
        except Exception as e:
            self.results.fail_test("Fallback urgence", f"Exception: {str(e)}")
    
    def test_vs_random_games(self):
        """Simulation de parties contre aléatoire"""
        print("\n🎲 Test parties vs Random:")
        
        try:
            wins = 0
            games = 10  # Nombre limité pour les tests
            
            for game_num in range(games):
                try:
                    winner = self.play_vs_random()
                    if winner == Player.PLAYER1:  # Notre IA
                        wins += 1
                except Exception:
                    # Partie annulée, ne compte pas
                    pass
            
            win_rate = wins / games if games > 0 else 0
            
            if win_rate >= 0.7:  # Au moins 70% contre aléatoire
                self.results.pass_test(f"Taux victoire: {win_rate:.1%} ({wins}/{games})")
            else:
                self.results.fail_test("Taux victoire", f"Seulement {win_rate:.1%} ({wins}/{games})")
                
        except Exception as e:
            self.results.fail_test("Parties vs Random", f"Exception: {str(e)}")
    
    def play_vs_random(self):
        """Joue une partie complète IA vs Random"""
        board = QuantikBoard()
        ai_smart = QuantikAI(Player.PLAYER1)
        ai_random = RandomAI(Player.PLAYER2)
        
        ai_smart.max_time = 1.0  # Limite pour tests
        current_player = Player.PLAYER1
        pieces_count = {Player.PLAYER1: {s: 2 for s in Shape}, Player.PLAYER2: {s: 2 for s in Shape}}
        
        for turn in range(32):  # Max 16 coups par joueur
            if current_player == Player.PLAYER1:
                move = ai_smart.get_move(board.board, pieces_count)
            else:
                move = ai_random.get_move(board.board, pieces_count)
            
            if move is None:
                break  # Aucun coup possible
            
            row, col, shape = move
            piece = Piece(shape, current_player)
            
            if not board.place_piece(row, col, piece):
                break  # Coup invalide
            
            if board.check_victory():
                return current_player
            
            current_player = Player.PLAYER2 if current_player == Player.PLAYER1 else Player.PLAYER1
        
        return None  # Match nul

def main():
    """Lance la suite de tests"""
    test_suite = QuantikTestSuite()
    success = test_suite.run_all_tests()
    
    if success:
        print("\n🎉 TOUS LES TESTS SONT PASSÉS!")
        print("L'algorithme v4.0 est prêt pour la production.")
    else:
        print("\n💥 CERTAINS TESTS ONT ÉCHOUÉ!")
        print("Corrections nécessaires avant utilisation.")
    
    return success

if __name__ == "__main__":
    main()