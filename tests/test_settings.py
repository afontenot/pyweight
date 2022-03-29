import pytest

from pyweight.wmsettings import WMSettings


s = {"setting_bool": True, "setting_int": 2, "setting_str": "string"}
c = {"setting_bool": bool, "setting_int": int}


@pytest.fixture
def settings(tmp_path):
    s_path = str(tmp_path / "settings.ini")
    return WMSettings(s, c, s_path)


@pytest.fixture
def settings_memory():
    return WMSettings(s, c)


def test_settings_getattr(settings):
    assert settings.setting_bool
    assert settings.setting_int == 2
    assert settings.setting_str == "string"


def test_settings_setattr(settings):
    settings.setting_str = "newstring"
    # set a setting to a setting
    settings.setting_int = settings.setting_int
    assert settings.setting_str == "newstring"
    assert settings.setting_int == 2


def test_invalid_setting(settings):
    with pytest.raises(AttributeError):
        assert settings.setting_other == "other"
    with pytest.raises(AttributeError):
        settings.setting_other = "other"


def test_memory_qsettings(settings_memory):
    assert settings_memory.setting_bool


def test_save_inflight(settings):
    settings.setting_bool.inflight(False)
    assert settings.setting_bool
    settings.save()
    assert not settings.setting_bool


def test_flush_inflight(settings):
    settings.setting_bool.inflight(False)
    settings.flush()
    settings.save()
    assert settings.setting_bool
