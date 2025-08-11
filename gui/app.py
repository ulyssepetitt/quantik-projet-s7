# gui/app.py
# ---------------------------------------------------------------------
# Interface PyQt5 – visual du “vieil” app + configuration sur l’écran
# Découverte d’IA (ai_players/*/algorithme.py)
# Modes: Humain vs Humain, Humain vs IA, IA vs IA (sélection dans l’UI)
# Barre de défilement: panneau de gauche scrollable (vertical)
# ---------------------------------------------------------------------

import sys, time, importlib, pkgutil, pathlib
from typing import Optional
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *

from core.types import Shape, Player, Piece
from core.rules import QuantikBoard


# --- Découverte automatique des IA (plugins ai_players/*/algorithme.py) ---
def discover_ais():
    base_pkg = "ai_players"
    base_path = pathlib.Path(__file__).resolve().parents[1] / base_pkg
    ais = [{"name": "Humain", "module": None, "cls": None}]  # entrée Humain

    if not base_path.exists():
        return ais

    for pkg in pkgutil.iter_modules([str(base_path)]):
        if pkg.name == "template":
            continue  # on ignore le modèle
        mod_name = f"{base_pkg}.{pkg.name}.algorithme"
        try:
            mod = importlib.import_module(mod_name)
            ai_cls  = getattr(mod, "QuantikAI", None)
            ai_name = getattr(mod, "AI_NAME", pkg.name)
            if ai_cls:
                ais.append({"name": ai_name, "module": mod_name, "cls": ai_cls})
        except Exception as e:
            print(f"[AI DISCOVERY] Erreur pour {mod_name}: {e}")

    ais[1:] = sorted(ais[1:], key=lambda x: x["name"].lower())
    return ais


class AIThinkingWorker(QThread):
    """Thread pour calculer le coup IA sans bloquer l’UI."""
    move_calculated = pyqtSignal(tuple)  # (row, col, shape) ou (-1,-1,None)

    def __init__(self, ai, board, pieces_count):
        super().__init__()
        self.ai = ai
        self.board = board
        self.pieces_count = pieces_count

    def run(self):
        try:
            time.sleep(1.0)  # petit délai pour l’effet “réflexion”
            move = self.ai.get_move(self.board, self.pieces_count)
            if move:
                self.move_calculated.emit(move)
            else:
                self.move_calculated.emit((-1, -1, None))
        except Exception as e:
            print(f"Erreur IA: {e}")
            self.move_calculated.emit((-1, -1, None))


class QuantikGame(QMainWindow):
    """GUI Quantik – look & feel ancien + sélection de mode à l’écran."""

    def __init__(self):
        super().__init__()

        # IA disponibles
        self.available_ais = discover_ais()  # inclut "Humain" à l’index 0

        # Couleurs/étiquettes
        self.player_colors = {
            Player.PLAYER1: {
                'primary': '#3498db', 'secondary': '#2980b9', 'light': '#85c1e9',
                'name': 'Joueur 1 (Bleu)'
            },
            Player.PLAYER2: {
                'primary': '#e74c3c', 'secondary': '#c0392b', 'light': '#f1948a',
                'name': 'Joueur 2 (Rouge)'
            }
        }

        # État du jeu
        self.board = QuantikBoard()
        self.current_player = Player.PLAYER1
        self.selected_shape: Optional[Shape] = None
        self.game_enabled = True
        self.pieces_count = {
            Player.PLAYER1: {shape: 2 for shape in Shape},
            Player.PLAYER2: {shape: 2 for shape in Shape}
        }
        self.move_history = []

        # Instances d’IA (None = humain)
        self.ai_p1 = None
        self.ai_p2 = None
        self.ai_worker = None

        # UI
        self.init_ui()
        self.update_display()

        # Si on démarre avec une IA qui joue
        self._maybe_auto_play()

    # ====== Historique ======
    def format_shape_letter(self, shape):
        return {Shape.CIRCLE:'R', Shape.SQUARE:'C', Shape.TRIANGLE:'T', Shape.DIAMOND:'L'}.get(shape, '?')

    def format_player_letter(self, player):
        return {Player.PLAYER1:'1', Player.PLAYER2:'2'}.get(player, '?')

    def add_move_to_history(self, player, shape, row, col):
        move_str = f"{self.format_player_letter(player)}{self.format_shape_letter(shape)}({row},{col})"
        self.move_history.append(move_str)
        print(f"Coup ajouté à l'historique: {move_str}")

    def format_move_history(self):
        return str(self.move_history)

    def copy_move_history(self):
        QApplication.clipboard().setText(self.format_move_history())
        QMessageBox.information(self, "Historique copié",
                                f"L'historique des coups a été copié:\n\n{self.format_move_history()}")

    # ====== UI ======
    def init_ui(self):
        self.setWindowTitle('🎯 QUANTIK - Config à l’écran')
        self.setGeometry(100, 100, 1000, 700)
        self.setStyleSheet("background-color: #2c3e50;")

        # --- Le centralWidget sera une zone de défilement sur la colonne de gauche uniquement ---
        central = QWidget()
        self.setCentralWidget(central)

        main_layout = QHBoxLayout(central)
        main_layout.setSpacing(30)
        main_layout.setContentsMargins(30, 30, 30, 30)

        # Panneau gauche “réel”
        left_panel_widget = self.create_left_panel()

        # QScrollArea enveloppant le panneau gauche (scroll vertical)
        left_scroll = QScrollArea()
        left_scroll.setWidgetResizable(True)                 # le contenu s’adapte en largeur
        left_scroll.setFrameShape(QFrame.NoFrame)            # sans bordure
        left_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        left_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        left_scroll.setWidget(left_panel_widget)             # le widget réel du panneau

        # Panneau droit (plateau)
        right_panel = self.create_board_panel()

        # Ajout aux colonnes principales
        main_layout.addWidget(left_scroll, 0)   # colonne scrollable
        main_layout.addWidget(right_panel, 1)   # plateau

    def create_left_panel(self):
        """Construit le panneau gauche (retourné comme widget, scrollé par QScrollArea)."""
        panel = QWidget()
        panel.setMaximumWidth(350)
        layout = QVBoxLayout(panel)

        # Titre
        title = QLabel("🎯 QUANTIK")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("""
            QLabel {
                font-size: 28px; font-weight: bold; color: #ecf0f1;
                background-color: #34495e; padding: 20px; border-radius: 10px; margin-bottom: 20px;
            }
        """)
        layout.addWidget(title)

        # ===== Groupe de configuration (sur l’écran) =====
        cfg_group = QGroupBox("Configuration des joueurs")
        cfg_group.setStyleSheet("""
            QGroupBox {
                font-size: 14px; font-weight: bold; color: #ecf0f1;
                background-color: #2c3e50; border: 2px solid #7f8c8d;
                border-radius: 10px; margin-top: 10px; padding-top: 10px;
            }
            QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 10px; }
        """)
        cfg_layout = QVBoxLayout(cfg_group)

        self.cb_p1 = QComboBox()
        self.cb_p2 = QComboBox()
        for ai in self.available_ais:
            self.cb_p1.addItem(ai["name"])
            self.cb_p2.addItem(ai["name"])
        self.cb_p1.setCurrentIndex(0)
        self.cb_p2.setCurrentIndex(1 if len(self.available_ais) > 1 else 0)
        for cb in (self.cb_p1, self.cb_p2):
            cb.setStyleSheet("""
                QComboBox { background: #ecf0f1; border: 1px solid #7f8c8d; padding: 6px; border-radius: 6px; }
            """)

        cfg_layout.addWidget(QLabel("Joueur 1:"))
        cfg_layout.addWidget(self.cb_p1)
        cfg_layout.addWidget(QLabel("Joueur 2:"))
        cfg_layout.addWidget(self.cb_p2)

        btn_apply = QPushButton("Démarrer / Réinitialiser")
        btn_apply.clicked.connect(self.new_game)
        btn_apply.setStyleSheet("""
            QPushButton {
                font-size: 14px; font-weight: bold; color: white;
                background-color: #27ae60; border: none; padding: 10px 16px;
                border-radius: 8px; margin-top: 8px;
            }
            QPushButton:hover { background-color: #2ecc71; }
            QPushButton:pressed { background-color: #239b56; }
        """)
        cfg_layout.addWidget(btn_apply)
        layout.addWidget(cfg_group)

        # Indicateur de tour
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
                font-size: 18px; font-weight: bold; color: white;
                background-color: {self.player_colors[Player.PLAYER1]['primary']};
                padding: 10px 20px; border-radius: 8px; margin: 5px 0 15px 0;
            }}
        """)
        player_layout.addWidget(self.player_label)

        self.ai_status_label = QLabel("")
        self.ai_status_label.setAlignment(Qt.AlignCenter)
        self.ai_status_label.setStyleSheet("""
            QLabel {
                font-size: 14px; font-weight: bold; color: #f39c12;
                padding: 8px; border-radius: 6px; margin: 5px 0;
            }
        """)
        player_layout.addWidget(self.ai_status_label)

        self.current_player_widget.setStyleSheet("""
            QWidget { background-color: #34495e; border-radius: 10px; padding: 10px; margin-bottom: 20px; }
        """)
        layout.addWidget(self.current_player_widget)

        # Groupes de formes
        self.create_player_section(layout, Player.PLAYER1)
        self.create_ai_section(layout, Player.PLAYER2)

        layout.addStretch()

        quit_btn = QPushButton("❌ Quitter")
        quit_btn.clicked.connect(self.close)
        quit_btn.setStyleSheet("""
            QPushButton {
                font-size: 14px; font-weight: bold; color: white;
                background-color: #e74c3c; border: none; padding: 12px 20px; border-radius: 8px;
            }
            QPushButton:hover { background-color: #ec7063; }
            QPushButton:pressed { background-color: #cb4335; }
        """)
        layout.addWidget(quit_btn)

        return panel

    def create_player_section(self, layout, player):
        colors = self.player_colors[player]
        group = QGroupBox(colors['name'])
        group.setStyleSheet(f"""
            QGroupBox {{
                font-size: 14px; font-weight: bold; color: {colors['primary']};
                background-color: #2c3e50; border: 2px solid {colors['primary']};
                border-radius: 10px; margin-top: 10px; margin-bottom: 10px; padding-top: 10px;
            }}
            QGroupBox::title {{ subcontrol-origin: margin; left: 10px; padding: 0 10px; }}
        """)
        group_layout = QVBoxLayout(group)

        shapes_label = QLabel("Formes disponibles:")
        shapes_label.setStyleSheet("color: #ecf0f1; font-size: 12px; font-weight: bold; margin-bottom: 8px;")
        group_layout.addWidget(shapes_label)

        shapes_widget = QWidget()
        shapes_layout = QGridLayout(shapes_widget)
        shapes_layout.setSpacing(5)

        if not hasattr(self, 'shape_buttons'):
            self.shape_buttons = {}
        self.shape_buttons[player] = {}

        for i, shape in enumerate(Shape):
            row_pos = i // 2
            col_pos = i % 2

            shape_container = QWidget()
            container_layout = QHBoxLayout(shape_container)
            container_layout.setContentsMargins(5, 5, 5, 5)

            shape_btn = QPushButton(shape.value)
            shape_btn.setFixedSize(50, 40)
            shape_btn.clicked.connect(lambda checked, s=shape, p=player: self.select_shape(s, p))
            shape_btn.setStyleSheet(f"""
                QPushButton {{
                    font-size: 20px; font-weight: bold; color: {colors['secondary']};
                    background-color: {colors['light']}; border: 2px solid {colors['secondary']};
                    border-radius: 8px;
                }}
                QPushButton:hover {{ background-color: {colors['primary']}; color: white; }}
                QPushButton:pressed {{ background-color: {colors['secondary']}; }}
            """)
            container_layout.addWidget(shape_btn)

            count_label = QLabel("2")
            count_label.setAlignment(Qt.AlignCenter)
            count_label.setFixedSize(30, 30)
            count_label.setStyleSheet("""
                QLabel {
                    color: white; background-color: #34495e; border-radius: 15px;
                    font-size: 12px; font-weight: bold;
                }
            """)
            container_layout.addWidget(count_label)

            shape_container.setStyleSheet("""
                QWidget { background-color: #34495e; border-radius: 8px; margin: 2px; }
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
        """Même visuel; activable si Joueur 2 est humain (sinon, affichage)."""
        colors = self.player_colors[player]
        group = QGroupBox(colors['name'])
        group.setStyleSheet(f"""
            QGroupBox {{
                font-size: 14px; font-weight: bold; color: {colors['primary']};
                background-color: #2c3e50; border: 2px solid {colors['primary']};
                border-radius: 10px; margin-top: 10px; margin-bottom: 10px; padding-top: 10px;
            }}
            QGroupBox::title {{ subcontrol-origin: margin; left: 10px; padding: 0 10px; }}
        """)
        group_layout = QVBoxLayout(group)

        shapes_label = QLabel("Formes disponibles:")
        shapes_label.setStyleSheet("color: #ecf0f1; font-size: 12px; font-weight: bold; margin-bottom: 8px;")
        group_layout.addWidget(shapes_label)

        shapes_widget = QWidget()
        shapes_layout = QGridLayout(shapes_widget)
        shapes_layout.setSpacing(5)

        if player not in self.shape_buttons:
            self.shape_buttons[player] = {}

        for i, shape in enumerate(Shape):
            row_pos = i // 2
            col_pos = i % 2

            shape_container = QWidget()
            container_layout = QHBoxLayout(shape_container)
            container_layout.setContentsMargins(5, 5, 5, 5)

            shape_btn = QPushButton(shape.value)
            shape_btn.setFixedSize(50, 40)
            shape_btn.clicked.connect(lambda checked, s=shape, p=player: self.select_shape(s, p))
            container_layout.addWidget(shape_btn)

            count_label = QLabel("2")
            count_label.setAlignment(Qt.AlignCenter)
            count_label.setFixedSize(30, 30)
            count_label.setStyleSheet("""
                QLabel {
                    color: white; background-color: #34495e; border-radius: 15px;
                    font-size: 12px; font-weight: bold;
                }
            """)
            container_layout.addWidget(count_label)

            shape_container.setStyleSheet("""
                QWidget { background-color: #95a5a6; border-radius: 8px; margin: 2px; }
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
        """Panneau du plateau (grille 4x4) – côté droit, sans scroll."""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setAlignment(Qt.AlignCenter)

        board_container = QWidget()
        board_container.setStyleSheet("""
            QWidget { background-color: #34495e; border-radius: 15px; padding: 15px; }
        """)
        container_layout = QVBoxLayout(board_container)

        board_widget = QWidget()
        self.board_layout = QGridLayout(board_widget)
        self.board_layout.setSpacing(8)

        self.board_buttons = []
        for row in range(4):
            button_row = []
            for col in range(4):
                zone_color = '#ecf0f1' if ((row < 2 and col < 2) or (row >= 2 and col >= 2)) else '#d5dbdb'
                btn = QPushButton("")
                btn.setFixedSize(80, 80)
                btn.clicked.connect(lambda checked, r=row, c=col: self.place_piece(r, c))
                btn.setStyleSheet(f"""
                    QPushButton {{
                        font-size: 60px; font-weight: bold; background-color: {zone_color};
                        border: 2px solid #bdc3c7; border-radius: 8px;
                    }}
                    QPushButton:hover {{ background-color: #bdc3c7; border: 2px solid #85929e; }}
                    QPushButton:pressed {{ background-color: #a6acaf; }}
                """)
                if col == 1:
                    self.board_layout.setColumnMinimumWidth(col, 95)
                if row == 1:
                    self.board_layout.setRowMinimumHeight(row, 95)
                self.board_layout.addWidget(btn, row, col)
                button_row.append(btn)
            self.board_buttons.append(button_row)

        container_layout.addWidget(board_widget)
        layout.addWidget(board_container)
        return panel

    # ====== Interactions ======
    def _current_ai(self):
        return self.ai_p1 if self.current_player == Player.PLAYER1 else self.ai_p2

    def select_shape(self, shape, player):
        if not self.game_enabled:
            return
        if player != self.current_player:
            return
        if self._current_ai() is not None:
            return  # côté IA, pas de sélection manuelle
        if self.pieces_count[self.current_player][shape] <= 0:
            QMessageBox.warning(self, "Pièce épuisée", f"Vous n'avez plus de pièces {shape.value}")
            return
        self.selected_shape = shape
        self.update_shape_buttons()
        print(f"Forme sélectionnée: {shape.value} par {self.current_player}")

    def place_piece(self, row, col):
        if not self.game_enabled:
            return
        if self._current_ai() is not None:
            return  # IA côté courant : clic désactivé
        if self.selected_shape is None:
            QMessageBox.warning(self, "Aucune forme sélectionnée", "Veuillez d'abord sélectionner une forme")
            return

        piece = Piece(self.selected_shape, self.current_player)
        if self.board.place_piece(row, col, piece):
            self.add_move_to_history(self.current_player, self.selected_shape, row, col)
            self.pieces_count[self.current_player][self.selected_shape] -= 1

            if self.board.check_victory():
                self.show_victory(self.current_player)
                return

            # Changement de joueur
            self.current_player = Player.PLAYER2 if self.current_player == Player.PLAYER1 else Player.PLAYER1
            self.selected_shape = None
            self.update_display()

            if not self.board.has_valid_moves(self.current_player):
                self.show_no_moves()
                return

            self._maybe_auto_play()
        else:
            QMessageBox.critical(
                self, "Coup invalide",
                "Cette pièce ne peut pas être placée ici.\n\n"
                "Rappel : Vous ne pouvez pas placer une forme\n"
                "dans une ligne, colonne ou zone où votre\n"
                "adversaire a déjà cette même forme."
            )

    def _maybe_auto_play(self):
        ai_curr = self._current_ai()
        if ai_curr is None or not self.game_enabled:
            return
        self.game_enabled = False
        self.ai_status_label.setText("🤖 IA réfléchit...")
        self.ai_status_label.setStyleSheet("""
            QLabel {
                font-size: 14px; font-weight: bold; color: #f39c12;
                background-color: rgba(243, 156, 18, 0.2);
                padding: 8px; border-radius: 6px; margin: 5px 0;
            }
        """)
        self.ai_worker = AIThinkingWorker(ai_curr, self.board.board, self.pieces_count)
        self.ai_worker.move_calculated.connect(self._execute_ai_move)
        self.ai_worker.start()

    def _execute_ai_move(self, move):
        if move is None or move == (-1, -1, None) or move[0] == -1:
            print("IA n'a pas trouvé de coup valide")
            self.show_no_moves()
            return

        row, col, shape = move
        piece = Piece(shape, self.current_player)
        print(f"IA joue: {shape.value} en ({row}, {col})")

        if self.board.place_piece(row, col, piece):
            self.add_move_to_history(self.current_player, shape, row, col)
            self.pieces_count[self.current_player][shape] -= 1

            if self.board.check_victory():
                self.ai_status_label.setText("🎯 Victoire !")
                self.ai_status_label.setStyleSheet("""
                    QLabel {
                        font-size: 14px; font-weight: bold; color: #e74c3c;
                        background-color: rgba(231, 76, 60, 0.3);
                        padding: 8px; border-radius: 6px; margin: 5px 0;
                    }
                """)
                QTimer.singleShot(200, lambda: self.show_victory(self.current_player))
                return

            self.current_player = Player.PLAYER2 if self.current_player == Player.PLAYER1 else Player.PLAYER1
            self.game_enabled = True
            self.ai_status_label.setText("")

            if not self.board.has_valid_moves(self.current_player):
                self.show_no_moves()
                return

            self.update_display()
            self._maybe_auto_play()  # IA vs IA: enchaîne
        else:
            print("Erreur: Coup IA invalide!")
            self.game_enabled = True
            self.ai_status_label.setText("❌ Erreur IA")

    def update_display(self):
        # Plateau
        for row in range(4):
            for col in range(4):
                piece = self.board.board[row][col]
                btn = self.board_buttons[row][col]

                if piece is None:
                    zone_color = '#ecf0f1' if ((row < 2 and col < 2) or (row >= 2 and col >= 2)) else '#d5dbdb'
                    btn.setText("")
                    btn.setStyleSheet(f"""
                        QPushButton {{
                            font-size: 60px; font-weight: bold; background-color: {zone_color};
                            border: 2px solid #bdc3c7; border-radius: 8px;
                        }}
                        QPushButton:hover {{ background-color: #bdc3c7; border: 2px solid #85929e; }}
                        QPushButton:pressed {{ background-color: #a6acaf; }}
                    """)
                    btn.setEnabled(self.game_enabled and self._current_ai() is None)
                else:
                    colors = self.player_colors[piece.player]
                    btn.setText(piece.shape.value)
                    btn.setStyleSheet(f"""
                        QPushButton {{
                            font-size: 60px; font-weight: bold; color: {colors['primary']};
                            background-color: white; border: 3px solid {colors['primary']};
                            border-radius: 8px;
                        }}
                    """)
                    btn.setEnabled(False)

        # Étiquette “tour de”
        colors = self.player_colors[self.current_player]
        self.player_label.setText(colors['name'])
        self.player_label.setStyleSheet(f"""
            QLabel {{
                font-size: 18px; font-weight: bold; color: white;
                background-color: {colors['primary']};
                padding: 10px 20px; border-radius: 8px; margin: 5px 0 15px 0;
            }}
        """)

        self.update_shape_buttons()

    def update_shape_buttons(self):
        # “Humain” si l’IA de l’index est None
        p1_is_human = (self.available_ais[self.cb_p1.currentIndex()]["cls"] is None)
        p2_is_human = (self.available_ais[self.cb_p2.currentIndex()]["cls"] is None)

        for player in [Player.PLAYER1, Player.PLAYER2]:
            colors = self.player_colors[player]
            is_human = p1_is_human if player == Player.PLAYER1 else p2_is_human
            for shape, widgets in self.shape_buttons[player].items():
                btn = widgets['button']
                container = widgets['container']
                count = self.pieces_count[player][shape]
                widgets['count_label'].setText(str(count))

                if is_human:
                    if self.current_player == player and self.game_enabled:
                        if shape == self.selected_shape:
                            btn.setStyleSheet(f"""
                                QPushButton {{
                                    font-size: 20px; font-weight: bold; color: white;
                                    background-color: {colors['primary']};
                                    border: 3px solid {colors['secondary']}; border-radius: 8px;
                                }}
                            """)
                            container.setStyleSheet(f"""
                                QWidget {{ background-color: {colors['primary']}; border-radius: 8px; margin: 2px; }}
                            """)
                        elif count > 0:
                            btn.setStyleSheet(f"""
                                QPushButton {{
                                    font-size: 20px; font-weight: bold; color: {colors['secondary']};
                                    background-color: {colors['light']};
                                    border: 2px solid {colors['secondary']}; border-radius: 8px;
                                }}
                                QPushButton:hover {{ background-color: {colors['primary']}; color: white; }}
                                QPushButton:pressed {{ background-color: {colors['secondary']}; }}
                            """)
                            btn.setEnabled(True)
                            container.setStyleSheet("""
                                QWidget { background-color: #34495e; border-radius: 8px; margin: 2px; }
                            """)
                        else:
                            btn.setStyleSheet("""
                                QPushButton {
                                    font-size: 20px; font-weight: bold; color: #bdc3c7;
                                    background-color: #7f8c8d; border: 2px solid #95a5a6; border-radius: 8px;
                                }
                            """)
                            btn.setEnabled(False)
                            container.setStyleSheet("""
                                QWidget { background-color: #7f8c8d; border-radius: 8px; margin: 2px; }
                            """)
                    else:
                        btn.setStyleSheet("""
                            QPushButton {
                                font-size: 20px; font-weight: bold; color: #ecf0f1;
                                background-color: #95a5a6; border: 2px solid #7f8c8d; border-radius: 8px;
                            }
                        """)
                        btn.setEnabled(False)
                        container.setStyleSheet("""
                            QWidget { background-color: #95a5a6; border-radius: 8px; margin: 2px; }
                        """)
                else:
                    # IA – affichage uniquement
                    if self.current_player == player:
                        if count > 0:
                            btn.setStyleSheet(f"""
                                QPushButton {{
                                    font-size: 20px; font-weight: bold; color: {colors['secondary']};
                                    background-color: {colors['light']};
                                    border: 2px solid {colors['secondary']}; border-radius: 8px;
                                }}
                            """)
                            container.setStyleSheet(f"""
                                QWidget {{ background-color: {colors['primary']}; border-radius: 8px; margin: 2px; }}
                            """)
                        else:
                            btn.setStyleSheet("""
                                QPushButton {
                                    font-size: 20px; font-weight: bold; color: #bdc3c7;
                                    background-color: #7f8c8d; border: 2px solid #95a5a6; border-radius: 8px;
                                }
                            """)
                            container.setStyleSheet("""
                                QWidget { background-color: #7f8c8d; border-radius: 8px; margin: 2px; }
                            """)
                    else:
                        btn.setStyleSheet("""
                            QPushButton {
                                font-size: 20px; font-weight: bold; color: #ecf0f1;
                                background-color: #95a5a6; border: 2px solid #7f8c8d; border-radius: 8px;
                            }
                        """)
                        container.setStyleSheet("""
                            QWidget { background-color: #95a5a6; border-radius: 8px; margin: 2px; }
                        """)
                    btn.setEnabled(False)

    # ====== Popups ======
    def show_victory(self, winner: Player):
        winner_text = "🎉 Joueur 1 a gagné !" if winner == Player.PLAYER1 else "🎉 Joueur 2 a gagné !"
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("🏁 Partie terminée")
        msg_box.setText(winner_text)
        copy_history_btn = msg_box.addButton("📋 Copier historique", QMessageBox.ActionRole)
        msg_box.addButton("🔄 Nouvelle partie", QMessageBox.AcceptRole)
        msg_box.exec_()
        if msg_box.clickedButton() == copy_history_btn:
            self.copy_move_history()
        self.new_game()

    def show_no_moves(self):
        winner = Player.PLAYER2 if self.current_player == Player.PLAYER1 else Player.PLAYER1
        winner_text = "🎉 Joueur 1 gagne (adversaire bloqué) !" if winner == Player.PLAYER1 \
                      else "🎉 Joueur 2 gagne (adversaire bloqué) !"
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("🏁 Partie terminée")
        msg_box.setText(winner_text)
        copy_history_btn = msg_box.addButton("📋 Copier historique", QMessageBox.ActionRole)
        msg_box.addButton("🔄 Nouvelle partie", QMessageBox.AcceptRole)
        msg_box.exec_()
        if msg_box.clickedButton() == copy_history_btn:
            self.copy_move_history()
        self.new_game()

    # ====== Nouvelle partie / Reset ======
    def new_game(self):
        if self.ai_worker and self.ai_worker.isRunning():
            self.ai_worker.terminate()
            self.ai_worker.wait()

        self.board = QuantikBoard()
        self.current_player = Player.PLAYER1
        self.selected_shape = None
        self.game_enabled = True
        self.pieces_count = {
            Player.PLAYER1: {shape: 2 for shape in Shape},
            Player.PLAYER2: {shape: 2 for shape in Shape}
        }
        self.move_history = []
        self.ai_status_label.setText("")

        sel1 = self.available_ais[self.cb_p1.currentIndex()]
        sel2 = self.available_ais[self.cb_p2.currentIndex()]
        self.ai_p1 = sel1["cls"](Player.PLAYER1) if sel1["cls"] else None
        self.ai_p2 = sel2["cls"](Player.PLAYER2) if sel2["cls"] else None

        self.update_display()
        print("🎯 Nouvelle partie démarrée - P1:", sel1["name"], "| P2:", sel2["name"])
        self._maybe_auto_play()

    def closeEvent(self, event):
        if self.ai_worker and self.ai_worker.isRunning():
            self.ai_worker.terminate()
            self.ai_worker.wait()
        event.accept()


# ===================== Lancement =====================
def main():
    app = QApplication(sys.argv)
    app.setStyleSheet("QMainWindow { background-color: #2c3e50; }")
    game = QuantikGame()
    game.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
