import os
from pathlib import Path
from PyQt6 import QtWidgets, QtGui, QtCore, QtSvg

class BorderWidget(QtWidgets.QWidget):
    def __init__(self, width, height, border_type, scale_factor=1, parent=None):
        super().__init__(parent)
        self.cell_size = int(round(16 * scale_factor))
        self.width_ = width
        self.height_ = height
        self.type_ = border_type  # Renamed to avoid conflict with built-in type
        self.load_resources()
        self.setFixedSize(int(round(self.width_)), int(round(self.height_)))  # Use fixed dimensions

    def update_scale(self, scale_factor):
        """Update the internal rect values when scaling changes."""
        self.cell_size = int(16 * scale_factor)  # Scale cell size
        self.width_ = int(self.width_ * scale_factor)
        self.height_ = int(self.height_ * scale_factor)
        self.setFixedSize(int(round(self.width_)), int(round(self.height_)))  # Resize widget 
        self.update()  # Redraw widget

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
        """Loads SVG resources for the border elements."""
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
        self.renderers = {k: v for k, v in self.renderers.items() if v is not None} # Remove fails

    def paintEvent(self, event):
        """Paints the appropriate border based on the type."""
        with QtGui.QPainter(self) as painter:
            if self.type_ == "top":
                self.draw_top_border(painter)
            elif self.type_ == "bottom":
                self.draw_bottom_border(painter)
                self.setFixedSize(int(round(self.width_)), int(round(self.height_)) + int(self.cell_size))  # Use fixed dimensions

    def draw_top_border(self, painter):
        """Draws the top border."""
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
        """Draws the bottom border."""
        # Left
        rect = QtCore.QRectF(0, 0, self.cell_size, self.height_)
        self.renderers.get("left").render(painter, rect)
        # Right
        rect = QtCore.QRectF(self.width_ - self.cell_size, 0, self.cell_size, self.height_)
        self.renderers.get("right").render(painter, rect)
        # Bottom Left
        rect = QtCore.QRectF(0, self.height_, self.cell_size, self.cell_size)
        self.renderers.get("bottomleft").render(painter, rect)
        # Bottom
        rect = QtCore.QRectF(self.cell_size, self.height_, self.width_ - (self.cell_size * 2), self.cell_size)
        self.renderers.get("bottom").render(painter, rect)
        # Bottom Right
        rect = QtCore.QRectF(self.width_ - self.cell_size, self.height_ , self.cell_size, self.cell_size)
        self.renderers.get("bottomright").render(painter, rect)