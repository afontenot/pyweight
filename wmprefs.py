from PyQt5 import uic
from PyQt5.QtWidgets import QDialog, QDialogButtonBox

from wmsettings import WMSettings

class Preferences(WMSettings):
    defaults = {
        "open_prev": True,
        "prev_plan": "",
        "language": "English"
    }

    conversions = {
        "open_prev": bool
    }

    def __init__(self):
        super().__init__(self.defaults, self.conversions)

class PreferencesWindow(QDialog):
    def __init__(self, parent, *args, **kwargs):
        super().__init__(*args, **kwargs)
        uic.loadUi("ui/settings.ui", self)

        self.parent = parent

        self.config_buttons.button(QDialogButtonBox.Cancel).clicked.connect(self.reject)
        self.config_buttons.button(QDialogButtonBox.Ok).clicked.connect(self.accept)
        self.config_buttons.button(QDialogButtonBox.Cancel).setEnabled(False)

        # connect signals
        self.reopen_cbox.stateChanged.connect(self.reopen_toggled)

    def _set_modified(self):
        self.config_buttons.button(QDialogButtonBox.Cancel).setEnabled(True)

    def reopen_toggled(self):
        reopen_enabled = bool(self.reopen_cbox.checkState())
        def fn(): self.parent.prefs.open_prev = reopen_enabled
        self.parent.inflight_preference_changes["open_prev"] = fn
        self._set_modified()
