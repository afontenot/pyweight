import csv
import datetime
from copy import deepcopy
from io import StringIO

import pytest
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QAbstractItemView
from freezegun import freeze_time

from pyweight.wmdatamodel import WeightTable
from pyweight.wmutils import kg_to_lbs


START_DATE = datetime.date(2000, 1, 1)


class WeightTableBuilder:
    def __init__(self):
        self.__csv = "Date,Weight (kg)"
        self.__baseweight = "100"
        self.__currentday = START_DATE
        self.parent = None
        self.units = "metric"

    def replace_units(self, units):
        self.units = units
        unit = "lbs" if self.units == "imperial" else "kg"
        header = f"Weight ({unit})"
        if "\n" not in self.__csv:
            self.__csv = header
        else:
            self.__csv = header + "\n" + "\n".join(self.__csv.split("\n")[1:])

    def add_day(self, weight=""):
        date = datetime.datetime.strftime(self.__currentday, "%Y/%m/%d")
        self.__csv += f"\n{date},{weight}"
        self.__currentday += datetime.timedelta(days=1)

    def add_auto_day(self):
        date = datetime.datetime.strftime(self.__currentday, "%Y/%m/%d")
        self.__csv += f"\n{date},{self.__baseweight}"
        self.__currentday += datetime.timedelta(days=1)

    def build(self):
        csvf = csv.reader(StringIO(self.__csv))
        return WeightTable(csvf, self.units)

    # does the minimum fix-up to have a working WT
    def empty_build(self):
        self.add_day()
        return self.build()


class SimpleView(QAbstractItemView):
    def __init__(self):
        super().__init__()
        self.events = []

    def setModel(self, model):
        model.rowsAboutToBeInserted.connect(self.rowsAboutToBeInserted)
        super().setModel(model)

    def dataChanged(self, index_a, index_b, roles=None):
        self.events.append(("dataChanged", index_a.row(), index_b.row()))

    def rowsAboutToBeInserted(self, parent, start, end):
        self.events.append(("rowsAboutToBeInserted", start, end))

    def rowsInserted(self, parent, start, end):
        self.events.append(("rowsInserted", start, end))


@pytest.fixture
def wtb(qtbot):
    return WeightTableBuilder()


@pytest.fixture
def view(qtbot):
    return SimpleView()


def test_init(wtb):
    wt = wtb.empty_build()
    data = [[START_DATE, "2000/01/01", ""]]
    assert wt._data == data
    assert wt.has_new_plottable_data is False
    assert wt.start_date == START_DATE


def test_data(wtb):
    wtb.add_day("101.111")
    wtb.add_day()
    wtb.add_day("101.111")
    wt = wtb.build()
    data = [wt.data(wt.index(row, 0), Qt.DisplayRole) for row in range(3)]
    assert data == ["101.11", "", "101.11"]


def test_set_data(wtb, view, qtmodeltester):
    wtb.add_day("101.11")
    wtb.add_day("101.11")
    wt = wtb.build()
    qtmodeltester.check(wt)
    view.setModel(wt)
    wt.setData(wt.index(1, 0), "101.12", Qt.EditRole)
    data = [
        [datetime.date(2000, 1, 1), "2000/01/01", 101.11],
        [datetime.date(2000, 1, 2), "2000/01/02", 101.12],
    ]
    assert wt._data == data
    events = [("dataChanged", 1, 1)]
    assert view.events == events


def test_header_data(wtb):
    wtb.add_auto_day()
    wt = wtb.build()
    assert wt.headerData(0, Qt.Horizontal, Qt.DisplayRole) == "Weight (kg)"
    assert wt.headerData(0, Qt.Vertical, Qt.DisplayRole) == "2000/01/01"


def test_add_dates_no_change(wtb, view, qtmodeltester):
    wt = wtb.empty_build()
    qtmodeltester.check(wt)
    view.setModel(wt)
    before = deepcopy(wt._data)
    with freeze_time(START_DATE):
        wt.add_dates()
    assert before == wt._data
    assert view.events == []


def test_add_dates_final_blank(wtb, view, qtmodeltester):
    wtb.add_auto_day()
    wt = wtb.build()
    qtmodeltester.check(wt)
    view.setModel(wt)
    with freeze_time("2000-01-01"):
        wt.add_dates()
    data = [
        [datetime.date(2000, 1, 1), "2000/01/01", 100],
        [datetime.date(2000, 1, 2), "2000/01/02", ""],
    ]
    assert wt._data == data
    events = [
        ("rowsAboutToBeInserted", 1, 1),
        ("rowsInserted", 1, 1),
    ]
    assert view.events == events


def test_add_dates_missing(wtb, view, qtmodeltester):
    wt = wtb.empty_build()
    qtmodeltester.check(wt)
    view.setModel(wt)
    with freeze_time("2000-01-03"):
        wt.add_dates()
    data = [
        [datetime.date(2000, 1, 1), "2000/01/01", ""],
        [datetime.date(2000, 1, 2), "2000/01/02", ""],
        [datetime.date(2000, 1, 3), "2000/01/03", ""],
    ]
    assert wt._data == data
    events = [
        ("rowsAboutToBeInserted", 1, 2),
        ("rowsInserted", 1, 2),
    ]
    assert view.events == events


def test_end_date_empty(wtb):
    wt = wtb.empty_build()
    assert wt.end_date == START_DATE


def test_end_date(wtb):
    wtb.add_auto_day()
    wtb.add_day()
    wt = wtb.build()
    assert wt.end_date == START_DATE


def test_dates(wtb):
    wtb.add_auto_day()
    wtb.add_day()
    wtb.add_auto_day()
    wt = wtb.build()
    dates = [
        datetime.date(2000, 1, 1),
        datetime.date(2000, 1, 3),
    ]
    assert wt.dates == dates


def test_weights(wtb):
    wtb.add_auto_day()
    wtb.add_day()
    wtb.add_auto_day()
    wt = wtb.build()
    weights = [100, 100]
    assert wt.weights == weights


def test_weights_imperial(wtb):
    wtb.replace_units("imperial")
    wtb.add_auto_day()
    wtb.add_day()
    wtb.add_auto_day()
    wt = wtb.build()
    weights = [kg_to_lbs(100), kg_to_lbs(100)]
    assert wt.weights == weights


def test_csvdata_empty(wtb):
    wt = wtb.empty_build()
    # empty csv should still have first row
    csvdata = [[datetime.date(2000, 1, 1), "2000/01/01", ""]]
    assert wt.csvdata == csvdata


def test_csvdata(wtb):
    wtb.add_auto_day()
    wtb.add_day()
    wtb.add_auto_day()
    wtb.add_day()
    wt = wtb.build()
    csvdata = [
        [datetime.date(2000, 1, 1), "2000/01/01", 100],
        [datetime.date(2000, 1, 2), "2000/01/02", ""],
        [datetime.date(2000, 1, 3), "2000/01/03", 100],
    ]
    assert wt.csvdata == csvdata


def test_csvdata_imperial(wtb):
    wtb.replace_units("imperial")
    wtb.add_auto_day()
    wtb.add_day()
    wtb.add_auto_day()
    wtb.add_day()
    wt = wtb.build()
    csvdata = [
        [datetime.date(2000, 1, 1), "2000/01/01", 100],
        [datetime.date(2000, 1, 2), "2000/01/02", ""],
        [datetime.date(2000, 1, 3), "2000/01/03", 100],
    ]
    assert wt.csvdata == csvdata


def test_daynumbers(wtb):
    wtb.add_auto_day()
    wtb.add_day()
    wtb.add_auto_day()
    wt = wtb.build()
    assert wt.daynumbers == [1, 3]
