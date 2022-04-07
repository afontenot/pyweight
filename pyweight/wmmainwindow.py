#!/usr/bin/env python3
import os

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
from pyweight.wmhelp import open_help
from pyweight.wmplot import Canvas
from pyweight.wmprefs import Preferences, PreferencesWindow
from pyweight.wmprofile import Profile, ProfileWindow


class MainWindow(QMainWindow):
    """This class controls the UI for the main window.

    This should be the only object in this source file.
    MainWindow contains some of the program logic; mostly
    the bits that are directly activated by UI signals.

    Usually this class will only be instantiated by the
    __main__ module function.

    Init:
        app: a reference to the QApp instance, passed by main
    """

    def __init__(self, app, *args, **kwargs):
        self.app = app
        super().__init__(*args, **kwargs)
        uic.loadUi("pyweight/ui/main.ui", self)

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

        # do the rest of the initialization after app.exec()
        if app is not None:
            QTimer.singleShot(0, self._init_preferences)

    def _init_preferences(self):
        """Initializes preferences - have to defer this after app.exec()"""
        self.prefs = Preferences()
        if self.prefs.open_prev and self.prefs.prev_plan != "":
            if os.path.exists(self.prefs.prev_plan):
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
        """Creates a new *data* file.

        Asks user to choose a new location to save a data file, then save it,
        conditionally on approval and not overwriting a modified existing file.

        Only called by user actions.
        """
        path = QFileDialog.getSaveFileName(self, "New File", filter="CSV Files (*.csv)")
        if path[0] != "":
            if self.check_file_modified() == QMessageBox.Cancel:
                return
            # this is safe because the QFileDialog asks user to overwrite it
            if os.path.exists(path[0]):
                os.unlink(path[0])
            self.plan.path = path[0]
            self.open_data_file()

    def open_file(self):
        """Opens an existing *data* file.

        Asks user to choose a data file (any CSV), and open it, checking
        whether existing file has been modified.

        Only called by user actions.
        Does not do any sanity checking on file contents.
        """
        path = QFileDialog.getOpenFileName(
            self, "Open File", filter="CSV Files (*.csv)"
        )
        if path[0] != "":
            if self.check_file_modified() == QMessageBox.Cancel:
                return
            self.plan.path = path[0]
            self.open_data_file()

    def save_file(self):
        """Save *data* file at user's request.

        Unconditionally saves the CSV, and resets window modification states.
        """
        self.wt.save_csv()
        self.file_modified = False
        self.action_save_file.setEnabled(False)
        self.update_window_title()

    def new_plan(self):
        """Creates a new *plan* file.

        Exactly like `new_file`, but for plans.
        Initiates editing the new file immediately after saving.
        """
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
        """Opens a new plan file at user's request.

        Exactly like `open_file`, but for plans.
        """
        path = QFileDialog.getOpenFileName(
            self, "Open File", filter="Plan Files (*.wmplan)"
        )
        if path[0] != "":
            if self.check_file_modified() == QMessageBox.Cancel:
                return
            self.open_plan_file(path[0])

    def refresh(self):
        """Refreshes user-visible *data*.

        Two bits of data can get out of sync:
          * the dates shown in the table
          * the plot can not have the latest entries

        Mostly this happens when either a user enters new data into
        the WeightTable, which results in this method being called.
        But we also let the user activate this manually.
        """
        self.wt.add_dates()
        self.update_plot()

    def save_graph(self):
        """Saves a static copy of the canvas.

        PNG gets saved via a QPixmap, so it's a 1:1 copy of what the user sees.
        PDF and SVG get saved by the underlying matplotlib instance.

        Only called interactively. Requests the user pick a save path.
        """
        if not self.canvas:
            return
        valid_formats = (
            "PNG Image (.png) (*.png);;"
            "SVG Image (.svg) (*.svg);;"
            "PDF Document (.pdf) (*.pdf)"
        )
        path = QFileDialog.getSaveFileName(self, "Save File", filter=valid_formats)[0]
        if path == "":
            return

        if path.lower().endswith(".png"):
            pix = QPixmap(self.canvas.size())
            self.canvas.render(pix)
            pix.save(path, "PNG")
        elif path.lower().endswith(".pdf"):
            self.canvas.export(path, "pdf")
        elif path.lower().endswith(".svg"):
            self.canvas.export(path, "svg")

    def edit_plan(self, mode=None):
        """Opens the plan editor window.

        This method can be called interactively or automatically,
        as in when a new plan file is created. Saves the plan if
        the dialog is accepted.

        Args:
            mode: "new" indicates that the plan has not yet been saved following
              the initial creation step. This is useful information for both the
              editor window, and the plan saver.
        """
        profile_window = ProfileWindow(self.plan, self.save_plan, mode)
        ret = profile_window.exec()
        if ret == QDialog.Accepted:
            self.save_plan(mode)
        else:
            self.plan.flush()

    def save_plan(self, mode=None):
        """Saves the plan file.

        This method is responsible for changing the units visible in the
        main UI and the canvas; this only happens when the plan file gets
        saved because until then the user is viewing the plan editing modal.
        """
        old_units = self.plan.units
        self.plan.save()
        if self.file_open:
            if self.plan.units != old_units:
                self.wt.set_units(self.plan.units)
            self.update_plot()
        # don't call refresh if there's no data file open yet
        elif mode != "new":
            self.refresh()

    def edit_preferences(self):
        """Opens preferences editing window (user initiated)."""
        prefs_window = PreferencesWindow(self.prefs)
        ret = prefs_window.exec()
        if ret != QDialog.Accepted:
            self.prefs.flush()
            return
        self.prefs.save()
        self.update_plot()

    def show_about(self):
        """Displays information about the program (user initiated)."""
        about_window = AboutWindow(self.app.applicationVersion())
        about_window.exec()

    def show_help(self):
        """Finds docs and displays them in a reasonable per-platform way."""
        open_help()

    def return_key_activated(self):
        """Handles return key firing on the QTableView widget.

        This method provides a little bit of magic not available in QTV
        by default. We make the return key open and close the persistent
        editor automatically, and move down one row when committing data.
        """
        index = self.tableView.currentIndex()
        if self.tableView.isPersistentEditorOpen(index):
            # flag will result in next item being focused when table_changed fires
            self.table_needs_focusmove = True
            editor = self.tableView.indexWidget(index)
            self.tableView.commitData(editor)
            self.tableView.closeEditor(editor, QAbstractItemDelegate.NoHint)
        else:
            self.tableView.edit(index)

    def closeEvent(self, event=None):
        """reimplements from QMainWindow to handle window close"""
        if self.check_file_modified() == QMessageBox.Cancel:
            event.ignore()
            return
        event.accept()

    # Above: Qt slots
    # Below: utilities that can be called by any other method in this class

    def start_pyweight_guide(self):
        """Gives the user a quick and dirty way to get started."""
        mbox = QMessageBox()
        mbox.setWindowTitle("Guide - PyWeight")
        mbox.setText("Welcome to PyWeight!")
        mbox.setInformativeText(
            "If you have not used this program before, this guide will help "
            "you get started. If you already know how to use PyWeight and "
            "have a plan file ready to import, you can click 'No' now.\n\n"
            "To begin tracking your weight with PyWeight, you will first need "
            "to create a plan file. This file stores all of your settings, "
            "making it possible to create backups and share them between "
            "multiple installations of PyWeight.\n\n"
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

    def refresh_actions(self):
        """ensures enabled actions make sense for what the user can actually do"""
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
        """Prompts the user to save modified data files, returns cancelations"""
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
        """Open a data file (non-interactive).

        Attempts to open a data file and load it into a weight table,
        which should get hoisted into the class instance for general use.
        Also attempts to respond sensibly to broken data files.

        Responsible for setting the class status variables for data files.
        Performs initial setup for the tableView widget and MVC.
        """
        try:
            self.wt = WeightTable(self.plan.path, self.plan.units)
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

        # FIXME: could this go somewhere else?
        self.wt.dataChanged.connect(self.table_changed)
        self.wt.rowsInserted.connect(self.maybe_move_cursor_down)

    def open_plan_file(self, path):
        """Opens a plan file (non-interactively).

        Also opens a data file if appropriate given settings and state.
        Creates the class-wide `plan` instance.
        """
        self.plan = Profile(path)
        self.refresh_actions()
        self.prefs.prev_plan = path
        if self.prefs.open_prev and self.plan.path != "":
            self.open_data_file()

    def table_changed(self):
        """Responds to changes on the tableView's underlying model.

        Usually this will happen because the user added a new entry,
        so plotting and cursor movements need to happen here. However,
        this can also be called because of things like automatic date
        additions.
        """
        self.maybe_move_cursor_down()
        if self.table_is_loaded and self.wt.has_new_plottable_data:
            self.action_save_file.setEnabled(True)
            self.refresh()
            if self.prefs.auto_save_data:
                self.save_file()
            else:
                self.file_modified = True
                self.update_window_title()

    def maybe_move_cursor_down(self):
        """Checks whether cursor needs to move down a row, and moves it.

        This method implements the magic behind the <return> key handling.
        Changes on the table view which expect to move the cursor need to
        set `table_needs_focusmove`, because this move can only happen after
        new rows have potentially been added on the underlying model.

        This method is potentially called twice during model updates. This
        is because model data changes and row insertions can trigger cursor
        movements, but we can't guarantee that the sibling will be available
        until the row insertions (if any) fire.
        """
        if self.table_needs_focusmove:
            index = self.tableView.currentIndex()
            sibling = self.wt.index(index.row() + 1)
            if sibling.isValid():
                self.tableView.setCurrentIndex(sibling)
                self.table_needs_focusmove = False

    def update_window_title(self):
        """Keeps the window title up to date with new files and modifications."""
        title = "PyWeight"
        if self.file_open:
            fn = self.plan.path.split("/")[-1]
            if self.file_modified:
                fn += "*"
            title = f"{fn} - {title}"
        self.setWindowTitle(title)

    def update_plot(self):
        """Creates a Canvas widget and plots a new WeightTracker on it."""
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
