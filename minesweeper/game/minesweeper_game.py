import random

class MinesweeperGame:
    def __init__(self, rows, cols, mines, main_window=None):
        self.rows = rows
        self.cols = cols
        self.mines = mines
        self.board = self._create_board(rows, cols)
        self.game_over = False
        self.game_started = False
        self.mines_left = mines
        self.main_window = main_window  # Reference to the MainWindow for callbacks

    def _create_board(self, rows, cols):
        """Creates the initial game board with empty cells."""
        return [
            [
                {'mine': False, 'revealed': False, 'flagged': False, 'neighbor': 0, 'blasted': False, 'false_flagged': False}
                for _ in range(cols)
            ]
            for _ in range(rows)
        ]

    def initialize_board(self):
        """Initializes the board (used for resetting)."""
        self.reset_board()
        self.calculate_neighbors()

    def reset_board(self):
        """Resets the board to the initial state."""
        self.game_over = False
        self.game_started = False
        self.mines_left = self.mines
        for r in range(self.rows):
            for c in range(self.cols):
                self.board[r][c] = {'mine': False, 'revealed': False, 'flagged': False, 'neighbor': 0, 'blasted': False, 'false_flagged': False}


    def place_mines(self, start_row, start_col):
        """Places mines randomly, avoiding the starting cell."""
        positions = [(r, c) for r in range(self.rows) for c in range(self.cols) if (r, c) != (start_row, start_col)]
        mine_positions = random.sample(positions, self.mines)
        for r, c in mine_positions:
            self.board[r][c]['mine'] = True
        self.calculate_neighbors()

    def calculate_neighbors(self):
        """Calculates the number of neighboring mines for each cell."""
        for r in range(self.rows):
            for c in range(self.cols):
                if self.board[r][c]['mine']:
                    continue
                count = sum(
                    1 for dr in (-1, 0, 1) for dc in (-1, 0, 1)
                    if 0 <= r + dr < self.rows and 0 <= c + dc < self.cols and self.board[r + dr][c + dc]['mine']
                )
                self.board[r][c]['neighbor'] = count

    def reveal_cell(self, row, col):
        """Reveals a cell and handles game logic."""
        if not self.game_started:
            self.game_started = True
            self.place_mines(row, col)  # Place mines after the first click
            if self.main_window:
                self.main_window.start_timer()

        if self.game_over:
            return

        cell = self.board[row][col]
        if cell['revealed'] or cell['flagged']:
            return

        cell['revealed'] = True

        if cell['mine']:
            self.game_over = True
            cell['blasted'] = True
            self.reveal_all_mines()
            if self.main_window:
                self.main_window.game_over_callback() # Notify MainWindow
            return

        if cell['neighbor'] == 0:
            for dr in (-1, 0, 1):
                for dc in (-1, 0, 1):
                    nr, nc = row + dr, col + dc
                    if 0 <= nr < self.rows and 0 <= nc < self.cols:
                        self.reveal_cell(nr, nc)

        self.check_win_and_callback()

    def reveal_all_mines(self):
        """Reveals all mines and marks false flags."""
        for r in range(self.rows):
            for c in range(self.cols):
                cell = self.board[r][c]
                if cell['mine']:
                    if not cell.get('blasted', False):
                        cell['revealed'] = True
                elif cell['flagged']:
                    cell['false_flagged'] = True

    def toggle_flag(self, row, col):
        """Toggles the flag state of a cell."""
        if self.game_over or self.board[row][col]['revealed']:
            return

        cell = self.board[row][col]
        if cell['flagged']:
            cell['flagged'] = False
            self.mines_left += 1
        elif self.mines_left > 0:
            cell['flagged'] = True
            self.mines_left -= 1

        self.check_win_and_callback()

    def check_win(self):
        """Checks if the game has been won."""
        for r in range(self.rows):
            for c in range(self.cols):
                if not self.board[r][c]['mine'] and not self.board[r][c]['revealed']:
                    return False
        return self.mines_left == 0

    def check_win_and_callback(self):
        """Checks for a win and triggers the callback if necessary."""
        if self.check_win():
            self.game_over = True
            if self.main_window:
                self.main_window.win_game_callback()  # Notify MainWindow

    def reveal_adjacent(self, row, col):
        """Reveals adjacent cells if the correct number of flags are placed."""
        cell = self.board[row][col]
        if not cell['revealed'] or cell['neighbor'] == 0:
            return

        flag_count = sum(
            1 for dr in (-1, 0, 1) for dc in (-1, 0, 1)
            if 0 <= row + dr < self.rows and 0 <= col + dc < self.cols and self.board[row + dr][col + dc]['flagged']
        )

        if flag_count == cell['neighbor']:
            for dr in (-1, 0, 1):
                for dc in (-1, 0, 1):
                    nr, nc = row + dr, col + dc
                    if 0 <= nr < self.rows and 0 <= nc < self.cols and not self.board[nr][nc]['flagged']:
                        self.reveal_cell(nr, nc)

        self.check_win_and_callback()