from PyQt5 import uic
from PyQt5.QtWidgets import QDialog, QDialogButtonBox


class AboutWindow(QDialog):
    def __init__(self, versioninfo, *args, **kwargs):
        super().__init__(*args, **kwargs)
        uic.loadUi("pyweight/ui/about.ui", self)
        self.setFixedSize(self.size())

        self.version_label.setText(f"Version: {versioninfo}")

        self.config_buttons.button(QDialogButtonBox.Ok).clicked.connect(self.accept)
