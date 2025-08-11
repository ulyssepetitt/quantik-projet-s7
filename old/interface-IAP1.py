import sys
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from enum import Enum
import time

# Import de l'IA (assure-toi que algorithme.py est dans le même dossier)
try:
    from algorithme import QuantikAI, Shape, Player, Piece
    print("✅ IA Expert chargée avec succès")
except ImportError as e:
    print(f"❌ Erreur import IA: {e}")
    # Versions locales de fallback
    class Shape(Enum):
        CIRCLE = "●"
        SQUARE = "■"
        TRIANGLE = "▲"
        DIAMOND = "♦️"
    
    class Player(Enum):
        PLAYER1 = 1
        PLAYER2 = 2
    
    class Piece:
        def __init__(self, shape, player):
            self.shape = shape
            self.player = player
        
        def __eq__(self, other):
            if isinstance(other, Piece):
                return self.shape == other.shape and self.player == other.player
            return False
    
    class QuantikAI:
        def __init__(self, player):
            pass
        def get_move(self, board, pieces_count):
            return None

class QuantikBoard:
    """Plateau de jeu QUANTIK"""
    def __init__(self):
        # Plateau 4x4 vide
        self.board = [[None for _ in range(4)] for _ in range(4)]
        
        # Définition des 4 zones carrées 2x2
        self.zones = [
            [(0,0), (0,1), (1,0), (1,1)],  # Zone top-left
            [(0,2), (0,3), (1,2), (1,3)],  # Zone top-right
            [(2,0), (2,1), (3,0), (3,1)],  # Zone bottom-left
            [(2,2), (2,3), (3,2), (3,3)]   # Zone bottom-right
        ]
    
    def get_zone(self, row, col):
        """Retourne l'index de la zone pour une position donnée"""
        for i, zone in enumerate(self.zones):
            if (row, col) in zone:
                return i
        return -1
    
    def is_valid_move(self, row, col, piece):
        """Vérifie si un coup est valide selon les règles"""
        # Case déjà occupée
        if self.board[row][col] is not None:
            return False
        
        # Vérifier la ligne
        for c in range(4):
            if (self.board[row][c] is not None and 
                self.board[row][c].shape == piece.shape and 
                self.board[row][c].player != piece.player):
                return False
        
        # Vérifier la colonne
        for r in range(4):
            if (self.board[r][col] is not None and 
                self.board[r][col].shape == piece.shape and 
                self.board[r][col].player != piece.player):
                return False
        
        # Vérifier la zone
        zone_idx = self.get_zone(row, col)
        if zone_idx != -1:
            for r, c in self.zones[zone_idx]:
                if (self.board[r][c] is not None and 
                    self.board[r][c].shape == piece.shape and 
                    self.board[r][c].player != piece.player):
                    return False
        
        return True
    
    def place_piece(self, row, col, piece):
        """Place une pièce sur le plateau"""
        if self.is_valid_move(row, col, piece):
            self.board[row][col] = piece
            return True
        return False
    
    def check_victory_line(self, line_pieces):
        """Vérifie si une ligne/colonne/zone contient 4 formes différentes"""
        if len(line_pieces) != 4:
            return False
        
        shapes = set()
        for piece in line_pieces:
            if piece is None:
                return False
            shapes.add(piece.shape)
        
        return len(shapes) == 4
    
    def check_victory(self):
        """Vérifie les conditions de victoire"""
        # Vérifier les lignes
        for row in range(4):
            if self.check_victory_line(self.board[row]):
                return True
        
        # Vérifier les colonnes
        for col in range(4):
            column = [self.board[row][col] for row in range(4)]
            if self.check_victory_line(column):
                return True
        
        # Vérifier les zones
        for zone in self.zones:
            zone_pieces = [self.board[r][c] for r, c in zone]
            if self.check_victory_line(zone_pieces):
                return True
        
        return False
    
    def has_valid_moves(self, player):
        """Vérifie si un joueur a encore des coups valides"""
        for shape in Shape:
            for row in range(4):
                for col in range(4):
                    piece = Piece(shape, player)
                    if self.is_valid_move(row, col, piece):
                        return True
        return False

class AIThinkingWorker(QThread):
    """Worker thread pour l'IA afin d'éviter de bloquer l'interface"""
    move_calculated = pyqtSignal(tuple)  # Signal émis quand l'IA a calculé son coup
    
    def __init__(self, ai, board, pieces_count):
        super().__init__()
        self.ai = ai
        self.board = board
        self.pieces_count = pieces_count
    
    def run(self):
        try:
            # Ajouter un délai minimum pour l'effet visuel
            time.sleep(1.5)
            
            # Calculer le coup de l'IA
            move = self.ai.get_move(self.board, self.pieces_count)
            
            if move:
                self.move_calculated.emit(move)
            else:
                # Émettre un tuple vide au lieu de None
                self.move_calculated.emit((-1, -1, None))
        except Exception as e:
            print(f"Erreur dans le calcul IA: {e}")
            # Émettre un tuple d'erreur au lieu de None
            self.move_calculated.emit((-1, -1, None))

class QuantikGame(QMainWindow):
    """Interface graphique du jeu QUANTIK vs IA"""
    
    def __init__(self):
        super().__init__()
        
        # Couleurs des joueurs
        self.player_colors = {
            Player.PLAYER1: {
                'primary': '#3498db',
                'secondary': '#2980b9',
                'light': '#85c1e9',
                'name': 'Vous (Bleu)'
            },
            Player.PLAYER2: {
                'primary': '#e74c3c',
                'secondary': '#c0392b',
                'light': '#f1948a',
                'name': 'IA (Rouge)'
            }
        }
        
        self.board = QuantikBoard()
        self.current_player = Player.PLAYER1
        self.selected_shape = None
        self.game_enabled = True  # Pour désactiver l'interface pendant que l'IA joue
        
        # Compteurs de pièces pour chaque joueur
        self.pieces_count = {
            Player.PLAYER1: {shape: 2 for shape in Shape},
            Player.PLAYER2: {shape: 2 for shape in Shape}
        }
        
        # Historique des coups pour le suivi de la partie
        self.move_history = []
        
        # Initialiser l'IA
        self.ai = QuantikAI(Player.PLAYER2)
        self.ai_worker = None
        
        self.init_ui()
        self.update_display()
    
    def format_shape_letter(self, shape):
        """Convertit une forme en lettre pour l'historique"""
        shape_mapping = {
            Shape.CIRCLE: 'R',      # Rond
            Shape.SQUARE: 'C',      # Carré
            Shape.TRIANGLE: 'T',    # Triangle
            Shape.DIAMOND: 'L'      # Losange
        }
        return shape_mapping.get(shape, '?')
    
    def format_player_letter(self, player):
        """Convertit un joueur en lettre pour l'historique"""
        player_mapping = {
            Player.PLAYER1: '1',    # Player
            Player.PLAYER2: '2'     # IA
        }
        return player_mapping.get(player, '?')
    
    def add_move_to_history(self, player, shape, row, col):
        """Ajoute un coup à l'historique"""
        player_letter = self.format_player_letter(player)
        shape_letter = self.format_shape_letter(shape)
        move_str = f"{player_letter}{shape_letter}({row},{col})"
        self.move_history.append(move_str)
        print(f"Coup ajouté à l'historique: {move_str}")
    
    def format_move_history(self):
        """Formate l'historique des coups pour la copie"""
        return str(self.move_history)
    
    def copy_move_history(self):
        """Copie l'historique des coups dans le presse-papier"""
        history_text = self.format_move_history()
        clipboard = QApplication.clipboard()
        clipboard.setText(history_text)
        
        # Afficher un message de confirmation
        QMessageBox.information(self, "Historique copié", 
                              f"L'historique des coups a été copié dans le presse-papier:\n\n{history_text}")
    
    def init_ui(self):
        """Initialise l'interface utilisateur"""
        self.setWindowTitle('🎯 QUANTIK vs IA - Jeu de Stratégie')
        self.setGeometry(100, 100, 1000, 700)
        self.setStyleSheet("background-color: #2c3e50;")
        
        # Widget central
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Layout principal
        main_layout = QHBoxLayout(central_widget)
        main_layout.setSpacing(30)
        main_layout.setContentsMargins(30, 30, 30, 30)
        
        # Panel gauche pour les contrôles
        left_panel = self.create_left_panel()
        main_layout.addWidget(left_panel)
        
        # Panel droit pour le plateau
        right_panel = self.create_board_panel()
        main_layout.addWidget(right_panel)
    
    def create_left_panel(self):
        """Crée le panel gauche avec les contrôles"""
        panel = QWidget()
        panel.setMaximumWidth(350)
        layout = QVBoxLayout(panel)
        
        # Titre
        title = QLabel("🎯 QUANTIK vs IA")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("""
            QLabel {
                font-size: 28px;
                font-weight: bold;
                color: #ecf0f1;
                background-color: #34495e;
                padding: 20px;
                border-radius: 10px;
                margin-bottom: 20px;
            }
        """)
        layout.addWidget(title)
        
        # Indicateur du joueur actuel
        self.current_player_widget = QWidget()
        player_layout = QVBoxLayout(self.current_player_widget)
        
        tour_label = QLabel("🎮 Tour de:")
        tour_label.setAlignment(Qt.AlignCenter)
        tour_label.setStyleSheet("color: #bdc3c7; font-size: 14px; font-weight: bold;")
        player_layout.addWidget(tour_label)
        
        self.player_label = QLabel(self.player_colors[Player.PLAYER1]['name'])
        self.player_label.setAlignment(Qt.AlignCenter)
        self.player_label.setStyleSheet(f"""
            QLabel {{
                font-size: 18px;
                font-weight: bold;
                color: white;
                background-color: {self.player_colors[Player.PLAYER1]['primary']};
                padding: 10px 20px;
                border-radius: 8px;
                margin: 5px 0px 15px 0px;
            }}
        """)
        player_layout.addWidget(self.player_label)
        
        # Indicateur de statut IA
        self.ai_status_label = QLabel("")
        self.ai_status_label.setAlignment(Qt.AlignCenter)
        self.ai_status_label.setStyleSheet("""
            QLabel {
                font-size: 14px;
                font-weight: bold;
                color: #f39c12;
                padding: 8px;
                border-radius: 6px;
                margin: 5px 0px;
            }
        """)
        player_layout.addWidget(self.ai_status_label)
        
        self.current_player_widget.setStyleSheet("""
            QWidget {
                background-color: #34495e;
                border-radius: 10px;
                padding: 10px;
                margin-bottom: 20px;
            }
        """)
        layout.addWidget(self.current_player_widget)
        
        # Section du joueur humain
        self.create_player_section(layout, Player.PLAYER1)
        
        # Section IA (affichage seulement)
        self.create_ai_section(layout, Player.PLAYER2)
        
        # Spacer pour pousser les boutons vers le bas
        layout.addStretch()
        
        # Boutons de contrôle
        new_game_btn = QPushButton("🔄 Nouvelle Partie")
        new_game_btn.clicked.connect(self.new_game)
        new_game_btn.setStyleSheet("""
            QPushButton {
                font-size: 14px;
                font-weight: bold;
                color: white;
                background-color: #27ae60;
                border: none;
                padding: 12px 20px;
                border-radius: 8px;
                margin-bottom: 10px;
            }
            QPushButton:hover {
                background-color: #2ecc71;
            }
            QPushButton:pressed {
                background-color: #239b56;
            }
        """)
        layout.addWidget(new_game_btn)
        
        quit_btn = QPushButton("❌ Quitter")
        quit_btn.clicked.connect(self.close)
        quit_btn.setStyleSheet("""
            QPushButton {
                font-size: 14px;
                font-weight: bold;
                color: white;
                background-color: #e74c3c;
                border: none;
                padding: 12px 20px;
                border-radius: 8px;
            }
            QPushButton:hover {
                background-color: #ec7063;
            }
            QPushButton:pressed {
                background-color: #cb4335;
            }
        """)
        layout.addWidget(quit_btn)
        
        return panel
    
    def create_player_section(self, layout, player):
        """Crée la section du joueur humain"""
        colors = self.player_colors[player]
        
        # Groupe principal
        group = QGroupBox(colors['name'])
        group.setStyleSheet(f"""
            QGroupBox {{
                font-size: 14px;
                font-weight: bold;
                color: {colors['primary']};
                background-color: #2c3e50;
                border: 2px solid {colors['primary']};
                border-radius: 10px;
                margin-top: 10px;
                margin-bottom: 10px;
                padding-top: 10px;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 10px 0 10px;
            }}
        """)
        
        group_layout = QVBoxLayout(group)
        
        # Label des formes disponibles
        shapes_label = QLabel("Formes disponibles:")
        shapes_label.setStyleSheet("color: #ecf0f1; font-size: 12px; font-weight: bold; margin-bottom: 8px;")
        group_layout.addWidget(shapes_label)
        
        # Grille des formes
        shapes_widget = QWidget()
        shapes_layout = QGridLayout(shapes_widget)
        shapes_layout.setSpacing(5)
        
        if not hasattr(self, 'shape_buttons'):
            self.shape_buttons = {}
        
        self.shape_buttons[player] = {}
        
        for i, shape in enumerate(Shape):
            row_pos = i // 2
            col_pos = i % 2
            
            # Container pour chaque forme
            shape_container = QWidget()
            container_layout = QHBoxLayout(shape_container)
            container_layout.setContentsMargins(5, 5, 5, 5)
            
            # Bouton de forme
            shape_btn = QPushButton(shape.value)
            shape_btn.setFixedSize(50, 40)
            shape_btn.clicked.connect(lambda checked, s=shape, p=player: self.select_shape(s, p))
            shape_btn.setStyleSheet(f"""
                QPushButton {{
                    font-size: 20px;
                    font-weight: bold;
                    color: {colors['secondary']};
                    background-color: {colors['light']};
                    border: 2px solid {colors['secondary']};
                    border-radius: 8px;
                }}
                QPushButton:hover {{
                    background-color: {colors['primary']};
                    color: white;
                }}
                QPushButton:pressed {{
                    background-color: {colors['secondary']};
                }}
            """)
            container_layout.addWidget(shape_btn)
            
            # Compteur de pièces
            count_label = QLabel("2")
            count_label.setAlignment(Qt.AlignCenter)
            count_label.setFixedSize(30, 30)
            count_label.setStyleSheet("""
                QLabel {
                    color: white;
                    background-color: #34495e;
                    border-radius: 15px;
                    font-size: 12px;
                    font-weight: bold;
                }
            """)
            container_layout.addWidget(count_label)
            
            shape_container.setStyleSheet("""
                QWidget {
                    background-color: #34495e;
                    border-radius: 8px;
                    margin: 2px;
                }
            """)
            
            shapes_layout.addWidget(shape_container, row_pos, col_pos)
            
            self.shape_buttons[player][shape] = {
                'button': shape_btn,
                'count_label': count_label,
                'container': shape_container
            }
        
        group_layout.addWidget(shapes_widget)
        layout.addWidget(group)
    
    def create_ai_section(self, layout, player):
        """Crée la section de l'IA (affichage seulement)"""
        colors = self.player_colors[player]
        
        # Groupe principal
        group = QGroupBox(colors['name'])
        group.setStyleSheet(f"""
            QGroupBox {{
                font-size: 14px;
                font-weight: bold;
                color: {colors['primary']};
                background-color: #2c3e50;
                border: 2px solid {colors['primary']};
                border-radius: 10px;
                margin-top: 10px;
                margin-bottom: 10px;
                padding-top: 10px;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 10px 0 10px;
            }}
        """)
        
        group_layout = QVBoxLayout(group)
        
        # Label des formes disponibles
        shapes_label = QLabel("Formes disponibles:")
        shapes_label.setStyleSheet("color: #ecf0f1; font-size: 12px; font-weight: bold; margin-bottom: 8px;")
        group_layout.addWidget(shapes_label)
        
        # Grille des formes (non cliquables)
        shapes_widget = QWidget()
        shapes_layout = QGridLayout(shapes_widget)
        shapes_layout.setSpacing(5)
        
        if player not in self.shape_buttons:
            self.shape_buttons[player] = {}
        
        for i, shape in enumerate(Shape):
            row_pos = i // 2
            col_pos = i % 2
            
            # Container pour chaque forme
            shape_container = QWidget()
            container_layout = QHBoxLayout(shape_container)
            container_layout.setContentsMargins(5, 5, 5, 5)
            
            # Bouton de forme (non cliquable pour l'IA)
            shape_btn = QPushButton(shape.value)
            shape_btn.setFixedSize(50, 40)
            shape_btn.setEnabled(False)  # Toujours désactivé pour l'IA
            shape_btn.setStyleSheet(f"""
                QPushButton {{
                    font-size: 20px;
                    font-weight: bold;
                    color: #ecf0f1;
                    background-color: #95a5a6;
                    border: 2px solid #7f8c8d;
                    border-radius: 8px;
                }}
            """)
            container_layout.addWidget(shape_btn)
            
            # Compteur de pièces
            count_label = QLabel("2")
            count_label.setAlignment(Qt.AlignCenter)
            count_label.setFixedSize(30, 30)
            count_label.setStyleSheet("""
                QLabel {
                    color: white;
                    background-color: #34495e;
                    border-radius: 15px;
                    font-size: 12px;
                    font-weight: bold;
                }
            """)
            container_layout.addWidget(count_label)
            
            shape_container.setStyleSheet("""
                QWidget {
                    background-color: #95a5a6;
                    border-radius: 8px;
                    margin: 2px;
                }
            """)
            
            shapes_layout.addWidget(shape_container, row_pos, col_pos)
            
            self.shape_buttons[player][shape] = {
                'button': shape_btn,
                'count_label': count_label,
                'container': shape_container
            }
        
        group_layout.addWidget(shapes_widget)
        layout.addWidget(group)
    
    def create_board_panel(self):
        """Crée le panel du plateau de jeu"""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setAlignment(Qt.AlignCenter)
        
        # Container du plateau avec ombre
        board_container = QWidget()
        board_container.setStyleSheet("""
            QWidget {
                background-color: #34495e;
                border-radius: 15px;
                padding: 15px;
            }
        """)
        
        container_layout = QVBoxLayout(board_container)
        
        # Grille du plateau
        board_widget = QWidget()
        self.board_layout = QGridLayout(board_widget)
        self.board_layout.setSpacing(8)
        
        # Création des boutons du plateau
        self.board_buttons = []
        for row in range(4):
            button_row = []
            for col in range(4):
                # Couleur de fond pour distinguer les zones
                if (row < 2 and col < 2) or (row >= 2 and col >= 2):
                    zone_color = '#ecf0f1'  # Zone claire
                else:
                    zone_color = '#d5dbdb'  # Zone plus foncée
                
                btn = QPushButton("")
                btn.setFixedSize(80, 80)
                btn.clicked.connect(lambda checked, r=row, c=col: self.place_piece(r, c))
                btn.setStyleSheet(f"""
                    QPushButton {{
                        font-size: 60px;
                        font-weight: bold;
                        background-color: {zone_color};
                        border: 2px solid #bdc3c7;
                        border-radius: 8px;
                    }}
                    QPushButton:hover {{
                        background-color: #bdc3c7;
                        border: 2px solid #85929e;
                    }}
                    QPushButton:pressed {{
                        background-color: #a6acaf;
                    }}
                """)
                
                # Espacement spécial pour séparer les zones
                margin_right = 15 if col == 1 else 0
                margin_bottom = 15 if row == 1 else 0
                
                self.board_layout.addWidget(btn, row, col)
                if margin_right > 0:
                    self.board_layout.setColumnMinimumWidth(col, 95)
                if margin_bottom > 0:
                    self.board_layout.setRowMinimumHeight(row, 95)
                
                button_row.append(btn)
            self.board_buttons.append(button_row)
        
        container_layout.addWidget(board_widget)
        layout.addWidget(board_container)
        
        return panel
    
    def select_shape(self, shape, player):
        """Sélectionne une forme pour le joueur humain"""
        if not self.game_enabled or player != self.current_player or self.current_player != Player.PLAYER1:
            return
            
        if self.pieces_count[self.current_player][shape] > 0:
            self.selected_shape = shape
            self.update_shape_buttons()
            print(f"Forme sélectionnée: {shape.value}")
        else:
            QMessageBox.warning(self, "Pièce épuisée", 
                              f"Vous n'avez plus de pièces {shape.value}")
    
    def place_piece(self, row, col):
        """Place une pièce sur le plateau (joueur humain)"""
        if not self.game_enabled or self.current_player != Player.PLAYER1:
            return
            
        print(f"DEBUG: place_piece appelé avec selected_shape = {self.selected_shape}")
        
        if self.selected_shape is None:
            QMessageBox.warning(self, "Aucune forme sélectionnée", 
                              "Veuillez d'abord sélectionner une forme")
            return
        
        piece = Piece(self.selected_shape, self.current_player)
        
        if self.board.place_piece(row, col, piece):
            # Ajouter le coup à l'historique
            self.add_move_to_history(self.current_player, self.selected_shape, row, col)
            
            # Décrémenter le compteur de pièces
            self.pieces_count[self.current_player][self.selected_shape] -= 1
            
            # Vérifier la victoire
            if self.board.check_victory():
                self.show_victory()
                return
            
            # Changer de joueur vers l'IA
            self.current_player = Player.PLAYER2
            self.selected_shape = None
            self.update_display()
            
            # Vérifier si l'IA peut jouer
            if not self.board.has_valid_moves(self.current_player):
                self.show_no_moves()
                return
            
            # Lancer l'IA
            self.start_ai_turn()
        else:
            QMessageBox.critical(self, "Coup invalide", 
                               "Cette pièce ne peut pas être placée ici.\n\n" +
                               "Rappel : Vous ne pouvez pas placer une forme\n" +
                               "dans une ligne, colonne ou zone où votre\n" +
                               "adversaire a déjà cette même forme.")
    
    def start_ai_turn(self):
        """Démarre le tour de l'IA"""
        self.game_enabled = False  # Désactiver l'interface
        self.ai_status_label.setText("🤖 IA réfléchit...")
        self.ai_status_label.setStyleSheet("""
            QLabel {
                font-size: 14px;
                font-weight: bold;
                color: #f39c12;
                background-color: rgba(243, 156, 18, 0.2);
                padding: 8px;
                border-radius: 6px;
                margin: 5px 0px;
            }
        """)
        
        # Lancer le calcul IA dans un thread séparé
        self.ai_worker = AIThinkingWorker(self.ai, self.board.board, self.pieces_count)
        self.ai_worker.move_calculated.connect(self.execute_ai_move)
        self.ai_worker.start()
    
    def execute_ai_move(self, move):
        """Exécute le coup calculé par l'IA"""
        if move is None or move == (-1, -1, None) or move[0] == -1:
            print("IA n'a pas trouvé de coup valide")
            self.show_no_moves()
            return
        
        row, col, shape = move
        piece = Piece(shape, Player.PLAYER2)
        
        print(f"IA joue: {shape.value} en ({row}, {col})")
        
        if self.board.place_piece(row, col, piece):
            # Ajouter le coup de l'IA à l'historique
            self.add_move_to_history(Player.PLAYER2, shape, row, col)
            
            # Décrémenter le compteur de pièces de l'IA
            self.pieces_count[Player.PLAYER2][shape] -= 1
            
            # Vérifier la victoire de l'IA
            if self.board.check_victory():
                self.ai_status_label.setText("🎯 IA a gagné!")
                self.ai_status_label.setStyleSheet("""
                    QLabel {
                        font-size: 14px;
                        font-weight: bold;
                        color: #e74c3c;
                        background-color: rgba(231, 76, 60, 0.3);
                        padding: 8px;
                        border-radius: 6px;
                        margin: 5px 0px;
                    }
                """)
                QTimer.singleShot(1000, self.show_victory)
                return
            
            # Changer de joueur vers l'humain
            self.current_player = Player.PLAYER1
            self.game_enabled = True
            self.ai_status_label.setText("")
            
            # Vérifier si l'humain peut jouer
            if not self.board.has_valid_moves(self.current_player):
                self.show_no_moves()
                return
            
            self.update_display()
        else:
            print("Erreur: Coup IA invalide!")
            self.game_enabled = True
            self.ai_status_label.setText("❌ Erreur IA")
    
    def update_display(self):
        """Met à jour l'affichage complet"""
        # Mettre à jour le plateau
        for row in range(4):
            for col in range(4):
                piece = self.board.board[row][col]
                btn = self.board_buttons[row][col]
                
                if piece is None:
                    # Case vide avec couleur de zone
                    if (row < 2 and col < 2) or (row >= 2 and col >= 2):
                        zone_color = '#ecf0f1'  # Zone claire
                    else:
                        zone_color = '#d5dbdb'  # Zone plus foncée
                    
                    btn.setText("")
                    btn.setStyleSheet(f"""
                        QPushButton {{
                            font-size: 60px;
                            font-weight: bold;
                            background-color: {zone_color};
                            border: 2px solid #bdc3c7;
                            border-radius: 8px;
                        }}
                        QPushButton:hover {{
                            background-color: #bdc3c7;
                            border: 2px solid #85929e;
                        }}
                        QPushButton:pressed {{
                            background-color: #a6acaf;
                        }}
                    """)
                else:
                    # Case occupée
                    colors = self.player_colors[piece.player]
                    btn.setText(piece.shape.value)
                    btn.setStyleSheet(f"""
                        QPushButton {{
                            font-size: 60px;
                            font-weight: bold;
                            color: {colors['primary']};
                            background-color: white;
                            border: 3px solid {colors['primary']};
                            border-radius: 8px;
                        }}
                    """)
        
        # Mettre à jour l'indicateur de joueur
        colors = self.player_colors[self.current_player]
        self.player_label.setText(colors['name'])
        self.player_label.setStyleSheet(f"""
            QLabel {{
                font-size: 18px;
                font-weight: bold;
                color: white;
                background-color: {colors['primary']};
                padding: 10px 20px;
                border-radius: 8px;
                margin: 5px 0px 15px 0px;
            }}
        """)
        
        # Mettre à jour les boutons de forme
        self.update_shape_buttons()
    
    def update_shape_buttons(self):
        """Met à jour l'apparence des boutons de forme"""
        for player in [Player.PLAYER1, Player.PLAYER2]:
            colors = self.player_colors[player]
            for shape, widgets in self.shape_buttons[player].items():
                btn = widgets['button']
                container = widgets['container']
                count = self.pieces_count[player][shape]
                
                # Mettre à jour le compteur
                widgets['count_label'].setText(str(count))
                
                if player == Player.PLAYER1:  # Joueur humain
                    if self.current_player == Player.PLAYER1 and self.game_enabled:
                        if shape == self.selected_shape:
                            # Forme sélectionnée
                            btn.setStyleSheet(f"""
                                QPushButton {{
                                    font-size: 20px;
                                    font-weight: bold;
                                    color: white;
                                    background-color: {colors['primary']};
                                    border: 3px solid {colors['secondary']};
                                    border-radius: 8px;
                                }}
                            """)
                            container.setStyleSheet(f"""
                                QWidget {{
                                    background-color: {colors['primary']};
                                    border-radius: 8px;
                                    margin: 2px;
                                }}
                            """)
                        elif count > 0:
                            # Forme disponible
                            btn.setStyleSheet(f"""
                                QPushButton {{
                                    font-size: 20px;
                                    font-weight: bold;
                                    color: {colors['secondary']};
                                    background-color: {colors['light']};
                                    border: 2px solid {colors['secondary']};
                                    border-radius: 8px;
                                }}
                                QPushButton:hover {{
                                    background-color: {colors['primary']};
                                    color: white;
                                }}
                                QPushButton:pressed {{
                                    background-color: {colors['secondary']};
                                }}
                            """)
                            btn.setEnabled(True)
                            container.setStyleSheet("""
                                QWidget {
                                    background-color: #34495e;
                                    border-radius: 8px;
                                    margin: 2px;
                                }
                            """)
                        else:
                            # Forme épuisée
                            btn.setStyleSheet("""
                                QPushButton {
                                    font-size: 20px;
                                    font-weight: bold;
                                    color: #bdc3c7;
                                    background-color: #7f8c8d;
                                    border: 2px solid #95a5a6;
                                    border-radius: 8px;
                                }
                            """)
                            btn.setEnabled(False)
                            container.setStyleSheet("""
                                QWidget {
                                    background-color: #7f8c8d;
                                    border-radius: 8px;
                                    margin: 2px;
                                }
                            """)
                    else:
                        # Pas le tour du joueur ou jeu désactivé
                        btn.setStyleSheet("""
                            QPushButton {
                                font-size: 20px;
                                font-weight: bold;
                                color: #ecf0f1;
                                background-color: #95a5a6;
                                border: 2px solid #7f8c8d;
                                border-radius: 8px;
                            }
                        """)
                        btn.setEnabled(False)
                        container.setStyleSheet("""
                            QWidget {
                                background-color: #95a5a6;
                                border-radius: 8px;
                                margin: 2px;
                            }
                        """)
                else:  # IA (Player.PLAYER2)
                    if self.current_player == Player.PLAYER2:
                        # Tour de l'IA - montrer l'activité
                        if count > 0:
                            btn.setStyleSheet(f"""
                                QPushButton {{
                                    font-size: 20px;
                                    font-weight: bold;
                                    color: {colors['secondary']};
                                    background-color: {colors['light']};
                                    border: 2px solid {colors['secondary']};
                                    border-radius: 8px;
                                }}
                            """)
                            container.setStyleSheet(f"""
                                QWidget {{
                                    background-color: {colors['primary']};
                                    border-radius: 8px;
                                    margin: 2px;
                                }}
                            """)
                        else:
                            # Forme épuisée IA
                            btn.setStyleSheet("""
                                QPushButton {
                                    font-size: 20px;
                                    font-weight: bold;
                                    color: #bdc3c7;
                                    background-color: #7f8c8d;
                                    border: 2px solid #95a5a6;
                                    border-radius: 8px;
                                }
                            """)
                            container.setStyleSheet("""
                                QWidget {
                                    background-color: #7f8c8d;
                                    border-radius: 8px;
                                    margin: 2px;
                                }
                            """)
                    else:
                        # Pas le tour de l'IA
                        btn.setStyleSheet("""
                            QPushButton {
                                font-size: 20px;
                                font-weight: bold;
                                color: #ecf0f1;
                                background-color: #95a5a6;
                                border: 2px solid #7f8c8d;
                                border-radius: 8px;
                            }
                        """)
                        container.setStyleSheet("""
                            QWidget {
                                background-color: #95a5a6;
                                border-radius: 8px;
                                margin: 2px;
                            }
                        """)
                    
                    # L'IA ne peut jamais être cliquée
                    btn.setEnabled(False)
    
    def show_victory(self):
        """Affiche le message de victoire avec option de copie d'historique"""
        if self.current_player == Player.PLAYER1:
            winner_text = "🎉 Félicitations ! Vous avez battu l'IA !"
        else:
            winner_text = "🤖 L'IA a gagné cette fois !\nReessayez pour votre revanche."
        
        # Créer une boîte de dialogue personnalisée
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("🏁 Partie terminée")
        msg_box.setText(winner_text)
        
        # Ajouter le bouton pour copier l'historique
        copy_history_btn = msg_box.addButton("📋 Copier historique", QMessageBox.ActionRole)
        new_game_btn = msg_box.addButton("🔄 Nouvelle partie", QMessageBox.AcceptRole)
        
        # Afficher la boîte de dialogue
        msg_box.exec_()
        
        # Vérifier quel bouton a été cliqué
        clicked_button = msg_box.clickedButton()
        if clicked_button == copy_history_btn:
            self.copy_move_history()
        
        # Démarrer une nouvelle partie dans tous les cas
        self.new_game()
    
    def show_no_moves(self):
        """Affiche le message quand un joueur ne peut plus jouer avec option de copie d'historique"""
        if self.current_player == Player.PLAYER1:
            msg_text = "🤖 Vous ne pouvez plus jouer.\nL'IA gagne par forfait !"
        else:
            msg_text = "🎉 L'IA ne peut plus jouer.\nVous gagnez par forfait !"
        
        # Créer une boîte de dialogue personnalisée
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("🏁 Partie terminée")
        msg_box.setText(msg_text)
        
        # Ajouter le bouton pour copier l'historique
        copy_history_btn = msg_box.addButton("📋 Copier historique", QMessageBox.ActionRole)
        new_game_btn = msg_box.addButton("🔄 Nouvelle partie", QMessageBox.AcceptRole)
        
        # Afficher la boîte de dialogue
        msg_box.exec_()
        
        # Vérifier quel bouton a été cliqué
        clicked_button = msg_box.clickedButton()
        if clicked_button == copy_history_btn:
            self.copy_move_history()
        
        # Démarrer une nouvelle partie dans tous les cas
        self.new_game()
    
    def new_game(self):
        """Commence une nouvelle partie"""
        # Arrêter le worker IA s'il est en cours
        if self.ai_worker and self.ai_worker.isRunning():
            self.ai_worker.terminate()
            self.ai_worker.wait()
        
        self.board = QuantikBoard()
        self.current_player = Player.PLAYER1
        self.selected_shape = None
        self.game_enabled = True
        
        # Réinitialiser les compteurs
        self.pieces_count = {
            Player.PLAYER1: {shape: 2 for shape in Shape},
            Player.PLAYER2: {shape: 2 for shape in Shape}
        }
        
        # Réinitialiser l'historique des coups
        self.move_history = []
        
        # Réinitialiser l'IA
        self.ai = QuantikAI(Player.PLAYER2)
        self.ai_status_label.setText("")
        
        self.update_display()
        print("🎯 Nouvelle partie contre l'IA démarrée")
    
    def closeEvent(self, event):
        """Gérer la fermeture de la fenêtre"""
        # Arrêter le worker IA s'il est en cours
        if self.ai_worker and self.ai_worker.isRunning():
            self.ai_worker.terminate()
            self.ai_worker.wait()
        event.accept()

def main():
    """Point d'entrée du programme"""
    app = QApplication(sys.argv)
    
    # Style global de l'application
    app.setStyleSheet("""
        QMainWindow {
            background-color: #2c3e50;
        }
    """)
    
    game = QuantikGame()
    game.show()
    
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()