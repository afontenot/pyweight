from PyQt5.QtCore import QSettings

defaults = {
    "wlrate": 5,
    "cycle": 14,
    "path": "",
    "open_prev": True,
    "units": "lbs",
    "always_show_adj": True
}

conversions = {
    "wlrate": float,
    "cycle": int,
    "open_prev": bool,
    "always_show_adj": bool
}

# Each property specified in the `defaults` dict can be accessed
# directly as a property of a WlSettings instance.
class WlSettings(QSettings):
    def __init__(self):
        super().__init__()
        # for safety, prove that none of the chosen setting names
        # already exist as inherited attributes of QSettings
        for setting in defaults:
            assert(not hasattr(super(), setting))

    def __getattr__(self, attr):
        if attr in defaults:
            # QSettings saves bool False as "false"; workaround:
            if conversions.get(attr) == bool:
                value = super().value(attr, defaults[attr], type=bool)
            else:
                value = super().value(attr, defaults[attr])
            if attr in conversions:
                value = conversions[attr](value)
            return value
        return super().__getattr__(attr)

    def __setattr__(self, attr, value):
        if attr in defaults:
            super().setValue(attr, value)
        else:
            super().__setattr__(attr, value)

    @property
    def rate(self):
        return self.wlrate / -30
