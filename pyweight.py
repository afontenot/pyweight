#!/usr/bin/env python3
import csv
import sys
from datetime import datetime
from os.path import exists

from PyQt5 import uic
from PyQt5.QtGui import QPixmap, QKeySequence
from PyQt5.QtWidgets import QApplication, QDialog, QFileDialog, QMainWindow, QMessageBox, QShortcut, QAbstractItemDelegate

from wmabout import AboutWindow
from wmbodymodel import WeightTracker
from wmdatamodel import WeightTable
from wmplot import Canvas
from wmprefs import Preferences, PreferencesWindow
from wmprofile import Profile, ProfileWindow

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
        # sometimes we need to move focus down a row after a QTableView update
        self.table_needs_focusmove = False
        self.inflight_profile_changes = {}
        self.inflight_preference_changes = {}
        self.wt = None

        # initialize preferences
        self.prefs = Preferences()
        if self.prefs.open_prev and self.prefs.prev_plan != "":
            if exists(self.prefs.prev_plan):
                self.open_plan_file(self.prefs.prev_plan)
            else:
                mbox = QMessageBox()
                mbox.setIcon(QMessageBox.Warning)
                mbox.setText("Previous plan file could not be opened.")
                mbox.exec()

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

        # special return key handling for tableView (move down one line)
        self._return_shortcut = QShortcut(QKeySequence("Return"), self.tableView)
        self._return_shortcut.activated.connect(self.return_key_activated)

        self.show()

    ## connected callbacks for main window actions

    def new_file(self):
        path = QFileDialog.getSaveFileName(self, "New File", filter="CSV Files (*.csv)")
        if path[0] != "":
            if self.check_file_modified() == QMessageBox.Cancel:
                return
            with open(path[0], "w", encoding="utf-8", newline='') as csvfile:
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
        with open(self.plan.path, "w", encoding="utf-8", newline='') as csvfile:
            writer = csv.writer(csvfile)
            # header
            weight_header = self.wt.weight_colname
            if convert_units:
                weight_header = f"Mass ({self.plan.weight_unit})"
            writer.writerow(["Date", weight_header])
            for line in self.wt.csvdata:
                weight = line[2]
                if convert_units:
                    if self.plan.weight_unit == "kg" and self.wt.units == "lbs":
                        weight *= 0.45359237
                    elif self.plan.weight_unit == "lbs" and self.wt.units == "kg":
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
        self.save_prefs(self.inflight_profile_changes, mode)
        if not mode == "new":
            self.update_plot()

    def edit_preferences(self):
        prefs_window = PreferencesWindow(self)
        ret = prefs_window.exec()
        if ret != QDialog.Accepted:
            return
        self.save_prefs(self.inflight_preference_changes)
        self.update_plot()

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
        return None

    def save_prefs(self, prefs_list, mode=None):
        # we have a bunch of functions to run that apply the updates
        for setting in prefs_list:
            prefs_list[setting]()
        # if the units changed as the result of the previous step,
        # we resave the user's data file to use the preferred units
        if self.plan.weight_unit != self.wt.units and mode != "new":
            self.save_file(True)
            self.open_data_file()
        prefs_list = {}

    def open_data_file(self):
        try:
            with open(self.plan.path, encoding="utf-8", newline='') as csvfile:
                reader = csv.reader(csvfile)
                self.wt = WeightTable(parent=self.tableView, csvf=reader)
        except Exception as e:
            # file not found / corrupt / etc
            mbox = QMessageBox()
            mbox.setIcon(QMessageBox.Warning)
            if isinstance(e, FileNotFoundError):
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
        self.tableView.scrollToBottom()

        self.wt.dataChanged.connect(self.table_changed)

    def open_plan_file(self, path):
        self.plan = Profile(path)
        self.refresh_actions()
        self.prefs.prev_plan = path
        if self.prefs.open_prev and self.plan.path != "":
            self.open_data_file()

    def table_changed(self):
        self.move_cursor_down()
        if self.table_is_loaded and self.wt.has_new_plottable_data:
            self.file_modified = True
            self.action_save_file.setEnabled(True)
            self.update_window_title()
            self.refresh()

    def move_cursor_down(self):
        if self.table_needs_focusmove:
            index = self.tableView.currentIndex()
            sibling = self.wt.index(index.row()+1)
            if sibling.isValid():
                self.tableView.setCurrentIndex(sibling)
                self.table_needs_focusmove = False

    def update_table(self):
        self.tableView.setModel(self.wt)
        self.table_is_loaded = True
        self.tableView.setVisible(True)

    # fires when enter key is pressed on QTableView widget
    # we catch this to move down the list in our model
    def return_key_activated(self):
        index = self.tableView.currentIndex()
        if self.tableView.isPersistentEditorOpen(index):
            # flag will result in next item being focused when table_changed fires
            self.table_needs_focusmove = True
            editor = self.tableView.indexWidget(index)
            self.tableView.commitData(editor)
            self.tableView.closeEditor(editor, QAbstractItemDelegate.NoHint)
        else:
            self.tableView.edit(index)

    def update_window_title(self):
        title = "Weight Manager"
        if self.file_open:
            fn = self.plan.path.split("/")[-1]
            if self.file_modified:
                fn += "*"
            title = f"{fn} - {title}"
        self.setWindowTitle(title)

    def update_plot(self):
        if not self.canvas:
            self.canvas = Canvas()
            self.centralwidget.layout().addWidget(self.canvas)
            self.centralwidget.layout().setStretch(0, 1)
            self.centralwidget.layout().setStretch(1, 4)
        # It seems expensive to recreate this class and do a complete redraw
        # every time, but WT is extremely dependent on specific details. For
        # example, even one new data point will change the spline fit.
        self.wt.has_new_plottable_data = False
        weightloss = WeightTracker(self.wt, self.plan)
        self.canvas.plot(weightloss)
        self.canvas.draw()

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
