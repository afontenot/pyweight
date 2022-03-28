import csv
import datetime
from copy import deepcopy
from io import StringIO

import pytest
from freezegun import freeze_time

from pyweight.wmdatamodel import WeightTable


START_DATE = datetime.date(2000, 1, 1)


class WeightTableBuilder:
    def __init__(self):
        self.__csv = "Date,Mass (lbs)"
        self.__baseweight = "100"
        self.__currentday = START_DATE
        self.parent = None

    def replace_header(self, header):
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
        return WeightTable(csvf)

    # does the minimum fix-up to have a working WT
    def empty_build(self):
        self.add_day()
        return self.build()

    @property
    def csv(self):
        return self.__csv


@pytest.fixture
def wtb():
    return WeightTableBuilder()


# FIXME: add tests for QALM reimplemented functions
# FIXME: test that callbacks fire correctly when add_dates is called


def test_init(wtb):
    wt = wtb.empty_build()
    data = [[START_DATE, "2000/01/01", ""]]
    assert wt._data == data
    assert wt.has_new_plottable_data is False
    assert wt.weight_colname == "Mass (lbs)"
    assert wt.start_date == START_DATE


def test_add_dates_no_change(wtb, qtmodeltester):
    wt = wtb.empty_build()
    qtmodeltester.check(wt)
    before = deepcopy(wt._data)
    with freeze_time(START_DATE):
        wt.add_dates()
        assert before == wt._data


def test_add_dates_final_blank(wtb, qtmodeltester):
    wtb.add_auto_day()
    wt = wtb.build()
    qtmodeltester.check(wt)
    with freeze_time("2000-01-02"):
        wt.add_dates()
        data = [
            [datetime.date(2000, 1, 1), "2000/01/01", 100],
            [datetime.date(2000, 1, 2), "2000/01/02", ""],
        ]
        assert wt._data == data


def test_add_dates_missing(wtb, qtmodeltester):
    wt = wtb.empty_build()
    qtmodeltester.check(wt)
    with freeze_time("2000-01-03"):
        wt.add_dates()
        data = [
            [datetime.date(2000, 1, 1), "2000/01/01", ""],
            [datetime.date(2000, 1, 2), "2000/01/02", ""],
            [datetime.date(2000, 1, 3), "2000/01/03", ""],
        ]
        assert wt._data == data


def test_units_lbs(wtb):
    wt = wtb.empty_build()
    assert wt.units == "lbs"


def test_units_kg(wtb):
    wtb.replace_header("Date,Mass (kg)")
    wt = wtb.empty_build()
    assert wt.units == "kg"


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


def test_daynumbers(wtb):
    wtb.add_auto_day()
    wtb.add_day()
    wtb.add_auto_day()
    wt = wtb.build()
    assert wt.daynumbers == [1, 3]
