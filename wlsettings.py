from PyQt5.QtCore import QSettings

from wlbodymodel import initial_body_fat_est

defaults = {
    "wlrate": 5,
    "cycle": 14,
    "path": "",
    "open_prev": True,
    "units": "lbs",
    "always_show_adj": True,
    "body_fat_method": "automatic",
    "age": 25,
    "height": 65,
    "height_unit": "in",
    "gender_prop": 0.5,
    "manual_body_fat": 0.25
}

conversions = {
    "wlrate": float,
    "cycle": int,
    "open_prev": bool,
    "always_show_adj": bool,
    "age": int,
    "height": float,
    "gender_prop": float,
    "manual_body_fat": float
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
