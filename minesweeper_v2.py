import json
import os
import sys
import random
from PyQt6 import QtWidgets, QtGui, QtCore, QtSvg

# --------------------------------------------------
# Game logic class (Modified for game state tracking)
# --------------------------------------------------
class MinesweeperGame:
    def __init__(self, rows, cols, mines, main_window=None):
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
        self.game_started = False  # Track if the first click has occurred
        self.mines_left = mines   # Track remaining mines
        self.main_window = main_window  # Reference to MainWindow
        self.initialize_board()

    def initialize_board(self):
        # Board is initialized, but mines are placed on the first click
        self.reset_board()
        self.calculate_neighbors()

    def reset_board(self):
        for r in range(self.rows):
            for c in range(self.cols):
                self.board[r][c] = {'mine': False, 'revealed': False, 'flagged': False, 'neighbor': 0, 'blasted':False, 'false_flagged': False}

    def place_mines(self, start_row, start_col):
        """Places mines randomly, avoiding the starting cell."""
        positions = [(r, c) for r in range(self.rows) for c in range(self.cols) if (r, c) != (start_row, start_col)]
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
        if not self.game_started:
            self.game_started = True
            self.place_mines(row, col)  # Place mines after the first click
            
            # Ensure the timer starts when the game begins
            if hasattr(self, "main_window") and self.main_window:
                self.main_window.start_timer()

        if self.game_over:
            return

        cell = self.board[row][col]
        if cell['revealed'] or cell['flagged']:
            return

        cell['revealed'] = True
        if cell['mine']:
            self.game_over = True
            cell['blasted'] = True  # Mark the clicked mine
            self.reveal_all_mines()
            if self.main_window:
                self.main_window.game_over_callback()
            return

        if cell['neighbor'] == 0:
            for dr in (-1, 0, 1):
                for dc in (-1, 0, 1):
                    nr, nc = row + dr, col + dc
                    if 0 <= nr < self.rows and 0 <= nc < self.cols:
                        if not self.board[nr][nc]['revealed']:
                            self.reveal_cell(nr, nc)
        
        # **Check if the player has won**
        if self.check_win() and self.main_window:
            self.main_window.win_game_callback()


    def reveal_all_mines(self):
        """Reveals all mines when the game is lost."""
        for r in range(self.rows):
            for c in range(self.cols):
                cell = self.board[r][c]
                if cell['mine']:
                    # Ensure the clicked mine is marked as "blasted"
                    if 'blasted' in cell and cell['blasted']:
                        continue  # Skip because it's already marked
                    cell['revealed'] = True  # Reveal all mines
                elif cell['flagged'] and not cell['mine']:
                    # Mark false flags
                    cell['false_flagged'] = True

    def toggle_flag(self, row, col):
        if self.game_over:
            return
        cell = self.board[row][col]
        if cell['revealed']:
            return

        if cell['flagged']:
            cell['flagged'] = False
            self.mines_left += 1  # Increment mines_left when a flag is removed
        else:
            if self.mines_left > 0:  # Only allow flagging if mines are left
                cell['flagged'] = True
                self.mines_left -= 1  # Decrement mines_left when a flag is placed

        # **Check if the player has won after flagging a mine**
        if self.check_win() and self.main_window:
            self.main_window.win_game_callback()

    def check_win(self):
        for r in range(self.rows):
            for c in range(self.cols):
                cell = self.board[r][c]
                if not cell['mine'] and not cell['revealed']:
                    return False
        if self.mines_left == 0:  # Check if all mines are flagged
            self.game_over = True  # Set game_over to True when won
            return True
        return False


    def reveal_adjacent(self, row, col):
        """Reveals adjacent unrevealed squares if the correct number of flags are placed."""
        cell = self.board[row][col]
        
        # Only allow this action on revealed numbered cells
        if not cell['revealed'] or cell['neighbor'] == 0:
            return

        # Count the flags around the cell
        count_flags = sum(
            1 for dr in (-1, 0, 1) for dc in (-1, 0, 1)
            if 0 <= row + dr < self.rows and 0 <= col + dc < self.cols
            and self.board[row + dr][col + dc]["flagged"]
        )

        # If the number of adjacent flags matches the cell's number, reveal adjacent non-flagged cells
        if count_flags == cell["neighbor"]:
            for dr in (-1, 0, 1):
                for dc in (-1, 0, 1):
                    nr, nc = row + dr, col + dc
                    if 0 <= nr < self.rows and 0 <= nc < self.cols:
                        if not self.board[nr][nc]["flagged"]:
                            self.reveal_cell(nr, nc)

        # **Check if the player has won**
        if self.check_win() and self.main_window:
            self.main_window.win_game_callback()


# --------------------------------------------------
# Widget for the Minesweeper board (Modified)
# --------------------------------------------------
class MinesweeperWidget(QtWidgets.QWidget):
    def __init__(self, game, parent=None):
        super().__init__(parent)
        self.game = game
        self.cell_size = 32  # Initial cell size
        self.load_resources()
        self.mouse_pressed = False
        self.hovered_cell = None
        self.setMouseTracking(True)
        self.setFocusPolicy(QtCore.Qt.FocusPolicy.StrongFocus)
        self.temp_revealed_cells = []
        self.setFixedSize(self.game.cols * self.cell_size, (self.game.rows * self.cell_size) + int(self.cell_size/2))

        # Store reference to MainWindow explicitly
        self.parent_window = parent  # Ensure we have the correct reference

    def load_svg_renderer(self, relative_path):
        base_path = os.path.dirname(os.path.abspath(__file__))
        full_path = os.path.join(base_path, relative_path)
        if not os.path.exists(full_path):
            print(f"Error: {full_path} does not exist.")
            return None  # Return None on error
        return QtSvg.QSvgRenderer(full_path)

    def load_resources(self):
        self.renderers = {}
        self.renderers['unrevealed'] = self.load_svg_renderer("resources/svg/cells/cellup.svg")
        self.renderers['flag'] = self.load_svg_renderer("resources/svg/cells/cellflag.svg")
        self.renderers['mine'] = self.load_svg_renderer("resources/svg/cells/cellmine.svg")
        self.renderers['empty'] = self.load_svg_renderer("resources/svg/cells/celldown.svg")
        self.renderers['blast'] = self.load_svg_renderer("resources/svg/cells/blast.svg")
        self.renderers['falsemine'] = self.load_svg_renderer("resources/svg/cells/falsemine.svg")
        for i in range(1, 9):
            self.renderers[str(i)] = self.load_svg_renderer(f"resources/svg/cells/cell{i}.svg")
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
                            renderer = self.renderers.get('blast' if 'blasted' in cell and cell['blasted'] else 'mine')
                        else:
                            renderer = self.renderers.get(str(cell['neighbor']) if cell['neighbor'] > 0 else 'empty')
                    elif 'false_flagged' in cell and cell['false_flagged']:
                        renderer = self.renderers.get('falsemine')
                    else:
                         if (self.mouse_pressed and self.hovered_cell == (r, c)):
                             renderer = self.renderers.get('empty')
                         elif (r, c) in getattr(self, "temp_revealed_cells", []):
                             renderer = self.renderers.get('flag' if cell['flagged'] else 'empty')
                         else:
                            renderer = self.renderers.get('flag' if cell['flagged'] else 'unrevealed')
                    if renderer:
                        renderer.render(painter, rect)

    def mousePressEvent(self, event: QtGui.QMouseEvent):
        if self.game.game_over:  return
        col = int(event.position().x() // self.cell_size)
        row = int(event.position().y() // self.cell_size)
        if not (0 <= row < self.game.rows and 0 <= col < self.game.cols): return

        cell = self.game.board[row][col]
        self.mouse_pressed = True
        self.hovered_cell = (row, col)

        if event.button() == QtCore.Qt.MouseButton.MiddleButton or (event.buttons() == (QtCore.Qt.MouseButton.LeftButton | QtCore.Qt.MouseButton.RightButton)):
            self.mouse_pressed = False # Middle/both click don't press the cell
            self.temp_reveal_adjacent(row, col)
            self.parent_window.left_mouse_press_callback()
        elif event.button() == QtCore.Qt.MouseButton.LeftButton:
            if not cell['flagged']:
                self.update()
            self.parent_window.left_mouse_press_callback()
        elif event.button() == QtCore.Qt.MouseButton.RightButton:
            self.game.toggle_flag(row, col)
            self.update()
            self.parent_window.update_mines_display()

    def mouseMoveEvent(self, event: QtGui.QMouseEvent):
        if self.game.game_over: return        

        col = int(event.position().x() // self.cell_size)
        row = int(event.position().y() // self.cell_size)

        if 0 <= row < self.game.rows and 0 <= col < self.game.cols:
            # **Mouse is inside a valid square**
            if self.hovered_cell != (row, col):  # Only update if it has changed
                if event.buttons() == QtCore.Qt.MouseButton.MiddleButton or (event.buttons() == (QtCore.Qt.MouseButton.LeftButton | QtCore.Qt.MouseButton.RightButton)):
                    self.parent_window.left_mouse_press_callback()
                    self.temp_reveal_adjacent(row, col)
                cell = self.game.board[row][col]
                if not cell['flagged']:
                    self.hovered_cell = (row, col)
                    self.update()
        else:
            # **Mouse has moved off the grid or outside a square**
            self.parent_window.left_mouse_release_callback()
            if self.hovered_cell is not None:
                self.hovered_cell = None
                self.temp_revealed_cells = []
                self.update()

    def mouseReleaseEvent(self, event: QtGui.QMouseEvent):
        self.parent_window.left_mouse_release_callback()

        if self.game.game_over or not self.hovered_cell: return        

        row, col = self.hovered_cell

        if 0 <= row < self.game.rows and 0 <= col < self.game.cols:
            if event.button() == QtCore.Qt.MouseButton.LeftButton and not self.temp_revealed_cells:
                self.game.reveal_cell(row, col)
            elif event.button() == QtCore.Qt.MouseButton.MiddleButton or \
                (event.buttons() == (QtCore.Qt.MouseButton.LeftButton | QtCore.Qt.MouseButton.RightButton)):
                self.game.reveal_adjacent(row, col)  # **Middle-click reveals adjacent squares**
            
        self.mouse_pressed = False
        self.hovered_cell = None
        self.temp_revealed_cells = []
        self.update()

        # **Check if the player has won**
        if self.game.check_win():
            self.parent_window.win_game_callback()

    def leaveEvent(self, event: QtCore.QEvent):
        """Reset hovered cell and mouse press state when mouse leaves the grid."""
        self.hovered_cell = None
        self.mouse_pressed = False
        self.update() # Ensure UI updates when mouse leaves

    def temp_reveal_adjacent(self, row, col):
        self.temp_revealed_cells = [(row, col)] if not self.game.board[row][col]["flagged"] else []
        for dr in (-1, 0, 1):
            for dc in (-1, 0, 1):
                nr, nc = row + dr, col + dc
                if 0 <= nr < self.game.rows and 0 <= nc < self.game.cols:
                    cell = self.game.board[nr][nc]
                    if not cell["revealed"] and not cell["flagged"] and (nr, nc) != (row, col):
                        self.temp_revealed_cells.append((nr, nc))
        self.update()

    def keyPressEvent(self, event: QtGui.QKeyEvent):
        if event.key() == QtCore.Qt.Key.Key_F2:
            self.parent().new_game()
            return
        if self.game.game_over or not self.hovered_cell: return
        row, col = self.hovered_cell
        cell = self.game.board[row][col]

        if event.key() == QtCore.Qt.Key.Key_Space:
            if not cell["revealed"]:
                self.game.toggle_flag(row, col)
                self.parent_window.update_mines_display()
            self.update()

    def set_cell_size(self, size):
        self.cell_size = size
        self.setFixedSize(self.game.cols * self.cell_size, (self.game.rows * self.cell_size) + int(self.cell_size/2))
        self.update()

# --------------------------------------------------
# Widget for the counter display
# --------------------------------------------------
class CounterWidget(QtWidgets.QWidget):
    def __init__(self, initial_value=0, parent=None):
        super().__init__(parent)
        self.cell_size = 16
        self.value = initial_value
        self.load_resources()
        self.set_value(initial_value)  # Initialize with 000
        self.setFixedSize(3 * 26, 50)  # Adjust size

    def load_svg_renderer(self, relative_path):
        base_path = os.path.dirname(os.path.abspath(__file__))
        full_path = os.path.join(base_path, relative_path)
        if not os.path.exists(full_path):
            print(f"Error: {full_path} does not exist.")
            return None
        return QtSvg.QSvgRenderer(full_path)
    def load_resources(self):
        self.renderers = {}
        for i in range(10):
            self.renderers[i] = self.load_svg_renderer(f"resources/svg/counter/counter{i}.svg")
        self.renderers['-'] = self.load_svg_renderer("resources/svg/counter/counter-.svg")
        self.renderers = {k: v for k, v in self.renderers.items() if v is not None} # Remove failed

    def set_value(self, value):
        self.value = value
        self.update()

    def paintEvent(self, event):
        with QtGui.QPainter(self) as painter:
            value_str = f"{self.value:03}"  # Format as 3 digits with leading zeros
            if self.value < 0:
                value_str = f"-{-self.value:02}"
            for i, digit in enumerate(value_str):
                x = i * 26  # space between digits
                y = 0
                rect = QtCore.QRectF(x, y, 26, 50)  # Size of each digit
                if digit == '-':
                    renderer = self.renderers.get('-')
                else:
                    renderer = self.renderers.get(int(digit))
                if renderer:
                    renderer.render(painter, rect)

# --------------------------------------------------
# Widget for the face button
# --------------------------------------------------
class FaceButton(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.main_window = parent  # Store MainWindow reference
        self.state = 'smile'  # Initial state
        self.load_resources()
        self.setFixedSize(50, 50)  # Adjust size as needed
        self.mouse_pressed = False

    def load_svg_renderer(self, relative_path):
        base_path = os.path.dirname(os.path.abspath(__file__))
        full_path = os.path.join(base_path, relative_path)
        if not os.path.exists(full_path):
            print(f"Error: {full_path} does not exist.")
            return None
        return QtSvg.QSvgRenderer(full_path)

    def load_resources(self):
        self.renderers = {}
        self.renderers['smile'] = self.load_svg_renderer("resources/svg/faces/smileface.svg")
        self.renderers['click'] = self.load_svg_renderer("resources/svg/faces/clickface.svg")
        self.renderers['win'] = self.load_svg_renderer("resources/svg/faces/winface.svg")
        self.renderers['lose'] = self.load_svg_renderer("resources/svg/faces/lostface.svg")
        self.renderers['smile_down'] = self.load_svg_renderer("resources/svg/faces/smilefacedown.svg")
        self.renderers = {k: v for k, v in self.renderers.items() if v is not None}

    def paintEvent(self, event):
        with QtGui.QPainter(self) as painter:
            rect = QtCore.QRectF(0, 0, self.width(), self.height())
            if self.mouse_pressed:
                renderer = self.renderers.get('smile_down')
            else:
                renderer = self.renderers.get(self.state)
            if renderer:
                renderer.render(painter, rect)

    def mousePressEvent(self, event: QtGui.QMouseEvent):
        if event.button() == QtCore.Qt.MouseButton.LeftButton:
            self.mouse_pressed = True
            self.update()            

    def mouseReleaseEvent(self, event: QtGui.QMouseEvent):
        if event.button() == QtCore.Qt.MouseButton.LeftButton:
            self.mouse_pressed = False
            self.set_state('smile')  # Reset to smile after click
            self.update()
            if self.main_window:
                self.main_window.new_game()  # Call new_game from MainWindow

    def set_state(self, state):
        self.state = state
        self.update()

# --------------------------------------------------
# Widget for drawing borders
# --------------------------------------------------
class BorderWidget(QtWidgets.QWidget):
    def __init__(self, width, height, type, parent = None):
        super().__init__(parent)
        self.cell_size = 16
        self.width_ = width
        self.height_ = height
        self.type_ = type
        self.load_resources()
        self.setFixedSize(self.width_, self.height_)

    def load_svg_renderer(self, relative_path):
        base_path = os.path.dirname(os.path.abspath(__file__))
        full_path = os.path.join(base_path, relative_path)
        if not os.path.exists(full_path):
            print(f"Error: {full_path} does not exist.")
            return None
        return QtSvg.QSvgRenderer(full_path)
    def load_resources(self):
        self.renderers = {}
        self.renderers["topleft"] = self.load_svg_renderer("resources/svg/border/topleft.svg")
        self.renderers["top"] = self.load_svg_renderer("resources/svg/border/top.svg")
        self.renderers["topright"] = self.load_svg_renderer("resources/svg/border/topright.svg")
        self.renderers["left"] = self.load_svg_renderer("resources/svg/border/left.svg")
        self.renderers["middleleft"] = self.load_svg_renderer("resources/svg/border/middleleft.svg")
        self.renderers["middleright"] = self.load_svg_renderer("resources/svg/border/middleright.svg")
        self.renderers["right"] = self.load_svg_renderer("resources/svg/border/right.svg")
        self.renderers["bottomleft"] = self.load_svg_renderer("resources/svg/border/bottomleft.svg")
        self.renderers["bottom"] = self.load_svg_renderer("resources/svg/border/bottom.svg")
        self.renderers["bottomright"] = self.load_svg_renderer("resources/svg/border/bottomright.svg")
        self.renderers["counterleft"] = self.load_svg_renderer("resources/svg/border/counterleft.svg")
        self.renderers["countermiddle"] = self.load_svg_renderer("resources/svg/border/countermiddle.svg")
        self.renderers["counterright"] = self.load_svg_renderer("resources/svg/border/counterright.svg")
        self.renderers = {k: v for k, v in self.renderers.items() if v is not None}

    def paintEvent(self, event):
        with QtGui.QPainter(self) as painter:
            if self.type_ == "top":
                self.draw_top_border(painter)
            elif self.type_ == "bottom":
                self.draw_bottom_border(painter)
            elif self.type_ == "counter":
                self.draw_counter_border(painter)

    def draw_top_border(self, painter):
        # Top Left
        rect = QtCore.QRectF(0, 0, self.cell_size, self.cell_size)
        self.renderers.get("topleft").render(painter, rect)
        # Top
        rect = QtCore.QRectF(self.cell_size, 0, self.width_ - (self.cell_size * 2), self.cell_size)
        self.renderers.get("top").render(painter, rect)
        # Top Right
        rect = QtCore.QRectF(self.width_ - self.cell_size, 0, self.cell_size, self.cell_size)
        self.renderers.get("topright").render(painter, rect)
        # Left
        rect = QtCore.QRectF(0, self.cell_size, self.cell_size, self.height_ - (self.cell_size * 2))
        self.renderers.get("left").render(painter, rect)
        # Right
        rect = QtCore.QRectF(self.width_ - self.cell_size, self.cell_size, self.cell_size, self.height_ - (self.cell_size * 2))
        self.renderers.get("right").render(painter, rect)
        # Bottom Left
        rect = QtCore.QRectF(0, self.height_ - self.cell_size, self.cell_size, self.cell_size)
        self.renderers.get("middleleft").render(painter, rect)
        # Bottom
        rect = QtCore.QRectF(self.cell_size, self.height_ - self.cell_size, self.width_ - (self.cell_size * 2), self.cell_size)
        self.renderers.get("top").render(painter, rect)
        # Bottom Right
        rect = QtCore.QRectF(self.width_ - self.cell_size, self.height_ - self.cell_size, self.cell_size, self.cell_size)
        self.renderers.get("middleright").render(painter, rect)

    def draw_bottom_border(self, painter):
        # Left
        rect = QtCore.QRectF(0, 0, self.cell_size, self.height_ - self.cell_size)
        self.renderers.get("left").render(painter, rect)
        # Right
        rect = QtCore.QRectF(self.width_ - self.cell_size, 0, self.cell_size, self.height_ - self.cell_size)
        self.renderers.get("right").render(painter, rect)
        # Bottom Left
        rect = QtCore.QRectF(0, self.height_ - self.cell_size, self.cell_size, self.cell_size)
        self.renderers.get("bottomleft").render(painter, rect)
        # Bottom
        rect = QtCore.QRectF(self.cell_size, self.height_ - self.cell_size, self.width_ - (self.cell_size * 2), self.cell_size)
        self.renderers.get("bottom").render(painter, rect)
        # Bottom Right
        rect = QtCore.QRectF(self.width_ - self.cell_size, self.height_ - self.cell_size , self.cell_size, self.cell_size)
        self.renderers.get("bottomright").render(painter, rect)

    def draw_counter_border(self, painter):
        # # Left
        # rect = QtCore.QRectF(0, 0, 13, self.height_)
        # self.renderers.get("counterleft").render(painter, rect)
        # # Middle
        # rect = QtCore.QRectF(13, 0, self.width_-26, self.height_)
        # self.renderers.get("countermiddle").render(painter, rect)
        # # Right
        # rect = QtCore.QRectF(self.width_ - 13, 0, 13, self.height_)
        # self.renderers.get("counterright").render(painter, rect)
        pass

# --------------------------------------------------
# Main window (Completely Revised)
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
        self.game = None
        self.board_widget = None
        self.timer = QtCore.QTimer(self)
        self.timer.timeout.connect(self.update_timer)
        self.elapsed_time = 0
        self.zoom_level = 100
        self.create_menu()
        self.set_difficulty(*self.DIFFICULTIES["Beginner"]) # Start with beginner
        # self.timer.start(1000)  # Moved timer start to set_difficulty

    def create_menu(self):
        menubar = self.menuBar()
        game_menu = menubar.addMenu("&Game")
        new_game_action = QtGui.QAction("&New Game", self)
        new_game_action.setShortcut(QtGui.QKeySequence(QtCore.Qt.Key.Key_F2))
        new_game_action.triggered.connect(self.new_game)
        game_menu.addAction(new_game_action)
        game_menu.addSeparator()

        self.difficulty_actions = {}
        for label, (rows, cols, mines) in self.DIFFICULTIES.items():
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

        display_menu = menubar.addMenu("&Display")
        self.zoom_actions = {}
        for zoom in [100, 150, 200]:
            zoom_action = QtGui.QAction(f"{zoom}%", self, checkable=True)
            zoom_action.triggered.connect(lambda checked, z=zoom: self.set_zoom(z))
            self.zoom_actions[zoom] = zoom_action
            display_menu.addAction(zoom_action)
        self.zoom_actions[100].setChecked(True)

        import_menu = menubar.addMenu("&Import")
        export_menu = menubar.addMenu("&Export")
        import_action = QtGui.QAction("&Import", self)
        import_action.triggered.connect(self.import_game)
        import_menu.addAction(import_action)
        export_action = QtGui.QAction("&Export", self)
        export_action.triggered.connect(self.export_game)
        export_menu.addAction(export_action)

        help_menu = menubar.addMenu("&Help")
        about_action = QtGui.QAction("&About", self)
        about_action.triggered.connect(self.about)
        help_menu.addAction(about_action)

    def create_widgets(self):
        # Create central widget and layout
        central_widget = QtWidgets.QWidget()
        main_layout = QtWidgets.QVBoxLayout(central_widget)
        main_layout.setSpacing(0)  # Remove extra spacing
        main_layout.setContentsMargins(0, 0, 0, 0)

        # --- Top Panel (Counters and Face) ---
        top_panel_layout = QtWidgets.QHBoxLayout()
        top_panel_layout.setSpacing(0)

        # Wrap counters and face button with border widgets
        self.mines_counter = CounterWidget(self.game.mines)
        self.timer_counter = CounterWidget()
        self.face_button = FaceButton(self)

        mines_counter_border = BorderWidget(3*32 + 2*16, 46, "counter")
        timer_counter_border = BorderWidget(3*32 + 2*16, 46, "counter")

        # Layout for top panel elements
        mines_counter_layout = QtWidgets.QHBoxLayout(mines_counter_border)
        mines_counter_layout.addWidget(self.mines_counter)
        mines_counter_layout.setContentsMargins(0,0,0,0)
        timer_counter_layout = QtWidgets.QHBoxLayout(timer_counter_border)
        timer_counter_layout.addWidget(self.timer_counter)
        timer_counter_layout.setContentsMargins(0,0,0,0)

        top_panel_layout.addWidget(mines_counter_border)
        top_panel_layout.addStretch(1)  # Push face to the center
        top_panel_layout.addWidget(self.face_button)
        top_panel_layout.addStretch(1)  # Push timer to the right
        top_panel_layout.addWidget(timer_counter_border)

        # Wrap with a border widget
        self.top_panel_border = BorderWidget(self.board_widget.width() + 32, 96, "top")  # Adjust height as needed
        top_panel_border_layout = QtWidgets.QVBoxLayout(self.top_panel_border)
        top_panel_border_layout.addLayout(top_panel_layout)
        top_panel_border_layout.setContentsMargins(0,0,0,0)

        main_layout.addWidget(self.top_panel_border)

        # --- Game Board ---
        # Wrap the board widget with a border
        board_border = BorderWidget(self.board_widget.width() + 32, self.board_widget.height(), "bottom")
        board_layout = QtWidgets.QVBoxLayout(board_border)  # Use QVBoxLayout
        board_layout.addWidget(self.board_widget)
        board_layout.setContentsMargins(16,0,16,0) # board has 0 margins with border
        main_layout.addWidget(board_border)

        self.setCentralWidget(central_widget)

        # Initial sizing
        self.update_geometry()

    def update_geometry(self):
        """Calculates and sets the window size based on components."""
        scale_factor = self.zoom_level / 100

        board_width = self.game.cols * self.board_widget.cell_size
        board_height = self.game.rows * self.board_widget.cell_size

        # Account for borders (adjust values as needed based on your SVG sizes)
        border_width = int(32 * scale_factor) # Example: 16px on each side
        border_height = 0
        top_panel_height = int(96 * scale_factor)

        total_width = board_width + border_width
        total_height = board_height + border_height + top_panel_height + self.menuBar().height()

        #self.board_widget.setFixedSize(board_width, board_height)
        #self.setFixedSize(total_width, total_height)

    def new_game(self):
        self.timer.stop()
        self.elapsed_time = 0
        self.timer_counter.set_value(0)
        self.face_button.set_state('smile')  # Reset face
        difficulty_settings = self.DIFFICULTIES.get(self.selected_difficulty, None)
        if difficulty_settings:
            rows, cols, mines = difficulty_settings
        else:
            rows, cols, mines = self.game.rows, self.game.cols, self.game.mines
        self.set_difficulty(rows, cols, mines)  # Use set_difficulty for consistency
        self.timer.start(1000)

    def set_difficulty(self, rows, cols, mines):
        for action in self.difficulty_actions.values():
            action.setChecked(False)
        for label, action in self.difficulty_actions.items():
            if (rows, cols, mines) == self.DIFFICULTIES.get(label, None):
                action.setChecked(True)
                self.selected_difficulty = label
                break
        else:
            self.difficulty_actions["Custom"].setChecked(True)
            self.selected_difficulty = "Custom"

        self.game = MinesweeperGame(rows, cols, mines, main_window=self)
        self.game.reset_board()  # Reset the board for a new game
        if self.board_widget:
            self.board_widget.game = self.game  # Update game instance
            self.board_widget.set_cell_size(int(32 * (self.zoom_level / 100)))
            self.board_widget.update()
        else:
            self.board_widget = MinesweeperWidget(self.game, self) # Pass self (MainWindow)

        self.create_widgets()  # Recreate widgets to reflect the new board size
        self.update_mines_display()
        self.reset_timer()

    def show_custom_dialog(self):
        dialog = CustomFieldDialog(self)
        if dialog.exec():
            height, width, mines = dialog.getValues()
            self.set_difficulty(height, width, mines)

    def set_zoom(self, zoom_level):
        for action in self.zoom_actions.values():
            action.setChecked(False)
        self.zoom_actions[zoom_level].setChecked(True)
        self.zoom_level = zoom_level

        scale_factor = zoom_level / 100  # Convert percentage to factor

        # Scale Minesweeper grid
        if self.board_widget:
            new_cell_size = int(32 * scale_factor)  # Scale cell size
            self.board_widget.set_cell_size(new_cell_size)

        # Scale Face Button
        new_face_size = int(50 * scale_factor)
        self.face_button.setFixedSize(new_face_size, new_face_size)

        # Scale Counters
        new_counter_width = int(3 * 26 * scale_factor)
        new_counter_height = int(50 * scale_factor)
        self.mines_counter.setFixedSize(new_counter_width, new_counter_height)
        self.timer_counter.setFixedSize(new_counter_width, new_counter_height)

        # Scale Borders
        new_border_width = int(self.board_widget.width() + 32 * scale_factor)
        new_border_height = int(96 * scale_factor)
        self.top_panel_border.setFixedSize(new_border_width, new_border_height)

        # Update Layout and Geometry
        self.update_geometry()

    def start_timer(self):
        if not self.timer.isActive():
            self.elapsed_time = 0
            self.timer_counter.set_value(0)
            self.timer.start(1000)

    def update_timer(self):
        if not self.game.game_over and self.game.game_started:
            self.elapsed_time += 1
            self.timer_counter.set_value(self.elapsed_time)

    def reset_timer(self):
        self.timer.stop()
        self.elapsed_time = 0
        self.timer_counter.set_value(0)
        if self.game.game_started:
            self.timer.start(1000)

    def update_mines_display(self):
        self.mines_counter.set_value(self.game.mines_left)

    def game_over_callback(self):
        self.timer.stop()
        self.face_button.set_state('lose')

    def win_game_callback(self):
        self.timer.stop()
        self.face_button.set_state('win')

    def left_mouse_press_callback(self):
        if not self.game.game_over:
            self.face_button.set_state('click')

    def left_mouse_release_callback(self):
        if not self.game.game_over:
            self.face_button.set_state('smile')

    def export_game(self):
        def encode_cell(cell):
            if cell["mine"]:          return "M"
            if cell["revealed"]:      return "R"
            if cell["flagged"]:       return "F"
            if cell["neighbor"] > 0:  return f"N{cell['neighbor']}"
            return "E"
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
        filename, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Load Game", "", "JSON Files (*.json)")
        if filename:
            with open(filename, "r") as f:
                game_state = json.load(f)
            def decode_cell(symbol):
                if symbol == "M":    return {"mine": True, "revealed": False, "flagged": False, "neighbor": 0}
                if symbol == "R":    return {"mine": False, "revealed": True, "flagged": False, "neighbor": 0}
                if symbol == "F":    return {"mine": False, "revealed": False, "flagged": True, "neighbor": 0}
                if symbol.startswith("N"): return {"mine": False, "revealed": False, "flagged": False, "neighbor": int(symbol[1:])}
                return {"mine": False, "revealed": False, "flagged": False, "neighbor": 0}

            self.game = MinesweeperGame(game_state["rows"], game_state["cols"], game_state["mines"])
            self.game.board = [[decode_cell(cell) for cell in row] for row in game_state["board"]]
            self.game.calculate_neighbors()
            self.game.game_over = game_state["game_over"]
            self.game.game_started = game_state.get("game_started", False) # Default to False if not present
            self.game.mines_left = game_state.get("mines_left", self.game.mines) # Default to total mines if not present
            self.elapsed_time = game_state.get("elapsed_time", 0) # Default to 0

            difficulty = game_state.get("selected_difficulty", "Custom")
            self.selected_difficulty = difficulty
            for action in self.difficulty_actions.values():
                action.setChecked(False)
            if difficulty in self.difficulty_actions:
                self.difficulty_actions[difficulty].setChecked(True)

            zoom_level = game_state.get("zoom_level", 100)
            self.set_zoom(zoom_level)
            self.board_widget.game = self.game
            self.create_widgets()  # Recreate widgets
            self.update_mines_display()
            self.timer_counter.set_value(self.elapsed_time)

            if self.game.game_started:
                self.timer.start(1000)

            QtWidgets.QMessageBox.information(self, "Import Successful", "Game loaded successfully.")

    def about(self):
        QtWidgets.QMessageBox.about(self, "About Minesweeper",
                                    "Minesweeper Game built with PyQt6\nInspired by the classic Minesweeper.")

# --------------------------------------------------
# Custom Field Dialog (No changes needed)
# --------------------------------------------------
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