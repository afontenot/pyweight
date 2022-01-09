#!/usr/bin/env python3
import csv
import sys
from datetime import datetime

from PyQt5 import uic
from PyQt5.QtGui import QPixmap
from PyQt5.QtWidgets import QApplication, QDialog, QFileDialog, QMainWindow, QMessageBox

from wlplot import plot
from wlsettings import WlSettings
from wlbodymodel import WeightLoss
from wldatamodel import WeightTable
from wlprefs import PrefWindow

# This file contains the code for initialization and the main window class.

class MainWindow(QMainWindow):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        uic.loadUi("ui/main.ui", self)

        # disable save until a file is edited
        self.action_save.setEnabled(False)

        # initially hide the widgets before file is loaded
        self.set_doc_widget_visibility(False)

        # status variables
        self.file_open = False
        self.file_modified = False
        self.canvas = None
        self.table_is_loaded = False
        self.changed_settings = {}
        self.units_changed = False

        # initialize settings
        self.settings = WlSettings()
        self.wlrate_spin_box.setValue(self.settings.wlrate)
        if self.settings.open_prev and self.settings.path != "":
            self.open_file()

        # connect signals
        self.action_new.triggered.connect(self.new_file)
        self.action_open.triggered.connect(self.open_file_dialog)
        self.action_save.triggered.connect(self.save_file)
        self.action_refresh.triggered.connect(self.refresh)
        self.action_save_graph.triggered.connect(self.save_graph)
        self.action_preferences.triggered.connect(self.show_prefs)
        self.wlrate_spin_box.valueChanged.connect(self.changed_wlrate)

        self.show()

    def checkFileModified(self):
        if self.file_modified:
            mbox = QMessageBox()
            mbox.setIcon(QMessageBox.Warning)
            mbox.setText("Your log file has been modified.")
            mbox.setInformativeText("Do you want to save your changes or discard them?")
            mbox.setStandardButtons(QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel)
            mbox.setDefaultButton(QMessageBox.Save)
            resp = mbox.exec()
            if resp == QMessageBox.Save:
                self.save_file()
            return resp

    # reimplementation from QMainWindow to handle window close
    def closeEvent(self, event):
        if self.checkFileModified() == QMessageBox.Cancel:
            event.ignore()
            return
        event.accept()

    def open_file_dialog(self):
        path = QFileDialog.getOpenFileName(self, "Open File", filter="CSV Files (*.csv)")
        if self.checkFileModified() == QMessageBox.Cancel:
            return
        if path[0] != "":
            self.settings.path = path[0]
            self.open_file()

    def new_file(self):
        path = QFileDialog.getSaveFileName(self, "New File", filter="CSV Files (*.csv)")
        if path[0] != "":
            with open(path[0], "w", newline='') as csvfile:
                writer = csv.writer(csvfile)
                # header
                writer.writerow(["Date", f"Mass ({self.settings.units})"])
                today = datetime.now()
                writer.writerow([today.strftime("%Y/%m/%d"), ""])
            self.settings.path = path[0]
            self.open_file()

    # if convert_units is set to "kg" or "lbs", the existing file data
    # will be converted to that unit (from the other one)
    def save_file(self, convert_units=False):
        with open(self.settings.path, "w", newline='') as csvfile:
            writer = csv.writer(csvfile)
            # header
            weight_header = self.wt.weight_colname
            if convert_units == "kg":
                weight_header = "Mass (kg)"
            elif convert_units == "lbs":
                weight_header = "Mass (lbs)"
            writer.writerow(["Date", self.wt.weight_colname])
            for line in self.wt.csvdata:
                weight = line[2]
                if convert_units == "kg":
                    weight *= 0.45359237
                elif convert_units == "lbs":
                    weight /= 0.45359237
                writer.writerow([line[1], weight])
        self.file_modified = False
        self.action_save.setEnabled(False)
        self.update_window_title()

    def save_graph(self):
        if not self.canvas:
            return
        path = QFileDialog.getSaveFileName(self, "Save File", filter="PNG Files (*.png)")
        if path[0] != "":
            pix = QPixmap(self.canvas.size())
            self.canvas.render(pix)
            pix.save(path[0], "PNG")

    def save_prefs(self):
        # special handling if the user changed the default units
        for setting in self.changed_settings:
            if setting == "units":
                self.units_changed = True
            # we have a bunch of functions to run that apply the updates
            self.changed_settings[setting]()
        self.changed_settings = {}

    def show_prefs(self):
        pref_window = PrefWindow(self)
        ret = pref_window.exec()
        if ret != QDialog.Accepted:
            return
        self.save_prefs()

        # offer to convert units if the user changed them
        if self.units_changed and self.settings.units != self.wt.units:
            self.units_changed = False
            mbox = QMessageBox()
            mbox.setIcon(QMessageBox.Question)
            mbox.setText("You changed the default units for new files.\n" +
                         "Your current file appears to be using the old units.\n" +
                         "Would you like to convert this file to the new units?")
            mbox.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
            mbox.setDefaultButton(QMessageBox.No)
            resp = mbox.exec()
            if resp == QMessageBox.Yes:
                self.save_file(self.settings.units)
                self.open_file()
        else:
            self.refresh()

    def refresh(self):
        self.wt.add_dates()
        self.update_plot()

    def set_label_units(self):
        if self.wt.units == "kg":
            self.target_rate_label.setText("Loss Target (kg / 30 days)")
            self.wlrate_spin_box.setMaximum(6.5)
            # handle case where value is too high after switch
            if self.settings.wlrate > 6.5:
                self.wlrate_spin_box.setValue(2)
        elif self.wt.units == "lbs":
            self.target_rate_label.setText("Loss Target (lbs / 30 days)")
            self.wlrate_spin_box.setMaximum(15)

    def open_file(self):
        try:
            with open(self.settings.path, newline='') as csvfile:
                reader = csv.reader(csvfile)
                self.wt = WeightTable(parent=self.tableView, csvf=reader)
        except Exception as e:
            # file not found / corrupt / etc
            mbox = QMessageBox()
            mbox.setIcon(QMessageBox.Warning)
            # not "Pythonic", but saves redundant code
            if type(e) == FileNotFoundError:
                mbox.setText(f"{self.settings.path} could not be opened.")
            else:
                print(e)
                mbox.setText("File could not be opened.")
            mbox.exec()
            return

        self.file_open = True
        self.file_modified = False
        self.update_window_title()

        self.update_table()
        self.set_label_units()
        self.refresh()

        self.wt.dataChanged.connect(self.table_changed)

    def table_changed(self):
        if self.table_is_loaded:
            self.file_modified = True
            self.action_save.setEnabled(True)
            self.update_window_title()
            self.refresh()

    def update_window_title(self):
        title = "Weight Manager"
        if self.file_open:
            fn = self.settings.path.split("/")[-1]
            if self.file_modified:
                fn += "*"
            title = fn + " - " + title
        self.setWindowTitle(title)

    def changed_wlrate(self, new_rate):
        self.settings.wlrate = new_rate
        self.update_plot()

    def update_plot(self):
        if self.canvas:
            self.centralwidget.layout().removeWidget(self.canvas)
        weightloss = WeightLoss(self.wt, self.settings)
        self.canvas = plot(weightloss)
        self.centralwidget.layout().addWidget(self.canvas)
        self.centralwidget.layout().setStretch(0, 1)
        self.centralwidget.layout().setStretch(1, 4)

    def set_doc_widget_visibility(self, vis):
        self.tableView.setVisible(vis)
        self.line.setVisible(vis)
        self.target_rate_label.setVisible(vis)
        self.wlrate_spin_box.setVisible(vis)
        self.action_refresh.setEnabled(vis)
        self.action_save_graph.setEnabled(vis)

    def update_table(self):
        self.table_is_loaded = False
        self.tableView.setModel(self.wt)
        self.table_is_loaded = True
        self.set_doc_widget_visibility(True)

app = QApplication(sys.argv)
app.setOrganizationName("Adam Fontenot")
app.setOrganizationDomain("adam.sh")
app.setApplicationName("Weight Manager")
w = MainWindow()
app.exec_()
