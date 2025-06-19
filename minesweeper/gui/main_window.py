import json
from PyQt6 import QtWidgets, QtGui, QtCore
from game.minesweeper_game import MinesweeperGame
from gui.board_widget import MinesweeperWidget
from gui.counter_widget import CounterWidget
from gui.face_button import FaceButton
from gui.border_widget import BorderWidget
from gui.custom_game_dialog import CustomGameDialog

DIFFICULTIES = {
    "Beginner": (9, 9, 10),
    "Intermediate": (16, 16, 40),
    "Expert": (16, 30, 99)
}

class MainWindow(QtWidgets.QMainWindow):
    scaleChanged = QtCore.pyqtSignal(float)  # Signal to notify all widgets about scale updates

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Minesweeper")
        self.game = None
        self.board_widget = None
        self.timer = QtCore.QTimer(self)
        self.timer.timeout.connect(self.update_timer)
        self.elapsed_time = 0
        self.zoom_level = 100
        self.selected_difficulty = "Beginner" # Initialize
        self.create_menu()
        self.set_difficulty(*DIFFICULTIES["Beginner"])  # Initial game

        # Connect the scaleChanged signal to all border widgets
        self.scaleChanged.connect(self.update_all_borders)

        # Lock Size
        self.setFixedSize(self.size()) # Lock to initial size.

    def create_menu(self):
        """Creates the menu bar."""
        menubar = self.menuBar()

        # Game Menu
        game_menu = menubar.addMenu("&Game")
        new_game_action = QtGui.QAction("&New Game", self)
        new_game_action.setShortcut(QtGui.QKeySequence(QtCore.Qt.Key.Key_F2))
        new_game_action.triggered.connect(self.new_game)
        game_menu.addAction(new_game_action)
        game_menu.addSeparator()

        self.difficulty_actions = {}
        for label, (rows, cols, mines) in DIFFICULTIES.items():
            action = QtGui.QAction(f"&{label}", self, checkable=True)
            action.triggered.connect(lambda checked, r=rows, c=cols, m=mines: self.set_difficulty(r, c, m))
            self.difficulty_actions[label] = action
            game_menu.addAction(action)
        custom_action = QtGui.QAction("C&ustom...", self, checkable=True)
        custom_action.triggered.connect(self.show_custom_dialog)
        self.difficulty_actions["Custom"] = custom_action

        game_menu.addAction(custom_action)
        game_menu.addSeparator()

        exit_action = QtGui.QAction("E&xit", self)
        exit_action.triggered.connect(self.close)
        game_menu.addAction(exit_action)

       # Display Menu
        # display_menu = menubar.addMenu("&Display")
        # self.zoom_actions = {}
        # for zoom in [100, 150, 200]:
        #     zoom_action = QtGui.QAction(f"{zoom}%", self, checkable=True)
        #     zoom_action.triggered.connect(lambda checked, z=zoom: self.set_zoom(z))
        #     self.zoom_actions[zoom] = zoom_action
        #     display_menu.addAction(zoom_action)
        # self.zoom_actions[100].setChecked(True)  # Default zoom

        # Import/Export Menus
        import_menu = menubar.addMenu("&Import")
        export_menu = menubar.addMenu("&Export")
        import_action = QtGui.QAction("&Import", self)
        import_action.triggered.connect(self.import_game)
        import_menu.addAction(import_action)

        export_action = QtGui.QAction("&Export", self)
        export_action.triggered.connect(self.export_game)
        export_menu.addAction(export_action)

        # Help Menu
        help_menu = menubar.addMenu("&Help")
        about_action = QtGui.QAction("&About", self)
        about_action.triggered.connect(self.about)
        help_menu.addAction(about_action)

    def create_widgets(self):
        """Creates the main widgets and layout."""
        scale_factor = self.zoom_level / 100
        cell_size = int(16 * scale_factor)
        cell_size_double = int(cell_size * 2)

        central_widget = QtWidgets.QWidget()
        main_layout = QtWidgets.QVBoxLayout(central_widget)
        main_layout.setSpacing(0)  # Remove extra spacing
        main_layout.setContentsMargins(0, 0, 0, 0)

        # Top Panel (Counters and Face)
        top_panel_layout = QtWidgets.QHBoxLayout()
        top_panel_layout.setSpacing(0)

        self.mines_counter = CounterWidget(scale_factor, self.game.mines)
        self.timer_counter = CounterWidget(scale_factor)
        self.face_button = FaceButton(self)

        mines_counter_border = BorderWidget(6 * cell_size + cell_size_double, cell_size * 3, "counter", scale_factor)
        timer_counter_border = BorderWidget(6 * cell_size + cell_size_double, cell_size * 3, "counter", scale_factor)

        mines_counter_layout = QtWidgets.QHBoxLayout(mines_counter_border)
        mines_counter_layout.addWidget(self.mines_counter)
        mines_counter_layout.setContentsMargins(0, 0, 0, 0)

        timer_counter_layout = QtWidgets.QHBoxLayout(timer_counter_border)
        timer_counter_layout.addWidget(self.timer_counter)
        timer_counter_layout.setContentsMargins(0, 0, 0, 0)

        top_panel_layout.addWidget(mines_counter_border)
        top_panel_layout.addStretch(1)
        top_panel_layout.addWidget(self.face_button)
        top_panel_layout.addStretch(1)
        top_panel_layout.addWidget(timer_counter_border)

        # Wrap top panel with border
        self.top_panel_border = BorderWidget(int((self.game.cols * cell_size_double) + cell_size_double), cell_size_double * 3, "top", scale_factor)  # Adjust
        top_panel_border_layout = QtWidgets.QVBoxLayout(self.top_panel_border)
        top_panel_border_layout.addLayout(top_panel_layout)
        top_panel_border_layout.setContentsMargins(0,0,0,0)

        main_layout.addWidget(self.top_panel_border)

        # Game Board (with border)
        board_border = BorderWidget(int((self.game.cols * cell_size_double) + cell_size_double), int(self.game.rows * cell_size_double), "bottom", scale_factor)
        board_layout = QtWidgets.QVBoxLayout(board_border)
        board_layout.addWidget(self.board_widget)
        board_layout.setContentsMargins(cell_size, 0, cell_size, cell_size)
        main_layout.addWidget(board_border)

        self.setCentralWidget(central_widget)
        # Initial sizing (after widgets are created)
        self.resize_geometry()

    def resize_geometry(self):
        """Recalculates and resizes the window based on current content."""
        scale_factor = self.zoom_level / 100
        cell_size = int(16 * scale_factor)
        cell_size_double = int(cell_size * 2)

        self.mines_counter.set_cell_size(scale_factor)
        self.timer_counter.set_cell_size(scale_factor)
        self.board_widget.set_cell_size(cell_size_double)
            
        # Use the widget's current fixed size
        board_width = self.board_widget.width()
        board_height = self.board_widget.height()

        top_panel_height = self.top_panel_border.height() # Fixed height
        total_width = board_width + cell_size_double
        total_height = board_height + top_panel_height + (cell_size * 3)

        self.board_widget.setFixedSize(board_width, board_height)
        self.setFixedSize(total_width, total_height)

    def new_game(self):
        """Starts a new game."""
        self.timer.stop()
        self.elapsed_time = 0
        self.timer_counter.set_value(0)
        self.face_button.set_state('smile') # Reset face

        difficulty_settings = DIFFICULTIES.get(self.selected_difficulty, None)
        if difficulty_settings:
             rows, cols, mines = difficulty_settings
        else:  # Fallback to current game settings if not found
             rows, cols, mines = self.game.rows, self.game.cols, self.game.mines

        self.set_difficulty(rows, cols, mines)
        self.timer.start(1000)

    def update_all_borders(self, scale_factor):
        """This function is called when the zoom level changes."""
        cell_size = int(16 * scale_factor)

        for widget in self.findChildren(BorderWidget):
            widget.update_scale(scale_factor)
            #widget.setContentsMargins(cell_size, 0, cell_size, cell_size)

    def set_difficulty(self, rows, cols, mines):
        """Sets the game difficulty."""
        cell_size = int(32 * (self.zoom_level / 100))

        # Uncheck all difficulty actions, then check the correct one.
        for action in self.difficulty_actions.values():
            action.setChecked(False)

        for label, action in self.difficulty_actions.items():
            if (rows, cols, mines) == DIFFICULTIES.get(label, None):
                action.setChecked(True)
                self.selected_difficulty = label
                break
        else:  # If no standard difficulty matches, it's custom
            self.difficulty_actions["Custom"].setChecked(True)
            self.selected_difficulty = "Custom"

        self.game = MinesweeperGame(rows, cols, mines, self)
        self.game.reset_board()

        if self.board_widget:
            self.board_widget.game = self.game  # Update game
            self.board_widget.set_cell_size(cell_size)
            self.board_widget.update()
        else:
            self.board_widget = MinesweeperWidget(self.game, cell_size, self)  # Pass MainWindow

        self.create_widgets() # Recreate to apply changes
        self.update_mines_display()
        self.reset_timer()
        self.setFixedSize(self.minimumSize())  # Lock size after creation (key change)

    def show_custom_dialog(self):
        """Shows the custom field dialog."""
        dialog = CustomGameDialog(self)
        if dialog.exec():
            height, width, mines = dialog.getValues()
            self.set_difficulty(height, width, mines)

    def set_zoom(self, zoom_level):
        """Sets the zoom level."""
        for action in self.zoom_actions.values():
            action.setChecked(False)
        self.zoom_actions[zoom_level].setChecked(True)
        self.zoom_level = zoom_level
        scale_factor = zoom_level / 100

        # Scale Minesweeper board
        if self.board_widget:
            new_cell_size = int(32 * scale_factor)
            self.board_widget.set_cell_size(new_cell_size)

        # Scale Face Button
        new_face_size = int(50 * scale_factor)
        self.face_button.setFixedSize(new_face_size, new_face_size)

        # Scale Counters
        new_counter_width = int(3 * 26 * scale_factor)
        new_counter_height = int(50 * scale_factor)
        self.mines_counter.setFixedSize(new_counter_width, new_counter_height)
        self.timer_counter.setFixedSize(new_counter_width, new_counter_height)

        # Scale borders (example, you might need to adjust)
        new_border_width = int(self.board_widget.width() + 32 * scale_factor)
         # Adjust height as needed
        new_border_height = int(96 * scale_factor)
        self.top_panel_border.setFixedSize(new_border_width, new_border_height)

        self.resize_geometry()
        self.setFixedSize(self.minimumSize())  # Lock size after zoom (key change)
        # Emit signal to update all widgets
        print(scale_factor)
        self.scaleChanged.emit(scale_factor)

    def start_timer(self):
        """Starts the game timer."""
        if not self.timer.isActive():
            self.elapsed_time = 0
            self.timer_counter.set_value(0)
            self.timer.start(1000)

    def update_timer(self):
        """Updates the timer display."""
        if not self.game.game_over and self.game.game_started:
            self.elapsed_time += 1
            self.timer_counter.set_value(self.elapsed_time)

    def reset_timer(self):
        """Resets the timer."""
        self.timer.stop()
        self.elapsed_time = 0
        self.timer_counter.set_value(0)
        if self.game.game_started: # Restart timer only if game started
          self.timer.start(1000)

    def update_mines_display(self):
        """Updates the mines counter display."""
        self.mines_counter.set_value(self.game.mines_left)

    def game_over_callback(self):
        """Handles the game over event."""
        self.timer.stop()
        self.face_button.set_state('lose')

    def win_game_callback(self):
        """Handles the win game event."""
        self.timer.stop()
        self.face_button.set_state('win')

    def left_mouse_press_callback(self):
        """Handles left mouse press events (for the face button)."""
        if not self.game.game_over:
            self.face_button.set_state('click')

    def left_mouse_release_callback(self):
        """Handles left mouse release events (for the face button)."""
        if not self.game.game_over:
            self.face_button.set_state('smile')
    def export_game(self):
        """Exports the current game state to a JSON file."""
        def encode_cell(cell):
            if cell["mine"]: return "M"
            if cell["revealed"]: return "R"
            if cell["flagged"]: return "F"
            if cell["neighbor"] > 0: return f"N{cell['neighbor']}"
            return "E"  # Empty

        compressed_board = [[encode_cell(cell) for cell in row] for row in self.game.board]

        game_state = {
            "rows": self.game.rows,
            "cols": self.game.cols,
            "mines": self.game.mines,
            "board": compressed_board,
            "game_over": self.game.game_over,
            "game_started": self.game.game_started,
            "mines_left": self.game.mines_left,
            "elapsed_time": self.elapsed_time,
            "selected_difficulty": self.selected_difficulty,
            "zoom_level": self.zoom_level
        }

        filename, _ = QtWidgets.QFileDialog.getSaveFileName(self, "Save Game", "", "JSON Files (*.json)")
        if filename:
            with open(filename, "w") as f:
                json.dump(game_state, f)
            QtWidgets.QMessageBox.information(self, "Export Successful", "Game saved successfully.")

    def import_game(self):
        """Imports a game state from a JSON file."""
        filename, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Load Game", "", "JSON Files (*.json)")
        if filename:
            with open(filename, "r") as f:
                game_state = json.load(f)

            def decode_cell(symbol):
                if symbol == "M":
                    return {"mine": True, "revealed": False, "flagged": False, "neighbor": 0}
                if symbol == "R":
                    return {"mine": False, "revealed": True, "flagged": False, "neighbor": 0}
                if symbol == "F":
                    return {"mine": False, "revealed": False, "flagged": True, "neighbor": 0}
                if symbol.startswith("N"):
                    return {"mine": False, "revealed": False, "flagged": False, "neighbor": int(symbol[1:])}
                return {"mine": False, "revealed": False, "flagged": False, "neighbor": 0}
            self.game = MinesweeperGame(game_state["rows"], game_state["cols"], game_state["mines"])
            self.game.board = [[decode_cell(cell) for cell in row] for row in game_state["board"]]
            self.game.calculate_neighbors()  # Recalculate
            self.game.game_over = game_state["game_over"]
            self.game.game_started = game_state.get("game_started", False)  # Default
            self.game.mines_left = game_state.get("mines_left", self.game.mines)
            self.elapsed_time = game_state.get("elapsed_time", 0)  # Default

            difficulty = game_state.get("selected_difficulty", "Custom")
            self.selected_difficulty = difficulty
            for action in self.difficulty_actions.values():
                 action.setChecked(False)
            if difficulty in self.difficulty_actions:
                self.difficulty_actions[difficulty].setChecked(True)

            zoom_level = game_state.get("zoom_level", 100)
            self.set_zoom(zoom_level)
            self.board_widget.game = self.game
            self.create_widgets()
            self.update_mines_display()  # update mine counter
            self.timer_counter.set_value(self.elapsed_time)  # set correct time

            if self.game.game_started:
                self.timer.start(1000)  # start timer if already stated

            QtWidgets.QMessageBox.information(self, "Import Successful", "Game loaded successfully.")

    def about(self):
        """Displays the about dialog."""
        QtWidgets.QMessageBox.about(self, "About Minesweeper",
                                    "Minesweeper Game built with PyQt6\nInspired by the classic Minesweeper.")