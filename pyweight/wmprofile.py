from PyQt5 import uic
from PyQt5.QtWidgets import QDialog, QDialogButtonBox, QMessageBox

from pyweight.wmsettings import WMSettings
from pyweight.wmutils import lbs_to_kg, kg_to_lbs, m_to_in, m_to_cm, in_to_m, cm_to_m


# set reasonable limits to the weekly wc rate
WCRATE_MAX_LBS = 3
WCRATE_MIN_LBS = -1 * WCRATE_MAX_LBS
WCRATE_MAX_KG = round(lbs_to_kg(WCRATE_MAX_LBS), 2)
WCRATE_MIN_KG = -1 * WCRATE_MAX_KG


class Profile(WMSettings):
    defaults = {
        "wcrate": -0.4536 / 7,  # kg/day
        "cycle": 14,
        "path": "",
        "units": "imperial",
        "always_show_adj": True,
        "body_fat_method": "automatic",
        "age": 25,
        "height": 1.651,  # meters
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


class ProfileWindow(QDialog):
    def __init__(self, profile, save_fn, mode, *args, **kwargs):
        super().__init__(*args, **kwargs)
        uic.loadUi("pyweight/ui/profilemanager.ui", self)
        self.setFixedSize(self.size())

        # the Profile class in use by the parent
        self.config = profile
        self.save = save_fn
        self.mode = mode

        # store units used in the dialog before they are saved in the main window
        self.current_units = self.config.units
        self.current_height = self.config.height
        self.current_wcrate = self.config.wcrate

        # initialize GUI
        self._init_gui()

        # connect signals
        self.config_buttons.button(QDialogButtonBox.Cancel).clicked.connect(self.reject)
        self.config_buttons.button(QDialogButtonBox.Apply).clicked.connect(self._apply)
        self.config_buttons.button(QDialogButtonBox.Ok).clicked.connect(self.accept)
        self.units_buttongroup.buttonClicked.connect(self.changed_units)
        self.cycle_spinbox.valueChanged.connect(self.changed_cycle)
        self.show_adjust_cbox.stateChanged.connect(self.adjust_toggled)
        self.bfp_mode_buttongroup.buttonClicked.connect(self.changed_bfp_mode)
        self.bfp_info_button.clicked.connect(self.bfp_info_button_clicked)
        self.age_spinbox.valueChanged.connect(self.changed_age)
        self.height_spinbox.valueChanged.connect(self.changed_height)
        self.wcrate_spin_box.valueChanged.connect(self.changed_wcrate)
        self.sex_slider.valueChanged.connect(self.changed_sex_prop)
        self.manual_bfp_spinbox.valueChanged.connect(self.changed_manual_bfp)
        self.bfp_male_radio.toggled.connect(self.changed_gender)
        self.bfp_female_radio.toggled.connect(self.changed_gender)
        self.bfp_othergender_radio.toggled.connect(self.changed_gender)

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
        self._update_wcrate()
        self._update_height()

    def _set_modified(self):
        self.config_buttons.button(QDialogButtonBox.Cancel).setEnabled(True)
        self.config_buttons.button(QDialogButtonBox.Apply).setEnabled(True)

    def _apply(self):
        self.config_buttons.button(QDialogButtonBox.Cancel).setEnabled(False)
        self.config_buttons.button(QDialogButtonBox.Apply).setEnabled(False)
        self.save()
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
            item.setVisible(is_other)

    def _update_height(self):
        if self.current_units == "metric":
            value = m_to_cm(self.current_height)
        else:
            value = m_to_in(self.current_height)
        self.height_spinbox.blockSignals(True)
        self.height_spinbox.setValue(value)
        self.height_spinbox.blockSignals(False)
        unit = "cm" if self.current_units == "metric" else "in"
        self.height_spinbox.setSuffix(f" {unit}")

    def _update_wcrate(self):
        value = self.current_wcrate
        if self.current_units == "metric":
            self.wcrate_spin_box.setMinimum(WCRATE_MIN_KG)
            self.wcrate_spin_box.setMaximum(WCRATE_MAX_KG)
        else:
            value = kg_to_lbs(value)
            self.wcrate_spin_box.setMinimum(WCRATE_MIN_LBS)
            self.wcrate_spin_box.setMaximum(WCRATE_MAX_LBS)
        self.wcrate_spin_box.blockSignals(True)
        self.wcrate_spin_box.setValue(7 * value)
        self.wcrate_spin_box.blockSignals(False)
        unit = "kg" if self.current_units == "metric" else "lbs"
        self.wcrate_spin_box.setSuffix(f" {unit}/wk")

    # all these functions create and store functions that modify the setting
    # they don't actually execute until the user accepts the dialog
    def changed_units(self):
        new_units = "metric" if self.kg_radio.isChecked() else "imperial"
        if self.current_units == new_units:
            return
        self.current_units = new_units
        self._update_height()
        self._update_wcrate()
        self.config.units.inflight(new_units)
        self._set_modified()

    def changed_cycle(self, value):
        self.config.cycle.inflight(value)
        self._set_modified()

    def adjust_toggled(self):
        adjust_enabled = bool(self.show_adjust_cbox.checkState())
        self.config.always_show_adj.inflight(adjust_enabled)
        self._set_modified()

    def changed_bfp_mode(self):
        if self.bfp_automatic_radio.isChecked():
            self.config.body_fat_method.inflight("automatic")
        else:
            self.config.body_fat_method.inflight("manual")
        self._enable_disable_bfpitems(self.bfp_automatic_radio.isChecked())
        self._set_modified()

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
        self.config.age.inflight(value)
        self._set_modified()

    def changed_height(self, value):
        if self.current_units == "metric":
            value = cm_to_m(value)
        else:
            value = in_to_m(value)
        self.config.height.inflight(value)
        self.current_height = value
        self._set_modified()

    def changed_wcrate(self, value):
        # we convert here from <unit>/wk to <unit>/day
        value /= 7
        if self.current_units == "imperial":
            value = lbs_to_kg(value)
        self.config.wcrate.inflight(value)
        self.current_wcrate = value
        self._set_modified()

    def changed_sex_prop(self, value):
        # we convert here from percentage to decimal
        self.config.gender_prop.inflight(value / 100)
        self._set_modified()

    def changed_gender(self):
        if self.bfp_male_radio.isChecked():
            self.config.gender_selection.inflight("male")
        elif self.bfp_female_radio.isChecked():
            self.config.gender_selection.inflight("female")
        elif self.bfp_othergender_radio.isChecked():
            self.config.gender_selection.inflight("other")
        self._enable_disable_customgender(self.bfp_othergender_radio.isChecked())
        self._set_modified()

    def changed_manual_bfp(self, value):
        self.config.manual_body_fat.inflight(value / 100)
        self._set_modified()
