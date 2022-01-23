from PyQt5.QtCore import QSettings

# A simple subclass of QSettings to provide slighter better behavior
# including proper handling of type conversions and defaults

# Each property specified in the `defaults` dict can be accessed
# directly as a property of a WmSettings instance.
class WMSettings(QSettings):
    def __init__(self, defaults, conversions, path=None):
        if path:
            super().__init__(path, QSettings.IniFormat)
        else:
            super().__init__()

        # for safety, prove that none of the chosen setting names
        # already exist as inherited attributes of QSettings
        for setting in defaults:
            assert(not hasattr(super(), setting))

        self.defaults = defaults
        self.conversions = conversions

    def __getattr__(self, attr):
        if attr in self.defaults:
            # we expect anything with no conversion to return a str, so
            # make this assumption explicit
            conversion = self.conversions.get(attr, str)
            value = super().value(attr, self.defaults[attr], type=conversion)
            return value
        return super().__getattr__(attr)

    def __setattr__(self, attr, value):
        if attr in self.defaults:
            super().setValue(attr, value)
        else:
            super().__setattr__(attr, value)
