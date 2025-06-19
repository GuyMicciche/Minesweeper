import os
from pathlib import Path
from PyQt6 import QtWidgets, QtGui, QtCore, QtSvg

class FaceButton(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.main_window = parent
        self.state = 'smile'
        self.load_resources()
        self.setFixedSize(50, 50)  # Fixed size
        self.mouse_pressed = False

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
        """Loads SVG resources for the face states."""
        self.renderers = {}
        self.renderers['smile'] = self.load_svg_renderer("resources/svg/faces/smileface.svg")
        self.renderers['click'] = self.load_svg_renderer("resources/svg/faces/clickface.svg")
        self.renderers['win'] = self.load_svg_renderer("resources/svg/faces/winface.svg")
        self.renderers['lose'] = self.load_svg_renderer("resources/svg/faces/lostface.svg")
        self.renderers['smile_down'] = self.load_svg_renderer("resources/svg/faces/smilefacedown.svg")
        self.renderers = {k: v for k, v in self.renderers.items() if v is not None} # Remove fails.

    def paintEvent(self, event):
        """Paints the current face state."""
        with QtGui.QPainter(self) as painter:
            rect = QtCore.QRectF(0, 0, self.width(), self.height())
            if self.mouse_pressed:
                renderer = self.renderers.get('smile_down')
            else:
                renderer = self.renderers.get(self.state)
            if renderer:
                renderer.render(painter, rect)

    def mousePressEvent(self, event: QtGui.QMouseEvent):
        """Handles mouse press events."""
        if event.button() == QtCore.Qt.MouseButton.LeftButton:
            self.mouse_pressed = True
            self.update()

    def mouseReleaseEvent(self, event: QtGui.QMouseEvent):
        """Handles mouse release events."""
        if event.button() == QtCore.Qt.MouseButton.LeftButton:
            self.mouse_pressed = False
            self.set_state('smile')
            self.update()
            if self.main_window:
                self.main_window.new_game()

    def set_state(self, state):
        """Sets the face state and updates the display."""
        self.state = state
        self.update()