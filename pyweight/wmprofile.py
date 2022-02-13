from PyQt5 import uic
from PyQt5.QtWidgets import QDialog, QDialogButtonBox, QMessageBox

from pyweight.wmsettings import WMSettings


class Profile(WMSettings):
    defaults = {
        "wcrate": -1 / 7,  # lbs/day
        "cycle": 14,
        "path": "",
        "units": "imperial",
        "always_show_adj": True,
        "body_fat_method": "automatic",
        "age": 25,
        "height": 65,
        "gender_selection": "none",
        "gender_prop": 0.5,
        "manual_body_fat": 0.25,
    }

    conversions = {
        "wcrate": float,
        "cycle": int,
        "always_show_adj": bool,
        "age": int,
        "height": float,
        "gender_prop": float,
        "manual_body_fat": float,
    }

    def __init__(self, path):
        super().__init__(self.defaults, self.conversions, path)

    @property
    def height_unit(self):
        return "in" if self.units == "imperial" else "cm"

    @property
    def weight_unit(self):
        return "lbs" if self.units == "imperial" else "kg"


class ProfileWindow(QDialog):
    def __init__(self, parent, mode, *args, **kwargs):
        super().__init__(*args, **kwargs)
        uic.loadUi("ui/profilemanager.ui", self)

        self.config = parent.plan
        self.inflight = parent.inflight_profile_changes
        self.save = parent.save_prefs
        self.mode = mode

        # initialize GUI
        self._init_gui()

        # connect signals
        self.config_buttons.button(QDialogButtonBox.Cancel).clicked.connect(self.reject)
        self.config_buttons.button(QDialogButtonBox.Apply).clicked.connect(
            self._apply_changes
        )
        self.config_buttons.button(QDialogButtonBox.Ok).clicked.connect(self.accept)
        self.kg_radio.toggled.connect(self.kg_radio_toggled)
        self.lbs_radio.toggled.connect(self.lbs_radio_toggled)
        self.cycle_spinbox.valueChanged.connect(self.changed_cycle)
        self.show_adjust_cbox.stateChanged.connect(self.adjust_toggled)
        self.bfp_automatic_radio.toggled.connect(self.bfp_automatic_radio_toggled)
        self.bfp_manual_radio.toggled.connect(self.bfp_manual_radio_toggled)
        self.bfp_info_button.clicked.connect(self.bfp_info_button_clicked)
        self.age_spinbox.valueChanged.connect(self.changed_age)
        self.height_spinbox.valueChanged.connect(self.changed_height)
        self.wcrate_spin_box.valueChanged.connect(self.changed_wcrate)
        self.sex_slider.valueChanged.connect(self.changed_sex_prop)
        self.manual_bfp_spinbox.valueChanged.connect(self.changed_manual_bfp)
        self.bfp_male_radio.toggled.connect(self.changed_gender)
        self.bfp_female_radio.toggled.connect(self.changed_gender)
        self.bfp_othergender_radio.toggled.connect(self.changed_gender)

        # store units used in the dialog before they are saved in the main window
        self.current_height_unit = self.config.height_unit
        self.current_weight_unit = self.config.weight_unit

        self.show()

    def _init_gui(self):
        # set up buttons
        if self.mode == "new":
            self.config_buttons.button(QDialogButtonBox.Cancel).setHidden(True)
            self.config_buttons.button(QDialogButtonBox.Apply).setHidden(True)
        self.config_buttons.button(QDialogButtonBox.Cancel).setEnabled(False)
        self.config_buttons.button(QDialogButtonBox.Apply).setEnabled(False)
        # set UI values
        self.kg_radio.setChecked(bool(self.config.units == "metric"))
        self.cycle_spinbox.setValue(self.config.cycle)
        self.show_adjust_cbox.setChecked(bool(self.config.always_show_adj))
        self.bfp_automatic_radio.setChecked(
            bool(self.config.body_fat_method == "automatic")
        )
        self.bfp_manual_radio.setChecked(bool(self.config.body_fat_method == "manual"))
        self.age_spinbox.setValue(self.config.age)
        self.sex_slider.setValue(round(self.config.gender_prop * 100))
        self.manual_bfp_spinbox.setValue(self.config.manual_body_fat * 100)
        self._enable_disable_bfpitems(self.config.body_fat_method == "automatic")
        self.bfp_female_radio.setChecked(bool(self.config.gender_selection == "female"))
        self.bfp_male_radio.setChecked(bool(self.config.gender_selection == "male"))
        self.bfp_othergender_radio.setChecked(
            bool(self.config.gender_selection == "other")
        )
        self._enable_disable_customgender(self.config.gender_selection == "other")

        # special handling for inputs with units attached
        # we convert here from <unit>/day to <unit>/wk
        self.wcrate_spin_box.setValue(self.config.wcrate * 7)
        self.wcrate_spin_box.setSuffix(f" {self.config.weight_unit}/wk")
        self.height_spinbox.setValue(self.config.height)
        self.height_spinbox.setSuffix(f" {self.config.height_unit}")

    def _set_modified(self):
        self.config_buttons.button(QDialogButtonBox.Cancel).setEnabled(True)
        self.config_buttons.button(QDialogButtonBox.Apply).setEnabled(True)

    def _apply_changes(self):
        self.config_buttons.button(QDialogButtonBox.Cancel).setEnabled(False)
        self.config_buttons.button(QDialogButtonBox.Apply).setEnabled(False)
        self.save(self.inflight)
        # need to refresh GUI to pick up changes to units, if any
        self._init_gui()

    def _enable_disable_bfpitems(self, automatic_mode):
        automatic_items = (
            self.bfp_info_button,
            self.age_label,
            self.age_spinbox,
            self.height_label,
            self.height_spinbox,
            self.gender_selection_gbox,
        )
        manual_items = (self.manual_bfp_label, self.manual_bfp_spinbox)
        for item in automatic_items:
            item.setEnabled(automatic_mode)
        for item in manual_items:
            item.setEnabled(not automatic_mode)

    def _enable_disable_customgender(self, is_other):
        nonbinary_items = (
            self.sex_label_1,
            self.sex_label_2,
            self.sex_slider,
            self.usage_advice_label,
        )
        for item in nonbinary_items:
            item.setEnabled(is_other)

    def _set_height_ui_unit(self, unit):
        if self.current_height_unit == unit:
            return
        if unit == "cm":
            self.height_spinbox.setValue(self.height_spinbox.value() * 2.54)
        elif unit == "in":
            self.height_spinbox.setValue(self.height_spinbox.value() / 2.54)
        else:
            raise ValueError(f"Invalid unit: {unit}")
        self.height_spinbox.setSuffix(f" {unit}")
        self.current_height_unit = unit

    def _set_weight_ui_unit(self, unit):
        if self.current_weight_unit == unit:
            return
        current_target = self.wcrate_spin_box.value()
        if unit == "kg":
            self.wcrate_spin_box.setValue(current_target * 0.45359237)
            self.wcrate_spin_box.setMinimum(-3 * 0.45359237)
            self.wcrate_spin_box.setMaximum(3 * 0.45359237)
        elif unit == "lbs":
            self.wcrate_spin_box.setValue(current_target / 0.45359237)
            self.wcrate_spin_box.setMinimum(-3)
            self.wcrate_spin_box.setMaximum(3)
        else:
            raise ValueError(f"Invalid unit: {unit}")
        self.wcrate_spin_box.setSuffix(f" {unit}/wk")
        self.current_weight_unit = unit

    # all these functions create and store functions that modify the setting
    # they don't actually execute until the user accepts the dialog
    def kg_radio_toggled(self):
        if self.kg_radio.isChecked():
            self.inflight[self.config.units] = "metric"
            self._set_height_ui_unit("cm")
            self._set_weight_ui_unit("kg")
        self._set_modified()

    def lbs_radio_toggled(self):
        if self.lbs_radio.isChecked():
            self.inflight[self.config.units] = "imperial"
            self._set_height_ui_unit("in")
            self._set_weight_ui_unit("lbs")
        self._set_modified()

    def changed_cycle(self, value):
        self.inflight[self.config.cycle] = value
        self._set_modified()

    def adjust_toggled(self):
        adjust_enabled = bool(self.show_adjust_cbox.checkState())
        self.inflight[self.config.always_show_adj] = adjust_enabled
        self._set_modified()

    def bfp_automatic_radio_toggled(self):
        if self.bfp_automatic_radio.isChecked():
            self.inflight[self.config.body_fat_method] = "automatic"
            self._set_modified()
            self._enable_disable_bfpitems(True)
            # have to set this manually because they aren't linked in UI
            self.bfp_manual_radio.setChecked(False)

    def bfp_manual_radio_toggled(self):
        if self.bfp_manual_radio.isChecked():
            self.inflight[self.config.body_fat_method] = "manual"
            self._set_modified()
            self._enable_disable_bfpitems(False)
            self.bfp_automatic_radio.setChecked(False)

    def bfp_info_button_clicked(self):
        mbox = QMessageBox()
        mbox.setIcon(QMessageBox.Information)
        mbox.setText(
            "The program needs to know your initial body fat percentage (BFP) "
            "in order to estimate how your body composition will change after "
            "a given amount of body weight change. If you know your precise "
            "BFP, you should use manual mode.\n\n"
            "The automatic method attempts to estimate your BFP with the "
            "CUN-BAE method. This will only be a rough estimate, but usually "
            "gives a result within 10% of the true value.\n\n"
            "Most users will want to set select either Female or Male. "
            "Unfortunately, most published formulae for estimating body fat "
            "assume the subject is a cisgender male or female. Users of the "
            "program who are non-binary or are transgender and in the process "
            "of hormone replacement therapy may find a binary choice gives "
            "inaccurate results. Therefore, this program provides a slider "
            "which uses a weighted average of the two options instead, in the "
            "hope that the resulting approximation will be useful to some. "
            "Clearly this approach will not suffice for everyone, and we "
            "apologize for this limitation."
        )
        mbox.exec()

    def changed_age(self, value):
        self.inflight[self.config.age] = value
        self._set_modified()

    def changed_height(self, value):
        self.inflight[self.config.height] = value
        self._set_modified()

    def changed_wcrate(self, value):
        # we convert here from <unit>/wk to <unit>/day
        self.inflight[self.config.wcrate] = value / 7
        self._set_modified()

    def changed_sex_prop(self, value):
        # we convert here from percentage to decimal
        self.inflight[self.config.gender_prop] = value / 100
        self._set_modified()

    def changed_gender(self):
        if self.bfp_male_radio.isChecked():
            self.inflight[self.config.gender_selection] = "male"
        elif self.bfp_female_radio.isChecked():
            self.inflight[self.config.gender_selection] = "female"
        elif self.bfp_othergender_radio.isChecked():
            self.inflight[self.config.gender_selection] = "other"
        self._enable_disable_customgender(self.bfp_othergender_radio.isChecked())
        self._set_modified()

    def changed_manual_bfp(self, value):
        self.inflight[self.config.manual_body_fat] = value / 100
        self._set_modified()
