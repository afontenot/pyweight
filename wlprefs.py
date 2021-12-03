from PyQt5 import uic
from PyQt5.QtWidgets import QDialog, QDialogButtonBox

class PrefWindow(QDialog):
    def __init__(self, parent, *args, **kwargs):
        super().__init__(*args, **kwargs)
        uic.loadUi("ui/config.ui", self)

        self.parent = parent

        # set up buttons
        self.config_buttons.button(QDialogButtonBox.Cancel).setEnabled(False)
        self.config_buttons.button(QDialogButtonBox.Apply).setEnabled(False)
        self.config_buttons.button(QDialogButtonBox.Cancel).clicked.connect(self.reject)
        self.config_buttons.button(QDialogButtonBox.Apply).clicked.connect(self._apply_changes)
        self.config_buttons.button(QDialogButtonBox.Ok).clicked.connect(self.accept)

        # initialize GUI
        self.kg_radio.setChecked(self.parent.settings.units == "kg")
        self.reopen_cbox.setChecked(self.parent.settings.open_prev)
        self.cycle_spinbox.setValue(self.parent.settings.cycle)
        self.show_adjust_cbox.setChecked(self.parent.settings.always_show_adj)
        self.bfp_automatic_radio.setChecked(self.parent.settings.body_fat_method == "automatic")
        self.bfp_manual_radio.setChecked(self.parent.settings.body_fat_method == "manual")
        self.age_spinbox.setValue(self.parent.settings.age)
        self.height_spinbox.setValue(self.parent.settings.height)
        self.height_spinbox.setSuffix(" " + self.parent.settings.height_unit)
        self.sex_slider.setValue(round(self.parent.settings.gender_prop * 100))
        self.manual_bfp_spinbox.setValue(self.parent.settings.manual_body_fat * 100)
        self._enable_disable_bfpitems(self.parent.settings.body_fat_method == "automatic")

        # connect signals
        self.kg_radio.toggled.connect(self.kg_radio_toggled)
        self.lbs_radio.toggled.connect(self.lbs_radio_toggled)
        self.reopen_cbox.stateChanged.connect(self.reopen_toggled)
        self.cycle_spinbox.valueChanged.connect(self.changed_cycle)
        self.show_adjust_cbox.stateChanged.connect(self.adjust_toggled)
        self.bfp_automatic_radio.toggled.connect(self.bfp_automatic_radio_toggled)
        self.bfp_manual_radio.toggled.connect(self.bfp_manual_radio_toggled)
        self.bfp_info_button.clicked.connect(self.bfp_info_button_clicked)
        self.age_spinbox.valueChanged.connect(self.changed_age)
        self.height_spinbox.valueChanged.connect(self.changed_height)
        self.sex_slider.valueChanged.connect(self.changed_sex)
        self.manual_bfp_spinbox.valueChanged.connect(self.changed_manual_bfp)

        # set temporary variables that hold status while the window is open
        self.current_height_unit = self.parent.settings.height_unit

        self.show()

    def _set_modified(self):
        self.config_buttons.button(QDialogButtonBox.Cancel).setEnabled(True)
        self.config_buttons.button(QDialogButtonBox.Apply).setEnabled(True)

    def _apply_changes(self):
        self.config_buttons.button(QDialogButtonBox.Cancel).setEnabled(False)
        self.config_buttons.button(QDialogButtonBox.Apply).setEnabled(False)
        self.parent.save_prefs()
        self.parent.refresh()

    def _enable_disable_bfpitems(self, automatic_mode):
        automatic_items = (
            self.bfp_info_button,
            self.age_label,
            self.age_spinbox,
            self.height_label,
            self.height_spinbox,
            self.sex_label_1,
            self.sex_label_2,
            self.sex_slider
        )
        manual_items = (
            self.manual_bfp_label,
            self.manual_bfp_spinbox
        )
        for item in automatic_items:
            item.setEnabled(automatic_mode)
        for item in manual_items:
            item.setEnabled(not automatic_mode)

    def _set_height_ui_unit(self, unit):
        if self.current_height_unit == unit:
            return
        if unit == "cm":
            self.height_spinbox.setValue(self.height_spinbox.value() * 2.54)
        elif unit == "in":
            self.height_spinbox.setValue(self.height_spinbox.value() / 2.54)
        else:
            raise ValueError("Invalid unit for height: " + str(unit))
        self.current_height_unit = unit
        self.height_spinbox.setSuffix(" " + unit)

    # all these functions create and store functions that modify the setting
    # they don't actually execute until the user accepts the dialog
    def kg_radio_toggled(self):
        if self.kg_radio.isChecked():
            def fn(): self.parent.settings.units = "kg"
            self.parent.changed_settings["units"] = fn
            self._set_height_ui_unit("cm")
        self._set_modified()

    def lbs_radio_toggled(self):
        if self.lbs_radio.isChecked():
            def fn(): self.parent.settings.units = "lbs"
            self.parent.changed_settings["units"] = fn
            self._set_height_ui_unit("in")
        self._set_modified()

    def reopen_toggled(self):
        reopen_enabled = bool(self.reopen_cbox.checkState())
        def fn(): self.parent.settings.open_prev = reopen_enabled
        self.parent.changed_settings["open_prev"] = fn
        self._set_modified()

    def changed_cycle(self, value):
        def fn(): self.parent.settings.cycle = value
        self.parent.changed_settings["cycle"] = fn
        self._set_modified()

    def adjust_toggled(self):
        adjust_enabled = bool(self.show_adjust_cbox.checkState())
        def fn(): self.parent.settings.always_show_adj = adjust_enabled
        self.parent.changed_settings["always_show_adj"] = fn
        self._set_modified()

    def bfp_automatic_radio_toggled(self):
        if self.bfp_automatic_radio.isChecked():
            def fn(): self.parent.settings.body_fat_method = "automatic"
            self.parent.changed_settings["body_fat_method"] = fn
            self._set_modified()
            self._enable_disable_bfpitems(True)
            # have to set this manually because they aren't linked in UI
            self.bfp_manual_radio.setChecked(False)

    def bfp_manual_radio_toggled(self):
        if self.bfp_manual_radio.isChecked():
            def fn(): self.parent.settings.body_fat_method = "manual"
            self.parent.changed_settings["body_fat_method"] = fn
            self._set_modified()
            self._enable_disable_bfpitems(False)
            self.bfp_automatic_radio.setChecked(False)

    def bfp_info_button_clicked(self):
        mbox = QMessageBox()
        mbox.setIcon(QMessageBox.Information)
        mbox.setText("The automatic method attempts to guess your body fat " +
                     "percentage using a method called CUN-BAE. This will " +
                     "only be a rough estimate (usually accurate within 10%). " +
                     "The program needs to know your initial BFP in order " +
                     "to calculate how much fat you can expect to lose, and " +
                     "how many calories that fat will contain. If you know " +
                     "your exact body fat percentage, you should use the " +
                     "Manual mode.\n\n" +
                     "Most users will want to set the gender slider all the " +
                     "way to either Female or Male. Unfortunately, most " +
                     "published formulae for estimating body fat assume the " +
                     "subject is a cisgender male or female. Users of the " +
                     "program who are not male or female or are in the process " +
                     "of hormone replacement therapy may find a binary choice " +
                     "gives inaccurate results. Therefore, this program provides " +
                     "a slider which will result in an estimate that is a linear " +
                     "interpolation between the two, in the hope that this will " +
                     "be useful to some users.")
        mbox.exec()

    def changed_age(self, value):
        def fn(): self.parent.settings.age = value
        self.parent.changed_settings["age"] = fn
        self._set_modified()

    def changed_height(self, value):
        def fn(): self.parent.settings.height = value
        self.parent.changed_settings["height"] = fn
        def fn2(): self.parent.settings.height_unit = self.current_height_unit
        self.parent.changed_settings["height_unit"] = fn2
        self._set_modified()

    def changed_sex(self, value):
        def fn(): self.parent.settings.gender_prop = value / 100
        self.parent.changed_settings["gender_prop"] = fn
        self._set_modified()

    def changed_manual_bfp(self, value):
        def fn(): self.parent.settings.manual_body_fat = value / 100
        self.parent.changed_settings["manual_body_fat"] = fn
        self._set_modified()
