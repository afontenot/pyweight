#!/usr/bin/env python3
import csv
import sys
from datetime import datetime

from PyQt5 import uic
from PyQt5.QtGui import QPixmap
from PyQt5.QtWidgets import QApplication, QDialog, QFileDialog, QMainWindow, QMessageBox

from wlplot import plot
from wmabout import AboutWindow
from wlbodymodel import WeightTracker
from wldatamodel import WeightTable
from wmprefs import Preferences, PreferencesWindow
from wlprofile import Profile, ProfileWindow

# This file contains the code for initialization and the main window class.

class MainWindow(QMainWindow):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        uic.loadUi("ui/main.ui", self)

        # disable save until a file is edited
        self.action_save_file.setEnabled(False)

        # initially hide the widgets before file is loaded
        self.tableView.setVisible(False)

        # status variables
        self.file_open = False
        self.file_modified = False
        self.plan = None
        self.canvas = None
        self.table_is_loaded = False
        self.inflight_profile_changes = {}
        self.inflight_preference_changes = {}
        self.wt = None

        # initialize preferences
        self.prefs = Preferences()
        if self.prefs.open_prev and self.prefs.prev_plan != "":
            self.open_plan_file(self.prefs.prev_plan)

        # connect signals
        self.action_new_file.triggered.connect(self.new_file)
        self.action_open_file.triggered.connect(self.open_file)
        self.action_save_file.triggered.connect(self.save_file)
        self.action_new_plan.triggered.connect(self.new_plan)
        self.action_open_plan.triggered.connect(self.open_plan)
        self.action_quit.triggered.connect(self.close)
        self.action_refresh.triggered.connect(self.refresh)
        self.action_export.triggered.connect(self.save_graph)
        self.action_plan_settings.triggered.connect(self.edit_plan)
        self.action_pyweight_settings.triggered.connect(self.edit_preferences)
        self.action_about.triggered.connect(self.show_about)
        self.action_user_guide.triggered.connect(self.show_help)

        # initialize GUI
        self.refresh_actions()

        self.show()

    ## connected callbacks for main window actions

    def new_file(self):
        path = QFileDialog.getSaveFileName(self, "New File", filter="CSV Files (*.csv)")
        if path[0] != "":
            if self.check_file_modified() == QMessageBox.Cancel:
                return
            with open(path[0], "w", newline='') as csvfile:
                writer = csv.writer(csvfile)
                # header
                writer.writerow(["Date", f"Mass ({self.plan.weight_unit})"])
                today = datetime.now()
                writer.writerow([today.strftime("%Y/%m/%d"), ""])
            self.plan.path = path[0]
            self.open_data_file()

    def open_file(self):
        path = QFileDialog.getOpenFileName(self, "Open File", filter="CSV Files (*.csv)")
        if path[0] != "":
            if self.check_file_modified() == QMessageBox.Cancel:
                return
            self.plan.path = path[0]
            self.open_data_file()

    # if convert_units is set, the existing file data
    # will be converted to those units (from the other one)
    def save_file(self, convert_units=False):
        with open(self.plan.path, "w", newline='') as csvfile:
            writer = csv.writer(csvfile)
            # header
            weight_header = self.wt.weight_colname
            if convert_units:
                weight_header = f"Mass ({self.plan.weight_unit})"
            writer.writerow(["Date", weight_header])
            for line in self.wt.csvdata:
                weight = line[2]
                if self.plan.weight_unit == "kg":
                    weight *= 0.45359237
                elif self.plan.weight_unit == "lbs":
                    weight /= 0.45359237
                writer.writerow([line[1], weight])
        self.file_modified = False
        self.action_save_file.setEnabled(False)
        self.update_window_title()

    def new_plan(self):
        path = QFileDialog.getSaveFileName(self, "New File", filter="Plan Files (*.wmplan)")
        if path[0] != "":
            self.open_plan_file(path[0])
            self.edit_plan(mode="new")
        return

    def open_plan(self):
        path = QFileDialog.getOpenFileName(self, "Open File", filter="Plan Files (*.wmplan)")
        if path[0] != "":
            if self.check_file_modified() == QMessageBox.Cancel:
                return
            self.open_plan_file(path[0])

    def refresh(self):
        self.wt.add_dates()
        self.update_plot()

    # TODO: implement other save formats (svg, pdf?)
    def save_graph(self):
        if not self.canvas:
            return
        path = QFileDialog.getSaveFileName(self, "Save File", filter="PNG Files (*.png)")
        if path[0] != "":
            pix = QPixmap(self.canvas.size())
            self.canvas.render(pix)
            pix.save(path[0], "PNG")

    def edit_plan(self, mode=None):
        profile_window = ProfileWindow(self, mode)
        ret = profile_window.exec()
        if ret != QDialog.Accepted:
            return
        self.save_prefs(self.inflight_profile_changes)
        if not mode == "new":
            self.refresh()

    def edit_preferences(self):
        prefs_window = PreferencesWindow(self)
        ret = prefs_window.exec()
        if ret != QDialog.Accepted:
            return
        self.save_prefs(self.inflight_preference_changes)
        self.refresh()

    def show_about(self):
        about_window = AboutWindow(app.applicationVersion())
        about_window.exec()

    def show_help(self):
        mbox = QMessageBox()
        mbox.setIcon(QMessageBox.Information)
        mbox.setText("Not yet implemented.")
        mbox.setInformativeText("See Github for usage instructions.")
        mbox.setStandardButtons(QMessageBox.Ok)
        mbox.setDefaultButton(QMessageBox.Ok)
        mbox.exec()

    ## utilities that can be called by any other method in this class

    # make sure enabled actions make sense for what the user can actually do
    def refresh_actions(self):
        plan_active_actions = (
            self.action_new_file,
            self.action_open_file,
            self.action_save_file,
            self.action_plan_settings
        )
        file_open_actions = (
            self.action_refresh,
            self.action_export
        )
        for action in plan_active_actions:
            action.setEnabled(not self.plan is None)
        for action in file_open_actions:
            action.setEnabled(self.file_open)

    def check_file_modified(self):
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

    def save_prefs(self, prefs_list):
        # special handling if the user changed the default units
        for setting in prefs_list:
            # we have a bunch of functions to run that apply the updates
            prefs_list[setting]()
            # if the units changed as the result of the previous step,
            # we resave the user's data file to use the preferred units
            if setting == "units" and self.plan.units != self.wt.units:
                self.save_file(True)
                self.open_data_file()
        prefs_list = {}

    def open_data_file(self):
        try:
            with open(self.plan.path, newline='') as csvfile:
                reader = csv.reader(csvfile)
                self.wt = WeightTable(parent=self.tableView, csvf=reader)
        except Exception as e: # FIXME: use finally here instead?
            # file not found / corrupt / etc
            mbox = QMessageBox()
            mbox.setIcon(QMessageBox.Warning)
            # not "Pythonic", but saves redundant code
            if type(e) == FileNotFoundError:
                mbox.setText(f"{self.plan.path} could not be opened.")
            else:
                print(e)
                mbox.setText("File could not be opened.")
            mbox.exec()
            return

        self.file_open = True
        self.file_modified = False
        self.update_window_title()

        self.update_table()
        self.refresh()
        self.refresh_actions()

        self.wt.dataChanged.connect(self.table_changed)

    # FIXME: error handling like open_data_file
    def open_plan_file(self, path):
        self.plan = Profile(path)
        self.refresh_actions()
        self.prefs.prev_plan = path
        if self.prefs.open_prev and self.plan.path != "":
            self.open_data_file()

    def table_changed(self):
        if self.table_is_loaded:
            self.file_modified = True
            self.action_save_file.setEnabled(True)
            self.update_window_title()
            self.refresh()

    def update_window_title(self):
        title = "Weight Manager"
        if self.file_open:
            fn = self.plan.path.split("/")[-1]
            if self.file_modified:
                fn += "*"
            title = fn + " - " + title
        self.setWindowTitle(title)

    def update_plot(self):
        if self.canvas:
            self.centralwidget.layout().removeWidget(self.canvas)
        weightloss = WeightTracker(self.wt, self.plan)
        self.canvas = plot(weightloss)
        self.centralwidget.layout().addWidget(self.canvas)
        self.centralwidget.layout().setStretch(0, 1)
        self.centralwidget.layout().setStretch(1, 4)

    def update_table(self):
        self.table_is_loaded = False
        self.tableView.setModel(self.wt)
        self.table_is_loaded = True
        self.tableView.setVisible(True)

    # reimplementation from QMainWindow to handle window close
    def closeEvent(self, event=None):
        if self.check_file_modified() == QMessageBox.Cancel:
            event.ignore()
            return
        event.accept()

app = QApplication(sys.argv)
app.setOrganizationName("Adam Fontenot")
app.setOrganizationDomain("adam.sh")
app.setApplicationName("Weight Manager")
app.setApplicationVersion("0.1")
w = MainWindow()
app.exec_()
