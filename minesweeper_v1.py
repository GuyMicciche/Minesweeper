import json
import os
import sys
import random
from PyQt6 import QtWidgets, QtGui, QtCore, QtSvg

# --------------------------------------------------
# Game logic class
# --------------------------------------------------
class MinesweeperGame:
    def __init__(self, rows, cols, mines):
        self.rows = rows
        self.cols = cols
        self.mines = mines
        self.board = [
            [  # Each cell is a dictionary with its state.
                {'mine': False, 'revealed': False, 'flagged': False, 'neighbor': 0}
                for _ in range(cols)
            ]
            for _ in range(rows)
        ]
        self.game_over = False
        self.initialize_board()

    def initialize_board(self):
        # Randomly choose mine positions
        positions = [(r, c) for r in range(self.rows) for c in range(self.cols)]
        mine_positions = random.sample(positions, self.mines)
        for r, c in mine_positions:
            self.board[r][c]['mine'] = True
        self.calculate_neighbors()

    def calculate_neighbors(self):
        for r in range(self.rows):
            for c in range(self.cols):
                if self.board[r][c]['mine']:
                    continue
                count = 0
                for dr in (-1, 0, 1):
                    for dc in (-1, 0, 1):
                        nr, nc = r + dr, c + dc
                        if 0 <= nr < self.rows and 0 <= nc < self.cols:
                            if self.board[nr][nc]['mine']:
                                count += 1
                self.board[r][c]['neighbor'] = count

    def reveal_cell(self, row, col):
        if self.game_over:
            return

        cell = self.board[row][col]
        if cell['revealed'] or cell['flagged']:
            return

        cell['revealed'] = True

        if cell['mine']:
            self.game_over = True
            cell['blasted'] = True  # Mark the clicked mine
            self.reveal_all_mines()  # Reveal all mines
            return

        if cell['neighbor'] == 0:
            # Recursively reveal neighboring cells
            for dr in (-1, 0, 1):
                for dc in (-1, 0, 1):
                    nr, nc = row + dr, col + dc
                    if 0 <= nr < self.rows and 0 <= nc < self.cols:
                        if not self.board[nr][nc]['revealed']:
                            self.reveal_cell(nr, nc)

    def reveal_all_mines(self):
        """Reveals all mines on the board when the player loses."""
        for r in range(self.rows):
            for c in range(self.cols):
                cell = self.board[r][c]
                if cell['mine']:
                    if 'blasted' not in cell:
                        cell['revealed'] = True  # Reveal all mines
                elif cell['flagged']:  # Incorrectly flagged mines
                    cell['false_flagged'] = True  # Mark as falsemine

    def toggle_flag(self, row, col):
        if self.game_over:
            return
        cell = self.board[row][col]
        if cell['revealed']:
            return
        cell['flagged'] = not cell['flagged']

    def check_win(self):
        # Player wins when all non-mine cells are revealed.
        for r in range(self.rows):
            for c in range(self.cols):
                cell = self.board[r][c]
                if not cell['mine'] and not cell['revealed']:
                    return False
        return True

# --------------------------------------------------
# Widget to display the game board using SVG icons
# --------------------------------------------------
class MinesweeperWidget(QtWidgets.QWidget):
    cell_size = 32  # Adjust cell size as needed

    def __init__(self, game, parent=None):
        super().__init__(parent)
        self.game = game
        self.setFixedSize(self.game.cols * self.cell_size, self.game.rows * self.cell_size)
        self.renderers = {}  # Store QSvgRenderers, not QPixmaps
        self.load_resources()

        # Track mouse state
        self.mouse_pressed = False
        self.hovered_cell = None
        self.setMouseTracking(True)

        # Ensure the widget can receive key events
        self.setFocusPolicy(QtCore.Qt.FocusPolicy.StrongFocus)

    def load_svg_renderer(self, relative_path):
        base_path = os.path.dirname(os.path.abspath(__file__))
        full_path = os.path.join(base_path, relative_path)

        if not os.path.exists(full_path):
            print(f"Error: {full_path} does not exist.")
            return None  # Return None on error

        return QtSvg.QSvgRenderer(full_path)

    def load_resources(self):
        # Load the cell images from the resources directory.
        self.renderers['unrevealed'] = self.load_svg_renderer("resources/svg/cells/cellup.svg")
        self.renderers['flag'] = self.load_svg_renderer("resources/svg/cells/cellflag.svg")
        self.renderers['mine'] = self.load_svg_renderer("resources/svg/cells/cellmine.svg")
        self.renderers['empty'] = self.load_svg_renderer("resources/svg/cells/celldown.svg")
        self.renderers['blast'] = self.load_svg_renderer("resources/svg/cells/blast.svg")
        self.renderers['falsemine'] = self.load_svg_renderer("resources/svg/cells/falsemine.svg")
        # Load numbers 1-8 for revealed cells
        for i in range(1, 9):
            self.renderers[str(i)] = self.load_svg_renderer(f"resources/svg/cells/cell{i}.svg")

        # Remove any renderers that failed to load
        self.renderers = {k: v for k, v in self.renderers.items() if v is not None}


    def paintEvent(self, event):
        with QtGui.QPainter(self) as painter:
            for r in range(self.game.rows):
                for c in range(self.game.cols):
                    cell = self.game.board[r][c]
                    x = c * self.cell_size
                    y = r * self.cell_size
                    rect = QtCore.QRectF(x, y, self.cell_size, self.cell_size)

                    if cell['revealed']:
                        if cell['mine']:
                            if 'blasted' in cell and cell['blasted']:
                                renderer = self.renderers.get('blast')  # Show explosion for clicked mine
                            else:
                                renderer = self.renderers.get('mine')  # Show regular mine
                        else:
                            renderer = self.renderers.get(str(cell['neighbor']) if cell['neighbor'] > 0 else 'empty')
                    elif 'false_flagged' in cell:
                        renderer = self.renderers.get('falsemine')  # Incorrect flag
                    else:
                        if (self.mouse_pressed and self.hovered_cell == (r, c)):                            
                            renderer = self.renderers.get('empty')  # Temporarily pressed state (celldown)
                        elif (r, c) in getattr(self, "temp_revealed_cells", []):
                            renderer = self.renderers.get('flag' if cell['flagged'] else 'empty')  # Temporarily revealed state (celldown)
                        else:
                            renderer = self.renderers.get('flag' if cell['flagged'] else 'unrevealed')

                    if renderer:
                        renderer.render(painter, rect)

    def mousePressEvent(self, event: QtGui.QMouseEvent):
        if self.game.game_over:
            return  # Ignore input after game over
    
        col = int(event.position().x() // self.cell_size)
        row = int(event.position().y() // self.cell_size)
        if not (0 <= row < self.game.rows and 0 <= col < self.game.cols):
            return
        
        cell = self.game.board[row][col]
        self.mouse_pressed = True
        self.hovered_cell = (row, col)

        # Middle click or left+right click: Temporarily reveal adjacent unrevealed squares
        if event.button() == QtCore.Qt.MouseButton.MiddleButton:
            self.mouse_pressed = False
            self.temp_reveal_adjacent(row, col)
        # Normal left-click behavior
        elif event.button() == QtCore.Qt.MouseButton.LeftButton:
            if not cell['flagged']:
                self.update()  # Show celldown.svg
        # Right click: Toggle flag
        elif event.button() == QtCore.Qt.MouseButton.RightButton:
            self.game.toggle_flag(row, col)
            self.update()

    def mouseMoveEvent(self, event: QtGui.QMouseEvent):
        if self.game.game_over:
            return  # Ignore mouse movement after game over

        col = int(event.position().x() // self.cell_size)
        row = int(event.position().y() // self.cell_size)

        if 0 <= row < self.game.rows and 0 <= col < self.game.cols:
            if event.buttons() == QtCore.Qt.MouseButton.MiddleButton:
                self.temp_reveal_adjacent(row, col)
                return
            cell = self.game.board[row][col]
            if not cell['flagged']:
                self.hovered_cell = (row, col)  # Store the last hovered cell
                self.update()  # Redraw with new hover position

    def mouseReleaseEvent(self, event: QtGui.QMouseEvent):
        if self.game.game_over:
            return  # Ignore clicks after game over

        if not self.hovered_cell:
            return

        row, col = self.hovered_cell
        self.mouse_pressed = False
        self.hovered_cell = None  # Clear hover state
        self.temp_revealed_cells = []  # Clear temporary revealed cells
        self.update()  # Redraw final state

        if 0 <= row < self.game.rows and 0 <= col < self.game.cols:
            if event.button() == QtCore.Qt.MouseButton.LeftButton:
                self.game.reveal_cell(row, col)
                # if self.game.game_over:
                #     QtWidgets.QMessageBox.critical(self, "Game Over", "You hit a mine!")
                # elif self.game.check_win():
                #     QtWidgets.QMessageBox.information(self, "Congratulations", "You win!")
            # elif event.button() == QtCore.Qt.MouseButton.RightButton:
            #     self.game.toggle_flag(row, col)

        self.update()  # Redraw final state

    def temp_reveal_adjacent(self, row, col):
        """Temporarily show all 9 squares (center + 8 adjacent) as pressed (celldown.svg)."""

        self.temp_revealed_cells = [(row, col)] if not self.game.board[row][col]["flagged"] else []  # Add center if not flagged

        for dr in (-1, 0, 1):
            for dc in (-1, 0, 1):
                nr, nc = row + dr, col + dc
                if 0 <= nr < self.game.rows and 0 <= nc < self.game.cols:
                    cell = self.game.board[nr][nc]
                    if not cell["revealed"] and not cell["flagged"] and (nr, nc) != (row, col):
                        self.temp_revealed_cells.append((nr, nc))  # Add adjacent cells
        self.update()  # Trigger a repaint

    def reveal_adjacent(self, row, col):
        """Reveals adjacent unrevealed squares if the correct number of flags are placed."""
        count_flags = sum(
            1 for dr in (-1, 0, 1) for dc in (-1, 0, 1)
            if 0 <= row + dr < self.game.rows and 0 <= col + dc < self.game.cols
            and self.game.board[row + dr][col + dc]["flagged"]
        )

        if count_flags == self.game.board[row][col]["neighbor"]:
            for dr in (-1, 0, 1):
                for dc in (-1, 0, 1):
                    nr, nc = row + dr, col + dc
                    if 0 <= nr < self.game.rows and 0 <= nc < self.game.cols:
                        if not self.game.board[nr][nc]["flagged"]:
                            self.game.reveal_cell(nr, nc)
            self.update()

    def keyPressEvent(self, event: QtGui.QKeyEvent):
        if event.key() == QtCore.Qt.Key.Key_F2:
            self.parent().new_game()  # Call new_game() from MainWindow
            return

        if self.game.game_over or not self.hovered_cell:
            return  # Ignore if game over or no hovered cell

        row, col = self.hovered_cell  # Get last hovered cell
        cell = self.game.board[row][col]

        if event.key() == QtCore.Qt.Key.Key_Space:
            if not cell["revealed"]:
                self.game.toggle_flag(row, col)
            else:
                self.reveal_adjacent(row, col)
            self.update()
           
# --------------------------------------------------
# Main window with menu bar and timer
# --------------------------------------------------
class MainWindow(QtWidgets.QMainWindow):
    DIFFICULTIES = {
        "Beginner": (9, 9, 10),
        "Intermediate": (16, 16, 40),
        "Expert": (16, 30, 99)
    }
    def __init__(self):
        super().__init__()        
        self.setWindowTitle("Minesweeper")
        self.create_menu()    
        # Start with beginner settings: 9x9 board with 10 mines.
        self.timer = QtCore.QTimer(self)
        self.timer.timeout.connect(self.update_timer)
        self.game = None
        self.board_widget = None        
        self.set_difficulty(*self.DIFFICULTIES["Beginner"])
        self.setCentralWidget(self.board_widget)
        self.elapsed_time = 0
        self.statusBar().showMessage("Time: 0")
        self.zoom_level = 100

        self.timer.start(1000)

    def create_menu(self):
        menubar = self.menuBar()
        
        # --- Game Menu ---
        game_menu = menubar.addMenu("&Game")

        new_game_action = QtGui.QAction("&New Game", self)
        new_game_action.triggered.connect(self.new_game)
        game_menu.addAction(new_game_action)

        game_menu.addSeparator()

        # Checkable difficulty settings
        self.difficulty_actions = {}

        for label, (rows, cols, mines) in self.DIFFICULTIES.items():
            action = QtGui.QAction(f"&{label}", self, checkable=True)
            action.triggered.connect(lambda checked, r=rows, c=cols, m=mines: self.set_difficulty(r, c, m))
            self.difficulty_actions[label] = action
            game_menu.addAction(action)

        # Custom Game Option
        custom_action = QtGui.QAction("C&ustom...", self, checkable=True)
        custom_action.triggered.connect(self.show_custom_dialog)
        self.difficulty_actions["Custom"] = custom_action
        game_menu.addAction(custom_action)

        game_menu.addSeparator()

        exit_action = QtGui.QAction("E&xit", self)
        exit_action.triggered.connect(self.close)
        game_menu.addAction(exit_action)

        # --- Display Menu ---
        display_menu = menubar.addMenu("&Display")

        self.zoom_actions = {}  # Store zoom actions to toggle
        for zoom in [100, 150, 200]:
            zoom_action = QtGui.QAction(f"{zoom}%", self, checkable=True)
            zoom_action.triggered.connect(lambda checked, z=zoom: self.set_zoom(z))
            self.zoom_actions[zoom] = zoom_action
            display_menu.addAction(zoom_action)

        self.zoom_actions[100].setChecked(True)  # Default zoom

        # --- Import/Export Menu ---
        import_menu = menubar.addMenu("&Import")
        export_menu = menubar.addMenu("&Export")

        import_action = QtGui.QAction("&Import", self)
        import_action.triggered.connect(self.import_game)
        import_menu.addAction(import_action)

        export_action = QtGui.QAction("&Export", self)
        export_action.triggered.connect(self.export_game)
        export_menu.addAction(export_action)

        # Lock window resizing
        self.setFixedSize(self.size())

    def new_game(self):
        """Starts a new game with the currently selected difficulty."""
        difficulty_settings = self.DIFFICULTIES.get(self.selected_difficulty, None)

        if difficulty_settings:
            rows, cols, mines = difficulty_settings
        else:
            # If custom, retain the last custom settings
            rows, cols, mines = self.game.rows, self.game.cols, self.game.mines

        self.set_difficulty(rows, cols, mines)

    def set_difficulty(self, rows, cols, mines):
        """Sets the selected difficulty and unchecks others."""
        self.timer.stop()
        self.elapsed_time = 0
        self.statusBar().showMessage("Time: 0")

        # Uncheck all difficulty actions
        for action in self.difficulty_actions.values():
            action.setChecked(False)

        # Find and check the selected difficulty
        for label, action in self.difficulty_actions.items():
            if (rows, cols, mines) == self.DIFFICULTIES.get(label, None):
                action.setChecked(True)
                self.selected_difficulty = label
                break
        else:
            # Custom game selected
            self.difficulty_actions["Custom"].setChecked(True)
            self.selected_difficulty = "Custom"

        # Set the new game settings
        self.game = MinesweeperGame(rows, cols, mines)
        if self.board_widget:
            self.board_widget.game = self.game
        else:
            self.board_widget = MinesweeperWidget(self.game)

        # Adjust board size dynamically
        self.board_widget.setFixedSize(cols * self.board_widget.cell_size, rows * self.board_widget.cell_size)
        self.setFixedSize(self.board_widget.width(), self.board_widget.height() + self.menuBar().height() + self.statusBar().height())

        self.board_widget.update()
        self.timer.start(1000)
    
    def show_custom_dialog(self):
        """Opens the custom field dialog and sets the new game board size."""
        dialog = CustomFieldDialog(self)
        if dialog.exec():
            height, width, mines = dialog.getValues()
            self.set_difficulty(height, width, mines)

    def set_zoom(self, zoom_level):
        """Updates the zoom level and resizes the board and UI elements."""
        for action in self.zoom_actions.values():
            action.setChecked(False)
        self.zoom_actions[zoom_level].setChecked(True)

        self.zoom_level = zoom_level

        # Adjust sizes
        new_size = int(32 * (zoom_level / 100))  # Scale cell size
        self.board_widget.cell_size = new_size
        self.board_widget.setFixedSize(self.game.cols * new_size, self.game.rows * new_size)

        # Adjust the entire window
        self.setFixedSize(self.board_widget.width(), self.board_widget.height() + self.menuBar().height() + self.statusBar().height())
        
        self.board_widget.update()  # Redraw the board

    def export_game(self):
        """Saves a compressed game state including difficulty and zoom level to a JSON file."""
        
        # Function to compress board data
        def encode_cell(cell):
            if cell["mine"]:
                return "M"
            if cell["revealed"]:
                return "R"
            if cell["flagged"]:
                return "F"
            if cell["neighbor"] > 0:
                return f"N{cell['neighbor']}"
            return "E"

        compressed_board = [[encode_cell(cell) for cell in row] for row in self.game.board]

        game_state = {
            "rows": self.game.rows,
            "cols": self.game.cols,
            "mines": self.game.mines,
            "board": compressed_board,  # Now stored as a compact list
            "game_over": self.game.game_over,
            "selected_difficulty": self.selected_difficulty,  # Save difficulty
            "zoom_level": self.zoom_level  # Save zoom level
        }

        filename, _ = QtWidgets.QFileDialog.getSaveFileName(self, "Save Game", "", "JSON Files (*.json)")
        
        if filename:
            with open(filename, "w") as f:
                json.dump(game_state, f)
            QtWidgets.QMessageBox.information(self, "Export Successful", "Game saved successfully.")


    def import_game(self):
        """Loads a compressed game state including difficulty and zoom settings from a JSON file."""
        filename, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Load Game", "", "JSON Files (*.json)")

        if filename:
            with open(filename, "r") as f:
                game_state = json.load(f)

            # Function to decode compressed board data
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
            self.game.calculate_neighbors()
            self.game.game_over = game_state["game_over"]

            # Restore difficulty
            difficulty = game_state.get("selected_difficulty", "Custom")
            self.selected_difficulty = difficulty

            for action in self.difficulty_actions.values():
                action.setChecked(False)
            if difficulty in self.difficulty_actions:
                self.difficulty_actions[difficulty].setChecked(True)

            # Restore zoom level
            zoom_level = game_state.get("zoom_level", 100)
            self.set_zoom(zoom_level)

            self.board_widget.game = self.game
            self.board_widget.update()

            QtWidgets.QMessageBox.information(self, "Import Successful", "Game loaded successfully.")

    def update_timer(self):
        if not self.game.game_over:
            self.elapsed_time += 1
            self.statusBar().showMessage(f"Time: {self.elapsed_time}")

    def about(self):
        QtWidgets.QMessageBox.about(self, "About Minesweeper",
                                    "Minesweeper Game built with PyQt6\nInspired by the classic Minesweeper.")

class CustomFieldDialog(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowTitle("Custom Field Settings")
        self.setFixedSize(250, 200)

        formLayout = QtWidgets.QFormLayout()

        self.heightInput = QtWidgets.QSpinBox()
        self.heightInput.setRange(9, 24)
        self.heightInput.setValue(20)  # Default

        self.widthInput = QtWidgets.QSpinBox()
        self.widthInput.setRange(9, 30)
        self.widthInput.setValue(30)  # Default

        self.minesInput = QtWidgets.QSpinBox()
        self.minesInput.setRange(10, 668)
        self.minesInput.setValue(145)  # Default

        formLayout.addRow("Height:", self.heightInput)
        formLayout.addRow("Width:", self.widthInput)
        formLayout.addRow("Mines:", self.minesInput)

        buttonBox = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.StandardButton.Ok | QtWidgets.QDialogButtonBox.StandardButton.Cancel)
        buttonBox.accepted.connect(self.accept)
        buttonBox.rejected.connect(self.reject)

        mainLayout = QtWidgets.QVBoxLayout()
        mainLayout.addLayout(formLayout)
        mainLayout.addWidget(buttonBox)
        self.setLayout(mainLayout)

    def getValues(self):
        """Returns the user-selected height, width, and mine count."""
        return (self.heightInput.value(),
                self.widthInput.value(),
                self.minesInput.value())

# --------------------------------------------------
# Main entry point
# --------------------------------------------------
def main():
    app = QtWidgets.QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == '__main__':
    main()
