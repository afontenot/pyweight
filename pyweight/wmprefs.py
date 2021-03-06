from PyQt5 import uic
from PyQt5.QtWidgets import QDialog, QDialogButtonBox

from pyweight.wmsettings import WMSettings


class Preferences(WMSettings):
    """A class to allow instantiating preferences.

    Users could just call WMSettings directly, but this class provides
    a way for other classes to get a preferences instance without
    knowing anything about its defaults, conversions, etc.
    """

    defaults = {
        "open_prev": True,
        "auto_save_data": False,
        "prev_plan": "",
        "language": "English",
    }

    conversions = {"open_prev": bool, "auto_save_data": bool}

    def __init__(self):
        super().__init__(self.defaults, self.conversions)


class PreferencesWindow(QDialog):
    """A class to manage the preferences window UI.

    Init:
        prefs: the Preferences instance the parent wants us to manage,
            e.g. save our inflights to
    """

    def __init__(self, prefs, *args, **kwargs):
        super().__init__(*args, **kwargs)
        uic.loadUi("pyweight/ui/prefs.ui", self)
        self.setFixedSize(self.size())

        # Preferences class in use by parent window
        self.config = prefs

        self.config_buttons.button(QDialogButtonBox.Cancel).clicked.connect(self.reject)
        self.config_buttons.button(QDialogButtonBox.Ok).clicked.connect(self.accept)
        self.config_buttons.button(QDialogButtonBox.Cancel).setEnabled(False)

        self.reopen_cbox.setChecked(bool(self.config.open_prev))
        self.auto_save_cbox.setChecked(bool(self.config.auto_save_data))

        # connect signals
        self.reopen_cbox.stateChanged.connect(self.reopen_toggled)
        self.auto_save_cbox.stateChanged.connect(self.autosave_toggled)

    def _set_modified(self):
        self.config_buttons.button(QDialogButtonBox.Cancel).setEnabled(True)

    def reopen_toggled(self):
        reopen_enabled = bool(self.reopen_cbox.checkState())
        self.config.open_prev.inflight(reopen_enabled)
        self._set_modified()

    def autosave_toggled(self):
        autosave_enabled = bool(self.auto_save_cbox.checkState())
        self.config.auto_save_data.inflight(autosave_enabled)
        self._set_modified()
