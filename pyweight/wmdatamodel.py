from datetime import datetime, timedelta

from PyQt5.QtCore import Qt, QAbstractListModel, QModelIndex


# A simple model for QT's MVC architecture
# Can be initialized with a CSV.
#
# Any method that reimplements a QT method *must* access the internal
# data in reversed order, because this data is presented to the user
# reverse chronologically (but internally, we usually need it in
# increasing order).
#
# This class provides several convenience properties and methods:
#   * units: gets the assumed units of the file
#   * add_dates: fill model with empty dates when needed
#   * end_date: get date of the last *filled* cell
#   * dates: get list of dates for every filled cell
#   * weights: get list of weights for every filled cell
#   * daynumbers: get list of days since start for each filled cell
class WeightTable(QAbstractListModel):
    def __init__(self, parent=None, csvf=None):
        super().__init__(parent)

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

        # initialize the table from a CSV
        # currently we depend on a very specific format, which should
        # be created for the user as needed with a new file
        if csvf:
            header_row = next(csvf)
            self.weight_colname = header_row[1]
            self.weight_data = {}
            for row in csvf:
                date = datetime.strptime(row[0], "%Y/%m/%d").date()
                value = row[1]
                if value != "":
                    value = float(value)
                self._data.append([date, row[0], value])

            self.start_date = self._data[0][0]

    # reimplements QAbstractListModel
    def rowCount(self, parent):
        if parent.isValid():
            return 0
        return len(self._data)

    # reimplements QAbstractListModel
    def data(self, index, role):
        if role in (Qt.DisplayRole, Qt.EditRole):
            # get third column
            val = self._data[index.row()][2]
            # we store high precision internally, but for display round the values
            if val != "":
                val = round(val, 2)
            return str(val)
        return None

    # reimplements QAbstractListModel
    # transparently handles values in the model (which are floats)
    # and empty values (which are "" strings)
    def setData(self, index, value, role):
        if role == Qt.EditRole:
            # handle the case of deleting an entry
            if value != "":
                try:
                    value = float(value)
                    # handle absurd values that might otherwise cause a crash
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

    # reimplements QAbstractListModel; all entries are editable
    def flags(self, index):
        if index.isValid():
            return super().flags(index) | Qt.ItemIsEditable
        return super().flags(index)

    # reimplements QAbstractListModel
    # QT uses "orientations" to indicate whether we are getting row or column
    # headers. If we have horizontal orientation, we automatically know that
    # we have the (single) column header
    def headerData(self, section, orientation, role):
        if role == Qt.DisplayRole:
            if orientation == Qt.Horizontal:
                return self.weight_colname
            # return header from reversed list, second column
            return self._data[section][1]
        return super().headerData(section, orientation, role)

    # make sure model contains dates up till present day
    # and also always contains at least one empty cell at the end
    def add_dates(self):
        today = datetime.now().date()
        days_passed = (today - self._data[-1][0]).days
        # last line is blank: add 0, last line is not blank: add 1
        days_to_add = int((self._data[-1][2]) != "")
        days_to_add = max(days_to_add, days_passed)
        if days_to_add > 0:
            row_count = len(self._data)
            # we have to warn QT which rows are about to be edited
            self.beginInsertRows(QModelIndex(), row_count, row_count + days_to_add - 1)
            last_date_in_model = self._data[-1][0]
            for i in range(days_to_add):
                new_date = last_date_in_model + timedelta(days=i + 1)
                self._data.append([new_date, new_date.strftime("%Y/%m/%d"), ""])
            self.endInsertRows()
            begin_index = self.index(row_count)
            end_index = self.index(row_count + days_to_add - 1)
            self.dataChanged.emit(begin_index, end_index)

    # this is hacky for sure, but we have to trust that the data CSV is sane
    @property
    def units(self):
        if "kg" in self.weight_colname:
            return "kg"
        if "lbs" in self.weight_colname:
            return "lbs"
        return None

    @property
    def end_date(self):
        dates = self.dates
        # when no data has been entered, use the first date as the end date
        if len(dates) != 0:
            return dates[-1]
        return self._data[0][0]

    @property
    def dates(self):
        return [row[0] for row in self._data if row[2] != ""]

    @property
    def weights(self):
        return [row[2] for row in self._data if row[2] != ""]

    @property
    def csvdata(self):
        return [row for row in self._data if row[0] <= self.end_date]

    # get a list containing the distance between each recorded weight and the start
    # date, in days; corresponds to the `weights` list in that empty rows are skipped
    @property
    def daynumbers(self):
        # we offset the day count by 1 because otherwise it would take
        # (cycle + 1) days to reach the first knot
        return [
            1 + (row[0] - self.start_date).days for row in self._data if row[2] != ""
        ]
