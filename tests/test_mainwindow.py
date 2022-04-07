import csv
from datetime import datetime

import pytest
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QDialog, QMessageBox

import pyweight.wmmainwindow
from pyweight.wmdatamodel import WeightTable
from pyweight.wmmainwindow import MainWindow
from pyweight.wmplot import Canvas
from pyweight.wmprofile import Profile
from pyweight.wmsettings import WMSettings
from pyweight.wmutils import lbs_to_kg


class FakePrefs(WMSettings):
    defaults = {
        "open_prev": True,
        "auto_save_data": False,
        "prev_plan": "",
        "language": "English",
    }
    conversions = {"open_prev": bool, "auto_save_data": bool}

    def __init__(self, tmp_path):
        path = str(tmp_path / "prefs.ini")
        super().__init__(self.defaults, self.conversions, path)


@pytest.fixture
def datafile(tmp_path):
    path = str(tmp_path / "data.csv")
    with open(path, "w", encoding="utf-8", newline="") as f:
        csvw = csv.writer(f)
        csvw.writerow(["Date", "Weight (kg)"])
        today = datetime.now()
        csvw.writerow([today.strftime("%Y/%m/%d"), ""])
    return path


@pytest.fixture
def mw(qtbot, tmp_path, datafile):
    window = MainWindow(app=None)
    window.prefs = FakePrefs(tmp_path)
    window.open_plan_file(str(tmp_path / "plan.wmplan"))
    window.plan.path = datafile
    window.open_data_file()
    return window


def test_init_window(qtbot, mw):
    mw.show()
    qtbot.addWidget(mw)
    assert mw.windowTitle() == "data.csv - PyWeight"
    assert mw.file_open
    assert mw.table_is_loaded
    assert isinstance(mw.plan, Profile)
    assert isinstance(mw.canvas, Canvas)
    assert isinstance(mw.wt, WeightTable)


def test_edit_handling(qtbot, mw, monkeypatch):
    mw.show()
    qtbot.addWidget(mw)
    rect = mw.tableView.visualRect(mw.wt.index(0))
    qtbot.mouseClick(mw.tableView.viewport(), Qt.LeftButton, pos=rect.center())
    qtbot.keyClicks(mw.tableView, " ")
    editor_widget = mw.tableView.indexWidget(mw.wt.index(0))
    qtbot.keyClicks(editor_widget, "100.0")
    # no way to test keyboard shortcuts directly
    # https://github.com/pytest-dev/pytest-qt/issues/254
    mw.return_key_activated()
    monkeypatch.setattr(
        pyweight.wmmainwindow.QMessageBox, "exec", lambda *args: QMessageBox.Discard
    )
    assert mw.windowTitle() == "data.csv* - PyWeight"
    # (fake) return key should move cursor down a line
    assert mw.tableView.currentIndex().row() == 1


def test_edit_with_autosave(qtbot, mw, monkeypatch):
    mw.prefs.auto_save_data = True
    mw.show()
    qtbot.addWidget(mw)
    rect = mw.tableView.visualRect(mw.wt.index(0))
    qtbot.mouseClick(mw.tableView.viewport(), Qt.LeftButton, pos=rect.center())
    qtbot.keyClicks(mw.tableView, " ")
    editor_widget = mw.tableView.indexWidget(mw.wt.index(0))
    qtbot.keyClicks(editor_widget, "100.0")
    mw.return_key_activated()
    monkeypatch.setattr(
        pyweight.wmmainwindow.QMessageBox, "exec", lambda *args: QMessageBox.Discard
    )
    assert not mw.file_modified
    assert mw.windowTitle() == "data.csv - PyWeight"


def test_closing_safely(qtbot, mw, monkeypatch):
    mw.show()
    qtbot.addWidget(mw)
    # program should ask what to do with unsaved changes; patch to cancel
    monkeypatch.setattr(
        pyweight.wmmainwindow.QMessageBox, "exec", lambda *args: QMessageBox.Cancel
    )
    rect = mw.tableView.visualRect(mw.wt.index(0))
    qtbot.mouseClick(mw.tableView.viewport(), Qt.LeftButton, pos=rect.center())
    qtbot.keyClicks(mw.tableView, " ")
    editor_widget = mw.tableView.indexWidget(mw.wt.index(0))
    qtbot.keyClicks(editor_widget, "100.0")
    mw.return_key_activated()
    res = mw.close()
    monkeypatch.setattr(
        pyweight.wmmainwindow.QMessageBox, "exec", lambda *args: QMessageBox.Discard
    )
    assert not res


def test_editing_profile(qtbot, mw, monkeypatch):
    class MockProfileWindow:
        def __init__(self, plan, *args):
            self.plan = plan

        def exec(self):
            self.plan.wcrate.inflight(-0.751)
            return QDialog.Accepted

    mw.show()
    qtbot.addWidget(mw)
    monkeypatch.setattr(pyweight.wmmainwindow, "ProfileWindow", MockProfileWindow)
    qtbot.mouseClick(mw.menuSettings, Qt.LeftButton)
    action_loc = mw.menuSettings.actionGeometry(mw.action_plan_settings)
    qtbot.mouseClick(mw.menuSettings, Qt.LeftButton, pos=action_loc.center())
    assert mw.plan.wcrate == -0.751


def test_rejecting_profile(qtbot, mw, monkeypatch):
    class MockProfileWindow:
        def __init__(self, plan, *args):
            self.plan = plan

        def exec(self):
            self.plan.wcrate.inflight(-0.751)
            return QDialog.Rejected

    mw.show()
    qtbot.addWidget(mw)
    prev_wcrate = mw.plan.wcrate
    monkeypatch.setattr(pyweight.wmmainwindow, "ProfileWindow", MockProfileWindow)
    qtbot.mouseClick(mw.menuSettings, Qt.LeftButton)
    action_loc = mw.menuSettings.actionGeometry(mw.action_plan_settings)
    qtbot.mouseClick(mw.menuSettings, Qt.LeftButton, pos=action_loc.center())
    assert mw.plan.wcrate == prev_wcrate


def test_entering_data(qtbot, mw, monkeypatch):
    mw.show()
    qtbot.addWidget(mw)
    rect = mw.tableView.visualRect(mw.wt.index(0))
    qtbot.mouseClick(mw.tableView.viewport(), Qt.LeftButton, pos=rect.center())
    qtbot.keyClicks(mw.tableView, " ")
    editor_widget = mw.tableView.indexWidget(mw.wt.index(0))
    qtbot.keyClicks(editor_widget, "100.0")
    mw.return_key_activated()
    monkeypatch.setattr(
        pyweight.wmmainwindow.QMessageBox, "exec", lambda *args: QMessageBox.Discard
    )
    assert mw.wt._data[0][2] == lbs_to_kg(100)


def test_saving_data(qtbot, mw, monkeypatch):
    mw.show()
    qtbot.addWidget(mw)
    rect = mw.tableView.visualRect(mw.wt.index(0))
    qtbot.mouseClick(mw.tableView.viewport(), Qt.LeftButton, pos=rect.center())
    qtbot.keyClicks(mw.tableView, " ")
    editor_widget = mw.tableView.indexWidget(mw.wt.index(0))
    qtbot.keyClicks(editor_widget, "100.0")
    mw.return_key_activated()
    mw.save_file()
    mw.open_data_file()
    assert mw.wt._data[0][2] == lbs_to_kg(100)


def test_converting_units(qtbot, mw, monkeypatch):
    mw.show()
    qtbot.addWidget(mw)
    rect = mw.tableView.visualRect(mw.wt.index(0))
    qtbot.mouseClick(mw.tableView.viewport(), Qt.LeftButton, pos=rect.center())
    qtbot.keyClicks(mw.tableView, " ")
    editor_widget = mw.tableView.indexWidget(mw.wt.index(0))
    qtbot.keyClicks(editor_widget, "100.0")
    mw.return_key_activated()
    monkeypatch.setattr(
        pyweight.wmmainwindow.QMessageBox, "exec", lambda *args: QMessageBox.Discard
    )
    assert mw.wt.weights[0] == 100.0

    class MockProfileWindow:
        def __init__(self, plan, *args):
            self.plan = plan

        def exec(self):
            self.plan.units.inflight("metric")
            return QDialog.Accepted

    monkeypatch.setattr(pyweight.wmmainwindow, "ProfileWindow", MockProfileWindow)
    mw.edit_plan()

    assert mw.wt.weights[0] == lbs_to_kg(100)
    assert not mw.wt.imperial
    assert mw.wt.unit == "kg"
    assert mw.wt.weight_colname == "Weight (kg)"

    mw.save_file()
    mw.open_data_file()
    assert mw.wt.weights[0] == lbs_to_kg(100)
    assert mw.wt._data[0][2] == lbs_to_kg(100)
