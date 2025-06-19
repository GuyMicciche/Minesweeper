import os
from pathlib import Path
from PyQt6 import QtWidgets, QtGui, QtCore, QtSvg
from game.minesweeper_game import MinesweeperGame  # Import MinesweeperGame

class MinesweeperWidget(QtWidgets.QWidget):
    def __init__(self, game: MinesweeperGame, cell_size=32, parent=None):
        super().__init__(parent)
        self.game = game
        self.cell_size = cell_size
        self.load_resources()
        self.mouse_pressed = False
        self.hovered_cell = None
        self.setMouseTracking(True)
        self.setFocusPolicy(QtCore.Qt.FocusPolicy.StrongFocus)
        self.temp_revealed_cells = []
        self.parent_window = parent  # Store MainWindow reference
        self.set_cell_size(self.cell_size) # Use set_cell_size for fixed sizing

    def load_svg_renderer(self, relative_path):
        """Loads an SVG renderer from the given path."""
        # Use pathlib.Path for robust path handling
        base_path = Path(__file__).resolve().parent.parent.parent  # Key change!
        full_path = base_path / relative_path

        if not full_path.exists():
            print(f"Error: {full_path} does not exist.")
            return None
        return QtSvg.QSvgRenderer(str(full_path))

    def load_resources(self):
        """Loads SVG resources for the cells."""
        self.renderers = {}
        self.renderers['unrevealed'] = self.load_svg_renderer("resources/svg/cells/cellup.svg")
        self.renderers['flag'] = self.load_svg_renderer("resources/svg/cells/cellflag.svg")
        self.renderers['mine'] = self.load_svg_renderer("resources/svg/cells/cellmine.svg")
        self.renderers['empty'] = self.load_svg_renderer("resources/svg/cells/celldown.svg")
        self.renderers['blast'] = self.load_svg_renderer("resources/svg/cells/blast.svg")
        self.renderers['falsemine'] = self.load_svg_renderer("resources/svg/cells/falsemine.svg")
        for i in range(1, 9):
            self.renderers[str(i)] = self.load_svg_renderer(f"resources/svg/cells/cell{i}.svg")
        # Filter out any failed loads
        self.renderers = {k: v for k, v in self.renderers.items() if v is not None}

    def paintEvent(self, event):
        """Paints the Minesweeper board."""
        with QtGui.QPainter(self) as painter:
            for r in range(self.game.rows):
                for c in range(self.game.cols):
                    cell = self.game.board[r][c]
                    x = c * self.cell_size
                    y = r * self.cell_size
                    rect = QtCore.QRectF(x, y, self.cell_size, self.cell_size)

                    if cell['revealed']:
                        if cell['mine']:
                            renderer = self.renderers.get('blast' if cell.get('blasted', False) else 'mine')
                        else:
                            renderer = self.renderers.get(str(cell['neighbor']) if cell['neighbor'] > 0 else 'empty')
                    elif cell.get('false_flagged', False):
                        renderer = self.renderers.get('falsemine')
                    else:
                        if self.mouse_pressed and self.hovered_cell == (r, c):
                            renderer = self.renderers.get('empty')
                        elif (r, c) in self.temp_revealed_cells:
                            renderer = self.renderers.get('flag' if cell['flagged'] else 'empty')
                        else:
                            renderer = self.renderers.get('flag' if cell['flagged'] else 'unrevealed')

                    if renderer:
                        renderer.render(painter, rect)

    def mousePressEvent(self, event: QtGui.QMouseEvent):
        """Handles mouse press events."""
        if self.game.game_over:
            return

        col = int(event.position().x() // self.cell_size)
        row = int(event.position().y() // self.cell_size)

        if not (0 <= row < self.game.rows and 0 <= col < self.game.cols):
            return

        cell = self.game.board[row][col]
        self.mouse_pressed = True
        self.hovered_cell = (row, col)

        if event.button() == QtCore.Qt.MouseButton.MiddleButton or (event.buttons() == (QtCore.Qt.MouseButton.LeftButton | QtCore.Qt.MouseButton.RightButton)):
            self.mouse_pressed = False  # Middle/both click don't press
            self.temp_reveal_adjacent(row, col)
            if self.parent_window:  # Check if parent_window is valid
                self.parent_window.left_mouse_press_callback()
        elif event.button() == QtCore.Qt.MouseButton.LeftButton:
            if not cell['flagged']:
                self.update()
            if self.parent_window:
                self.parent_window.left_mouse_press_callback()
        elif event.button() == QtCore.Qt.MouseButton.RightButton:
            self.game.toggle_flag(row, col)
            self.update()
            if self.parent_window:
                self.parent_window.update_mines_display()

    def mouseMoveEvent(self, event: QtGui.QMouseEvent):
        """Handles mouse move events."""
        if self.game.game_over:
            return

        col = int(event.position().x() // self.cell_size)
        row = int(event.position().y() // self.cell_size)

        if 0 <= row < self.game.rows and 0 <= col < self.game.cols:
            if self.hovered_cell != (row, col):
                if (event.buttons() == QtCore.Qt.MouseButton.MiddleButton or
                        (event.buttons() == (QtCore.Qt.MouseButton.LeftButton | QtCore.Qt.MouseButton.RightButton))):
                    if self.parent_window:
                        self.parent_window.left_mouse_press_callback()
                    self.temp_reveal_adjacent(row, col)
                    self.game.reveal_adjacent(row, col)

                cell = self.game.board[row][col]
                if not cell['flagged']:
                    self.hovered_cell = (row, col)
                    self.update()
        else:
             if self.parent_window:
                self.parent_window.left_mouse_release_callback()
             if self.hovered_cell is not None:
                self.hovered_cell = None
                self.temp_revealed_cells = []
                self.update()

    def mouseReleaseEvent(self, event: QtGui.QMouseEvent):
        """Handles mouse release events."""
        if self.parent_window:
            self.parent_window.left_mouse_release_callback()

        if self.game.game_over or not self.hovered_cell:
            return

        row, col = self.hovered_cell

        if 0 <= row < self.game.rows and 0 <= col < self.game.cols:
            if event.button() == QtCore.Qt.MouseButton.LeftButton and not self.temp_revealed_cells:
                self.game.reveal_cell(row, col)
            elif (event.button() == QtCore.Qt.MouseButton.MiddleButton or
                  (event.buttons() == (QtCore.Qt.MouseButton.LeftButton | QtCore.Qt.MouseButton.RightButton))):
                self.game.reveal_adjacent(row, col)

        self.mouse_pressed = False
        self.hovered_cell = None
        self.temp_revealed_cells = []
        self.update()

    def leaveEvent(self, event: QtCore.QEvent):
        """Handles the mouse leaving the widget."""
        self.hovered_cell = None
        self.mouse_pressed = False
        self.update()

    def temp_reveal_adjacent(self, row, col):
        """Temporarily reveals adjacent cells for the chord click."""
        self.temp_revealed_cells = [(row, col)] if not self.game.board[row][col]['flagged'] else []
        for dr in (-1, 0, 1):
            for dc in (-1, 0, 1):
                nr, nc = row + dr, col + dc
                if 0 <= nr < self.game.rows and 0 <= nc < self.game.cols:
                    cell = self.game.board[nr][nc]
                    if not cell['revealed'] and not cell['flagged'] and (nr, nc) != (row, col):
                        self.temp_revealed_cells.append((nr, nc))
        self.update()

    def keyPressEvent(self, event: QtGui.QKeyEvent):
        """Handles key press events (F2 for new game, Space to toggle flag)."""
        if event.key() == QtCore.Qt.Key.Key_F2:
            if self.parent_window:
                self.parent_window.new_game() # Call new_game on MainWindow
            return

        if self.game.game_over or not self.hovered_cell:
            return

        row, col = self.hovered_cell
        cell = self.game.board[row][col]

        if event.key() == QtCore.Qt.Key.Key_Space:
            if not cell['revealed']:
                self.game.toggle_flag(row, col)
                if self.parent_window:
                   self.parent_window.update_mines_display()
            self.update()

    def set_cell_size(self, size):
        """Sets the cell size and updates the widget size, locking it."""
        self.cell_size = int(size)
        # Lock Size
        self.setFixedSize(self.game.cols * self.cell_size, (self.game.rows * self.cell_size))
        self.update()