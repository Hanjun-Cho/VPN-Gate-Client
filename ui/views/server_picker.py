from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QDialog, QListWidget, QListWidgetItem, QVBoxLayout


class PickerDialog(QDialog):
    # emits the data attached to the selected item
    selected = Signal(object)

    # popup that shows a list of (label, data) choices; selecting one emits its
    # data and closes the dialog
    def __init__(self, choices, title, parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.resize(400, 320)

        self._list = QListWidget()
        for label, data in choices:
            item = QListWidgetItem(label)
            item.setData(Qt.UserRole, data)
            self._list.addItem(item)
        self._list.itemDoubleClicked.connect(self._on_item_double_clicked)

        layout = QVBoxLayout()
        layout.addWidget(self._list)
        self.setLayout(layout)

    def _on_item_double_clicked(self, item):
        self.selected.emit(item.data(Qt.UserRole))
        self.accept()
