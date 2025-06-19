from PyQt6 import QtWidgets

class CustomGameDialog(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Custom Game Settings")
        self.setFixedSize(250, 200)  # Fixed Size
        formLayout = QtWidgets.QFormLayout()

        self.heightInput = QtWidgets.QSpinBox()
        self.heightInput.setRange(9, 24)
        self.heightInput.setValue(20)
        self.widthInput = QtWidgets.QSpinBox()
        self.widthInput.setRange(9, 30)
        self.widthInput.setValue(30)
        self.minesInput = QtWidgets.QSpinBox()
        self.minesInput.setRange(10, 668)
        self.minesInput.setValue(145)

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
        """Returns the entered values."""
        return (self.heightInput.value(),
                self.widthInput.value(),
                self.minesInput.value())