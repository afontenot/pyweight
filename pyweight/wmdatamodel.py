import csv
import os
from datetime import datetime, timedelta
from tempfile import mkstemp

from PyQt5.QtCore import Qt, QAbstractListModel, QModelIndex

from pyweight.wmutils import kg_to_lbs, lbs_to_kg


class WeightTable(QAbstractListModel):
    """A model for QT's MVC architecture.

    A WeightTable contains a set of weight data, and tooling for creating,
    saving, and manipulating this data in a sensible way. For statistical
    methods for working with this data, see WeightTracker in wmbodymodel.py.

    Users of WeightTable (other than MVC members) are generally expected
    to interact with the data through the `dates`, `daynumbers`, and `weights`
    family of functions. These provide a linear, time-ordered view of the
    values in the list model, and are guaranteed to coincide. Each omits blank
    days, and `daynumbers` provides a one-based incrementing day counter that
    gives the true day total since the start of the dataset for each day.

    Since the 1-1 correspondence is maintained between dates and daynumbers,
    a generally useful approach for working with the data is to treat the
    day numbers and weights as x-y data, respectively, and use the true dates
    for display.

    Since PyWeight's underlying data are always stored in metric units, this
    class hides this implementation detail. Data are presented in the instance
    owner's preferred units.

    Init:
        csvpath: initializes the WT with a CSV file

    Attributes:
      * end_date: get date of the last *filled* cell
      * dates: get list of dates for every filled cell
      * daynumbers: get list of days since start for each filled cell
      * has_new_plottable_data: indicate whether changes to data need plotting
      * weights: get list of weights for every filled cell
      * weight_colname: display version of the weight unit

    Important Methods:
      * add_dates(): fill model with empty dates when needed
      * create_csv(): make a new blank csv at a path
      * save_csv(): saves stored data to the backing file
      * set_units(): tell WT which units to present the data in to viewers
    """

    def __init__(self, csvpath, units):
        super().__init__()

        # Internally, the data has three columns:
        #   [datetime, str_date, value]
        # This is a *list* model, however; the "data" is just the last column
        # The second column is used for the row headers, and keeping track of
        #   the date is useful internally
        self._data = []

        # We use this to determine when we need to replot. Adding new (blank)
        # dates also triggers the dataChanged() slot, but we don't want to
        # replot when that happens.
        self.has_new_plottable_data = False

        # If the user prefers imperial units to metric, this class pretends
        # that all the data is imperial, even though we only save metric data
        # to the underlying CSV.
        self.set_units(units)

        # If the CSV does not already exist, it is automatically created
        if not os.path.exists(csvpath):
            self.create_csv(csvpath)

        # initialize the table from a CSV
        # currently we depend on a very specific format, which should
        # be created for the user as needed with `create_csv()`
        with open(csvpath, encoding="utf-8", newline="") as f:
            csvr = csv.reader(f)
            next(csvr)  # skip header
            for row in csvr:
                date = datetime.strptime(row[0], "%Y/%m/%d").date()
                value = row[1]
                if value != "":
                    value = float(value)
                self._data.append([date, row[0], value])

        self.start_date = self._data[0][0]
        self.csvpath = csvpath

    def set_units(self, units):
        """Changes the units the model's public data is in.

        Sends a full update of the model to force a view refresh.

        Args:
            units: "imperial" or "metric" (default)
        """
        self.imperial = units == "imperial"
        self.unit = "lbs" if self.imperial else "kg"
        self.weight_colname = f"Weight ({self.unit})"
        self.dataChanged.emit(self.index(0), self.index(len(self._data)))

    def rowCount(self, parent):
        """Reimplements QAbstractListModel - count rows in model"""
        if parent.isValid():
            return 0
        return len(self._data)

    #
    def data(self, index, role):
        """Reimplements QAbstractListModel - read data from model"""
        if role in (Qt.DisplayRole, Qt.EditRole):
            # the third column contains the public data
            val = self._data[index.row()][2]
            # conversion to imperial (if needed) is here
            # we read data rarely enough that cacheing this is probably not worth it
            if val != "":
                if self.imperial:
                    val = kg_to_lbs(val)
                # we store high precision internally, but for display round the values
                val = round(val, 2)
            return str(val)
        return None

    def setData(self, index, value, role):
        """Reimplements QAbstractListModel - set data in model

        Transparently handles values in the model (which are floats)
        and empty values (which are "" strings).
        """
        if role == Qt.EditRole:
            # handle the case of deleting an entry
            if value != "":
                try:
                    value = float(value)
                    if self.imperial:
                        value = lbs_to_kg(value)
                    # handle absurd values that might otherwise cause a crash
                    # FIXME: maybe Qt views have validation?
                    if value > 2000 or value <= 0:
                        return False
                except ValueError:
                    return False
            # check that data has actually changed before emitting an event
            oldvalue = self._data[index.row()][2]
            if oldvalue != value:
                self._data[index.row()][2] = value
                self.has_new_plottable_data = True
                self.dataChanged.emit(index, index)
            return True
        return super().setData(index, value, role)

    def flags(self, index):
        """Reimplement QAbstractListModel - mark editable entries (all)."""
        if index.isValid():
            return super().flags(index) | Qt.ItemIsEditable
        return super().flags(index)

    def headerData(self, section, orientation, role):
        """Reimplements QAbstractListModel - get data in list header.

        Args:
            orientation: indicates whether a row or column header is wanted
        """
        if role == Qt.DisplayRole:
            # If we have horizontal orientation, we automatically know that
            # we have the column header, because there's only one of them.
            # Otherwise, return our "date" column for display.
            if orientation == Qt.Horizontal:
                return self.weight_colname
            return self._data[section][1]
        return super().headerData(section, orientation, role)

    def add_dates(self):
        """Ensures model always contains dates up to present day.

        Also checks that model contains at least one empty cell after last entry.
        """
        today = datetime.now().date()
        days_passed = (today - self._data[-1][0]).days
        # last line is blank: add 0, last line is not blank: add 1
        days_to_add = int((self._data[-1][2]) != "")
        days_to_add = max(days_to_add, days_passed)
        if days_to_add > 0:
            row_count = len(self._data)
            # we have to warn views which rows are about to be edited
            self.beginInsertRows(QModelIndex(), row_count, row_count + days_to_add - 1)
            last_date_in_model = self._data[-1][0]
            for i in range(days_to_add):
                new_date = last_date_in_model + timedelta(days=i + 1)
                self._data.append([new_date, new_date.strftime("%Y/%m/%d"), ""])
            self.endInsertRows()

    @property
    def end_date(self):
        """Returns the last non-blank date in the model."""
        dates = self.dates
        # when no data has been entered, use the first date as the end date
        if len(dates) != 0:
            return dates[-1]
        return self._data[0][0]

    @property
    def dates(self):
        """Get a list of non-blank dates in chrono order."""
        return [row[0] for row in self._data if row[2] != ""]

    @property
    def weights(self):
        """Returns a list of weights (in preferred units) in chrono order."""
        if self.imperial:
            return [kg_to_lbs(row[2]) for row in self._data if row[2] != ""]
        return [row[2] for row in self._data if row[2] != ""]

    @property
    def csvdata(self):
        """Returns the full data, up to the last day with a weight entry.

        FIXME: this should probably be a private method.
        """
        return [row for row in self._data if row[0] <= self.end_date]

    @property
    def daynumbers(self):
        """Returns a list with the number of days for each entry since the start.

        The first day is 1, instead of 0, because a knot happens every `n` days,
        and if the day count starts at 0 users would have to wait n+1 days to hit
        the first knot.

        The day numbers should not be used for anything except for a linear
        representation of time deltas, as when interpolating, determining advice
        intervals, etc.
        """
        return [
            1 + (row[0] - self.start_date).days for row in self._data if row[2] != ""
        ]

    def create_csv(self, csvpath):
        """Make a new blank CSV data file, from a template.

        FIXME: could be a static method?"""
        with open(csvpath, "w", encoding="utf-8", newline="") as f:
            csvw = csv.writer(f)
            csvw.writerow(["Date", "Weight (kg)"])
            today = datetime.now()
            csvw.writerow([today.strftime("%Y/%m/%d"), ""])

    def save_csv(self):
        """Save the CSV data file associated with the data model.

        Creates a temporary file and moves it on top of the old one,
        in an attempt to be mostly atomic in case of a crash.
        """
        dpath, fname = os.path.split(self.csvpath)
        tmpfd, tmppath = mkstemp(prefix=f"{fname}.", dir=dpath, text=True)
        # create file object to own the open fd; automatically closes for us
        with os.fdopen(tmpfd, "w", encoding="utf-8", newline="") as f:
            csvw = csv.writer(f)
            csvw.writerow(["Date", "Weight (kg)"])
            for row in self._data:
                csvw.writerow(row[1:])
        os.rename(tmppath, self.csvpath)
