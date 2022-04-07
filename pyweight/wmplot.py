import sys
from datetime import timedelta
from dateutil import rrule
from matplotlib import dates
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg
from matplotlib.figure import Figure


class Canvas(FigureCanvasQTAgg):
    """A wrapper class for matplotlib's Canvas for Qt.

    The class provides convenient defaults as static attributes.
    Mostly we just store a figure and plot WeightTracker objects to it.
    """

    locator = dates.AutoDateLocator(interval_multiples=False)
    locator.intervald[rrule.HOURLY] = [24]
    locator.intervald[rrule.MINUTELY] = [24 * 60]
    locator.intervald[rrule.SECONDLY] = [24 * 60 * 60]
    date_fmts = ["%b %Y", "%b %-d", "%b %-d", "%b %-d", "%b %-d", "%b %-d"]
    if sys.platform == "win32":
        date_fmts = [x.replace("-", "#") for x in date_fmts]
    offset_fmts = ["", "%Y", "%Y", "%Y", "%Y", "%Y"]
    formatter = dates.ConciseDateFormatter(
        locator, formats=date_fmts, offset_formats=offset_fmts
    )

    def __init__(self, dpi=96):
        self.fig = Figure(dpi=dpi)
        super().__init__(self.fig)

    def clear(self):
        self.fig.clear()
        self.axes = self.fig.add_subplot(111)

    def plot(self, wtracker):
        """Plots the WeightTracker instance to our stored axes.

        Args:
            wtracker: the WeightTracker instance to plot (see wmbodymodel.py)
        """
        self.clear()

        # plot using the original independent variable, the date, to get nicer output
        self.axes.plot(
            wtracker.data.dates, wtracker.data.weights, "o", c="xkcd:burgundy", ms=4
        )

        # if interpolation is available, plot it and provide advice
        info = ""
        if wtracker.interpolation:
            self.axes.plot(
                wtracker.data.dates,
                wtracker.interpolation(wtracker.data.daynumbers),
                c="xkcd:dark navy blue",
            )

            # Every `cycle` days, print out instructions
            if wtracker.data.daynumbers[-1] % wtracker.settings.cycle == 0:
                if wtracker.adjustment != 0:
                    adjword = "increasing" if wtracker.adjustment > 0 else "decreasing"
                    info = f"Consider {adjword} intake by {abs(wtracker.adjustment)} calories per day."
            else:
                days_to_go = wtracker.settings.cycle - (
                    wtracker.data.daynumbers[-1] % wtracker.settings.cycle
                )
                plural = "s" if days_to_go > 1 else ""
                info = f"Continue current intake for next {days_to_go} day{plural}."
                if wtracker.settings.always_show_adj:
                    info += f" Adjustment value is {wtracker.adjustment:+}."

        # from here to the end of the method it's just formatting stuff
        # found by trial and error, mostly
        self.axes.set_xlabel("Date", labelpad=15)
        self.axes.set_ylabel(wtracker.data.weight_colname, labelpad=15)

        # pick a reasonable date range if we haven't seen enough data
        if (wtracker.data.end_date - wtracker.data.start_date).days < 14:
            self.axes.set_xlim(
                left=wtracker.data.start_date + timedelta(days=-1),
                right=wtracker.data.start_date + timedelta(days=15),
            )
        if len(wtracker.data.dates) == 0:
            self.axes.set_ylim(bottom=90, top=200)

        self.fig.suptitle("Weight Tracking")
        self.axes.set_title(info, fontsize=10, pad=20)

        self.axes.xaxis.set_major_locator(self.locator)
        self.axes.xaxis.set_major_formatter(self.formatter)
        self.axes.grid(True)

    def export(self, path, filetype):
        self.fig.savefig(path, format=filetype)
