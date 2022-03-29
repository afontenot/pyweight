import pytest
from PyQt5.QtCore import Qt, QPoint
from PyQt5.QtWidgets import QDialogButtonBox

from pyweight.wmprofile import Profile, ProfileWindow


@pytest.fixture
def pw(tmp_path):
    profile_path = str(tmp_path / "settings.ini")
    profile = Profile(profile_path)
    return ProfileWindow(profile, profile.save, None)


def test_init_profilewindow(qtbot, pw):
    assert pw.config.height_unit == "in"
    assert pw.config.weight_unit == "lbs"
    for key, val in Profile.defaults.items():
        res = pw.config.__getattr__(key)
        assert res._raw == val
    assert not pw.kg_radio.isChecked()
    assert pw.lbs_radio.isChecked()
    assert pw.wcrate_spin_box.value() == -1.0
    assert pw.wcrate_spin_box.suffix() == " lbs/wk"
    assert pw.cycle_spinbox.value() == 14
    assert pw.show_adjust_cbox.isChecked()
    assert pw.age_spinbox.value() == 25
    assert pw.height_spinbox.value() == 65
    assert pw.height_spinbox.suffix() == " in"
    assert pw.bfp_info_button.isEnabled()


def test_apply_button(qtbot, pw):
    test_settings = {
        "wcrate": -2 / 7,
        "cycle": 20,
        "always_show_adj": False,
        "body_fat_method": "manual",
        "age": 30,
        "height": 60,
        "gender_selection": "female",
        "gender_prop": 0.7,
        "manual_body_fat": 0.3,
    }
    pw.show()
    qtbot.addWidget(pw)
    pw.wcrate_spin_box.clear()
    qtbot.keyClicks(pw.wcrate_spin_box, str(test_settings["wcrate"] * 7))
    pw.cycle_spinbox.clear()
    qtbot.keyClicks(pw.cycle_spinbox, str(test_settings["cycle"]))
    qtbot.mouseClick(pw.show_adjust_cbox, Qt.LeftButton)
    pw.age_spinbox.clear()
    qtbot.keyClicks(pw.age_spinbox, str(test_settings["age"]))
    pw.height_spinbox.clear()
    qtbot.keyClicks(pw.height_spinbox, str(test_settings["height"]))
    qtbot.mouseClick(pw.bfp_othergender_radio, Qt.LeftButton)
    # hacky, but qtbot doesn't seem to have a clean way to do this
    pw.sex_slider.setValue(70)
    pw.changed_sex_prop(70)
    qtbot.mouseClick(pw.bfp_female_radio, Qt.LeftButton)
    qtbot.mouseClick(pw.bfp_manual_radio, Qt.LeftButton)
    pw.manual_bfp_spinbox.clear()
    qtbot.keyClicks(pw.manual_bfp_spinbox, str(test_settings["manual_body_fat"] * 100))
    qtbot.mouseClick(pw.config_buttons.button(QDialogButtonBox.Apply), Qt.LeftButton)

    for key, val in test_settings.items():
        assert pw.config.__getattr__(key)._raw == val


def test_changed_gender(qtbot, pw):
    nonbinary_items = (
        pw.sex_label_1,
        pw.sex_label_2,
        pw.sex_slider,
        pw.usage_advice_label,
    )
    pw.show()
    qtbot.addWidget(pw)
    for item in nonbinary_items:
        assert not item.isVisible()
    qtbot.mouseClick(pw.bfp_male_radio, Qt.LeftButton)
    for item in nonbinary_items:
        assert not item.isVisible()
    qtbot.mouseClick(pw.bfp_othergender_radio, Qt.LeftButton)
    for item in nonbinary_items:
        assert item.isVisible()
    qtbot.mouseClick(pw.bfp_female_radio, Qt.LeftButton)
    for item in nonbinary_items:
        assert not item.isVisible()


# note: this only tests the parts of unit changes internal to the profile window
# the tests for the main window also need to check converting the file's units
# FIXME: always save the file in metric, convert when needed
def test_change_unit(qtbot, pw):
    pw.show()
    qtbot.addWidget(pw)
    qtbot.mouseClick(pw.kg_radio, Qt.LeftButton)
    assert pw.wcrate_spin_box.value() == round(-1 * 0.45359237, 2)
    assert pw.wcrate_spin_box.suffix() == " kg/wk"
    assert pw.height_spinbox.value() == 65 * 2.54
    assert pw.height_spinbox.suffix() == " cm"
    pw.save()
    assert pw.config.units == "metric"
    # assert pw.config.wcrate == round(-1 * 0.45359237, 2) / 7
    assert pw.config.height == 65 * 2.54
    qtbot.mouseClick(pw.lbs_radio, Qt.LeftButton)
    # assert pw.wcrate_spin_box.value() == -1
    assert pw.wcrate_spin_box.suffix() == " lbs/wk"
    assert pw.height_spinbox.value() == 65
    assert pw.height_spinbox.suffix() == " in"
    pw.save()
    assert pw.config.units == "imperial"
    # assert pw.config.wcrate == -1
    assert pw.config.height == 65


def test_change_bfp_mode(qtbot, pw):
    automatic_items = (
        pw.bfp_info_button,
        pw.age_label,
        pw.age_spinbox,
        pw.height_label,
        pw.height_spinbox,
        pw.gender_selection_gbox,
    )
    manual_items = (pw.manual_bfp_label, pw.manual_bfp_spinbox)
    pw.show()
    qtbot.addWidget(pw)
    qtbot.mouseClick(pw.bfp_manual_radio, Qt.LeftButton)
    for item in automatic_items:
        assert not item.isEnabled()
    for item in manual_items:
        assert item.isEnabled()
    qtbot.mouseClick(pw.bfp_automatic_radio, Qt.LeftButton)
    for item in automatic_items:
        assert item.isEnabled()
    for item in manual_items:
        assert not item.isEnabled()
