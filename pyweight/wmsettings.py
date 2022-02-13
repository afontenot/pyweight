from PyQt5.QtCore import QSettings


# Get a wrapped Setting object that behaves like its underlying
# value, but contains a setter function that changes the value.
class Setting:
    def __init__(self, name, value, setter):
        self._name = name
        self._value = value
        self.set = setter

    def __hash__(self):
        return hash(self._name)

    @property
    def raw(self):
        return type(self._value)(self)


def get_setting(name, value, setter):
    if isinstance(value, bool):

        class BoolSetting(Setting):
            def __bool__(self):
                return self._value

        return BoolSetting(name, value, setter)

    class VarSetting(Setting, type(value)):
        def __new__(cls, name, value, setter):
            return super().__new__(cls, value)

    return VarSetting(name, value, setter)


# A simple subclass of QSettings to provide slighter better behavior
# including proper handling of type conversions and defaults
# Each property specified in the `defaults` dict can be accessed
# directly as a property of a WmSettings instance.
class WMSettings:
    def __init__(self, defaults, conversions, path=None):
        if path:
            self.__qs = QSettings(path, QSettings.IniFormat)
        else:
            self.__qs = QSettings()

        self.__defaults = defaults
        self.__conversions = conversions

    def __getattr__(self, attr):
        if attr in self.__defaults:
            # we expect anything with no conversion to return a str, so
            # make this assumption explicit
            conversion = self.__conversions.get(attr, str)
            value = self.__qs.value(attr, self.__defaults[attr], type=conversion)

            def setter(value):
                if isinstance(value, Setting):
                    value = value.raw
                self.__qs.setValue(attr, value)

            return get_setting(attr, value, setter)
        else:
            raise AttributeError(f"{attr} is not a valid setting for {self}.")

    def __setattr__(self, attr, value):
        if attr.startswith("_WMSettings"):
            super().__setattr__(attr, value)
        elif attr in self.__defaults:
            self.__qs.setValue(attr, value._value)
        else:
            raise AttributeError(f"{attr} is not a valid setting for {self}.")
