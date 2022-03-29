#!/usr/bin/env python3
import csv
from datetime import datetime
from os.path import exists

from PyQt5 import uic
from PyQt5.QtCore import QTimer
from PyQt5.QtGui import QPixmap, QKeySequence
from PyQt5.QtWidgets import (
    QDialog,
    QFileDialog,
    QMainWindow,
    QMessageBox,
    QShortcut,
    QAbstractItemDelegate,
)

from pyweight.wmabout import AboutWindow
from pyweight.wmbodymodel import WeightTracker
from pyweight.wmdatamodel import WeightTable
from pyweight.wmplot import Canvas
from pyweight.wmprefs import Preferences, PreferencesWindow
from pyweight.wmprofile import Profile, ProfileWindow


# This file contains the code for initialization and the main window class.


class MainWindow(QMainWindow):
    def __init__(self, app, *args, **kwargs):
        self.app = app
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
        self.wt = None

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

        # timer will fire immediately after app.exec()
        QTimer.singleShot(0, self._init_preferences)

    # initialize preferences - have to defer this after app.exec()
    def _init_preferences(self):
        self.prefs = Preferences()
        if self.prefs.open_prev and self.prefs.prev_plan != "":
            if exists(self.prefs.prev_plan):
                self.open_plan_file(self.prefs.prev_plan)
            else:
                mbox = QMessageBox()
                mbox.setIcon(QMessageBox.Warning)
                mbox.setText("Previous plan file could not be opened.")
                mbox.exec()
        elif self.prefs.prev_plan == "":
            # give the user some help if they've never used pyweight before
            self.start_pyweight_guide()

    # Below here:
    # Slots for main window actions

    def new_file(self):
        path = QFileDialog.getSaveFileName(self, "New File", filter="CSV Files (*.csv)")
        if path[0] != "":
            if self.check_file_modified() == QMessageBox.Cancel:
                return
            with open(path[0], "w", encoding="utf-8", newline="") as csvfile:
                writer = csv.writer(csvfile)
                # FIXME: moving CSV writing code to wmdata
                writer.writerow(["Date", "Weight (kg)"])
                today = datetime.now()
                writer.writerow([today.strftime("%Y/%m/%d"), ""])
            self.plan.path = path[0]
            self.open_data_file()

    def open_file(self):
        path = QFileDialog.getOpenFileName(
            self, "Open File", filter="CSV Files (*.csv)"
        )
        if path[0] != "":
            if self.check_file_modified() == QMessageBox.Cancel:
                return
            self.plan.path = path[0]
            self.open_data_file()

    def save_file(self):
        with open(self.plan.path, "w", encoding="utf-8", newline="") as csvfile:
            csvw = csv.writer(csvfile)
            self.wt.save_csv(csvw)
        self.file_modified = False
        self.action_save_file.setEnabled(False)
        self.update_window_title()

    def new_plan(self):
        path = QFileDialog.getSaveFileName(
            self, "New File", filter="Plan Files (*.wmplan)"
        )
        if path[0] != "":
            if self.check_file_modified() == QMessageBox.Cancel:
                return
            self.file_open = False
            self.open_plan_file(path[0])
            self.edit_plan(mode="new")

    def open_plan(self):
        path = QFileDialog.getOpenFileName(
            self, "Open File", filter="Plan Files (*.wmplan)"
        )
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
        path = QFileDialog.getSaveFileName(
            self, "Save File", filter="PNG Files (*.png)"
        )
        if path[0] != "":
            pix = QPixmap(self.canvas.size())
            self.canvas.render(pix)
            pix.save(path[0], "PNG")

    def edit_plan(self, mode=None):
        profile_window = ProfileWindow(self.plan, self.save_plan, mode)
        ret = profile_window.exec()
        if ret == QDialog.Accepted:
            self.save_plan()
        else:
            self.plan.flush()

    def save_plan(self):
        old_units = self.plan.units
        self.plan.save()
        if self.file_open:
            if self.plan.units != old_units:
                self.open_data_file()
            self.update_plot()
        else:
            self.refresh()

    def edit_preferences(self):
        prefs_window = PreferencesWindow(self.prefs)
        ret = prefs_window.exec()
        if ret != QDialog.Accepted:
            self.prefs.flush()
            return
        self.prefs.save()
        self.update_plot()

    def show_about(self):
        about_window = AboutWindow(self.app.applicationVersion())
        about_window.exec()

    def show_help(self):
        mbox = QMessageBox()
        mbox.setIcon(QMessageBox.Information)
        mbox.setText("Not yet implemented.")
        mbox.setInformativeText("See Github for usage instructions.")
        mbox.setStandardButtons(QMessageBox.Ok)
        mbox.setDefaultButton(QMessageBox.Ok)
        mbox.exec()

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

    # reimplementation from QMainWindow to handle window close
    def closeEvent(self, event=None):
        if self.check_file_modified() == QMessageBox.Cancel:
            event.ignore()
            return
        event.accept()

    # Above: Qt slots
    # Below: utilities that can be called by any other method in this class

    def start_pyweight_guide(self):
        mbox = QMessageBox()
        mbox.setWindowTitle("Guide - Weight Manager")
        mbox.setText("Welcome to pyweight!")
        mbox.setInformativeText(
            "If you have not used this program before, this guide will help "
            "you get started. If you already know how to use pyweight and "
            "have a plan file ready to import, you can click 'No' now.\n\n"
            "To begin tracking your weight with pyweight, you will first need "
            "to create a plan file. This file stores all of your settings, "
            "making it possible to create backups and share them between "
            "multiple installations of pyweight.\n\n"
            "You will also need to create a data file. This is a simple, "
            "human-readable CSV file that contains your recorded weight for "
            "each day you use the program.\n\n"
            "In the future, you can create these files manually by using the "
            "File menu.\n\n"
            "Would you like to create these files now?"
        )
        mbox.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        mbox.setDefaultButton(QMessageBox.Yes)
        ret = mbox.exec()
        if ret == QMessageBox.Yes:
            self.new_plan()
            if self.prefs.prev_plan != "":
                self.new_file()

    # make sure enabled actions make sense for what the user can actually do
    def refresh_actions(self):
        plan_active_actions = (
            self.action_new_file,
            self.action_open_file,
            self.action_save_file,
            self.action_plan_settings,
        )
        file_open_actions = (self.action_refresh, self.action_export)
        for action in plan_active_actions:
            action.setEnabled(self.plan is not None)
        for action in file_open_actions:
            action.setEnabled(self.file_open)

    def check_file_modified(self):
        if self.file_modified:
            mbox = QMessageBox()
            mbox.setIcon(QMessageBox.Warning)
            mbox.setText("Your log file has been modified.")
            mbox.setInformativeText("Do you want to save your changes or discard them?")
            mbox.setStandardButtons(
                QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel
            )
            mbox.setDefaultButton(QMessageBox.Save)
            resp = mbox.exec()
            if resp == QMessageBox.Save:
                self.save_file()
            return resp
        return None

    def open_data_file(self):
        try:
            with open(self.plan.path, encoding="utf-8", newline="") as csvfile:
                csvr = csv.reader(csvfile)
                self.wt = WeightTable(csvr, self.plan.units)
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

        self.tableView.setModel(self.wt)
        self.table_is_loaded = True
        self.tableView.setVisible(True)

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
            sibling = self.wt.index(index.row() + 1)
            if sibling.isValid():
                self.tableView.setCurrentIndex(sibling)
                self.table_needs_focusmove = False

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

    # Above: utility methods
