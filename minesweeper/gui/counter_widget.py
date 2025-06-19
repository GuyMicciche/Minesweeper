import os
from pathlib import Path
from PyQt6 import QtWidgets, QtGui, QtCore, QtSvg

class CounterWidget(QtWidgets.QWidget):
    def __init__(self, scale_factor=1, initial_value=0, parent=None):
        super().__init__(parent)
        self.value = initial_value
        self.load_resources()
        self.set_value(initial_value)
        self.scale_factor = scale_factor
        self.width_ = int(26 * self.scale_factor)
        self.height_ = int(50 * self.scale_factor)
        self.setFixedSize(3 * self.width_, self.height_)  # Fixed Size

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
        """Loads SVG resources for the counter digits."""
        self.renderers = {}
        for i in range(10):
            self.renderers[i] = self.load_svg_renderer(f"resources/svg/counter/counter{i}.svg")
        self.renderers['-'] = self.load_svg_renderer("resources/svg/counter/counter-.svg")
        self.renderers = {k: v for k, v in self.renderers.items() if v is not None} # Remove fails

    def set_value(self, value):
        """Sets the counter value and updates the display."""
        self.value = value
        self.update()

    def paintEvent(self, event):
        """Paints the counter digits."""
        with QtGui.QPainter(self) as painter:
            value_str = f"{self.value:03}"
            if self.value < 0:
                value_str = f"-{-self.value:02}"

            for i, digit in enumerate(value_str):
                x = i * self.width_
                y = 0
                rect = QtCore.QRectF(x, y, self.width_, self.height_)
                if digit == '-':
                    renderer = self.renderers.get('-')
                else:
                    renderer = self.renderers.get(int(digit))
                if renderer:
                    renderer.render(painter, rect)

    def set_cell_size(self, scale):
        """Sets the cell size and updates the widget size, locking it."""
        self.scale_factor = scale
        self.width_ = int(26 * self.scale_factor)
        self.height_ = int(50 * self.scale_factor)
        self.setFixedSize(3 * self.width_, self.height_)  # Fixed Size
        self.update()