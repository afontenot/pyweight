from PyQt5.QtCore import QSettings


# A wrapped Setting object that behaves like its underlying
# value, but contains a (passed) function that stores an in
# flight change to its value that hasn't yet been saved.
class Setting:
    def __init__(self, name, value, inflight):
        self.__name = name
        # there's nothing wrong, in theory, with using a Setting as a value
        # but it can't be pickled (by QSettings), so keep the real value around
        self._raw = value
        self.__inflight = inflight

    def inflight(self, value):
        self.__inflight(value)


# class builder function: returns an appropriate subclass of Setting
# for the value provided; special handling for bools (can't be sublassed)
def get_setting(name, value, inflight):
    if isinstance(value, bool):

        class BoolSetting(Setting):
            def __bool__(self):
                return self._raw

        return BoolSetting(name, value, inflight)

    # multi-inheritance so that our Setting behaves exactly like value's type
    class VarSetting(Setting, type(value)):
        def __new__(cls, name, value, inflight):
            return super().__new__(cls, value)

    return VarSetting(name, value, inflight)


# A simple subclass of QSettings to provide slighter better behavior
# including proper handling of type conversions and defaults
# Each property specified in the `settings` dict can be accessed
# directly as a property of a WmSettings instance.
class WMSettings:
    def __init__(self, settings, conversions, path=None):
        if path:
            self.__qs = QSettings(path, QSettings.IniFormat)
        else:
            self.__qs = QSettings()

        self.__defaults = settings
        self.__settings = settings.keys()  # just for clarity
        self.__conversions = conversions
        self.__inflight = {}

    def __getattr__(self, attr):
        if attr in self.__settings:
            # we expect anything with no conversion to return a str, so
            # make this assumption explicit
            conversion = self.__conversions.get(attr, str)
            value = self.__qs.value(attr, self.__defaults[attr], type=conversion)

            def inflight(value):
                self.__inflight[attr] = value

            return get_setting(attr, value, inflight)
        else:
            raise AttributeError(f"{attr} is not a valid setting for {self}.")

    def __setattr__(self, attr, value):
        if attr.startswith("_WMSettings"):
            super().__setattr__(attr, value)
        elif attr in self.__settings:
            # QSettings can't accept our Setting class, so send the raw value
            if isinstance(value, Setting):
                value = value._raw
            self.__qs.setValue(attr, value)
        else:
            raise AttributeError(f"{attr} is not a valid setting for {self}.")

    # save inflight
    def save(self):
        for key, value in self.__inflight.items():
            self.__setattr__(key, value)
        self.flush()

    # clear inflight
    def flush(self):
        self.__inflight.clear()
