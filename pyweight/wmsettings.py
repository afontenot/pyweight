from PyQt5.QtCore import QSettings


class Setting:
    """A wrapped Setting object that behaves like its underlying value.

    Do not create instances of this class directly, call `get_setting` instead.

    Instances of this class should also inherit a basic Python type (int, str, etc).

    Objects of this class behave (in most cases, use caution) exactly like the
    types they mimic, but this class provides an additional method to class
    owners (Settings instances), in that they contain a callback intended to
    store an inflight (i.e. modified setting) on the parent.

    The parent can implement methods to save or flush these settings as desired.
    Note that Setting instances are read-only; attempts to edit them should change
    attributes on the parent Settings instance instead.

    Init:
        name: the name of the Setting (FIXME: unused?)
        value: the underlying value stored in the setting; never modified
        inflight: the method provided by the parent to save inflights
    """

    def __init__(self, name, value, inflight):
        self.__name = name
        # there's nothing wrong, in theory, with using a Setting as a value
        # but it can't be pickled (by QSettings), so keep the real value around
        self._raw = value
        self.__inflight = inflight

    def inflight(self, value):
        """Set an inflight value of the Setting on the parent Settings."""
        self.__inflight(value)


def get_setting(name, value, inflight):
    """Returns an appropriate subclass of Setting for the type.

    Usually we want a transparent class that inherits both the Setting
    class and the type of the value given. However, bools are singletons
    in Python, so they require special handling.
    """
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


class WMSettings:
    """A simple subclass of QSettings providing better behavior.

    Properly handles type conversions and defaults.
    Provides facilities for saving inflight settings, and perforaming
    coversions. Each property specified in the `settings` dict can be
    accessed directly as a property of a WMSettings instance.

    This class should be subclassed for convenience.

    Init:
        settings: a dict mapping all available settings to their defaults
        conversions: a dict mapping settings to type conversions where needed
        path: when given, use a specific INI file for settings (else Qt default)

    Attributes:
        [settings]: all settings known to the class are available as attributes
    """

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

    def save(self):
        """Safe inflights to the underlying QSettings."""
        for key, value in self.__inflight.items():
            self.__setattr__(key, value)
        self.flush()

    def flush(self):
        """Delete all inflights."""
        self.__inflight.clear()
