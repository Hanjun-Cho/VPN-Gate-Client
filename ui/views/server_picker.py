from PySide6.QtCore import Signal
from PySide6.QtWidgets import QDialog, QListWidget, QVBoxLayout


class ServerPickerDialog(QDialog):
    country_selected = Signal(str)

    # popup that shows the list of available countries; selecting one emits the
    # chosen country and closes the dialog
    def __init__(self, countries, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Change Server")
        self.resize(240, 320)

        self._list = QListWidget()
        self._list.addItems(countries or [])
        self._list.itemDoubleClicked.connect(self._on_item_double_clicked)

        layout = QVBoxLayout()
        layout.addWidget(self._list)
        self.setLayout(layout)

    def _on_item_double_clicked(self, item):
        self.country_selected.emit(item.text())
        self.accept()
