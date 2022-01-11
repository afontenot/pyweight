import sys
from datetime import timedelta
from dateutil import rrule
from matplotlib import dates
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg
from matplotlib.figure import Figure

class MplCanvas(FigureCanvasQTAgg):
    def __init__(self, dpi=96):
        self.fig = Figure(dpi=dpi)
        self.axes = self.fig.add_subplot(111)
        super(MplCanvas, self).__init__(self.fig)

# make a MPL canvas containing the requested plot
def plot(wl):
    canvas = MplCanvas()

    # plot using the original independent variable, the date, to get nicer output
    canvas.axes.plot(wl.data.dates, wl.data.weights, 'o', c="xkcd:burgundy", ms=4)

    # if interpolation is available, plot it and provide advice
    info = ""
    if wl.interpolation:
        canvas.axes.plot(wl.data.dates, wl.interpolation(wl.data.daynumbers), c="xkcd:dark navy blue")

        # Every `cycle` days, print out instructions
        if wl.data.daynumbers[-1] % wl.settings.cycle == 0:
            info = f"Consider adjusting intake by {wl.adjustment:+} calories per day."
        else:
            days_to_go = wl.settings.cycle - (wl.data.daynumbers[-1] % wl.settings.cycle)
            plural = "s" if days_to_go > 1 else ""
            info = f"Continue current intake for next {days_to_go} day{plural}."
            if wl.settings.always_show_adj:
                info += f" Adjustment value is {wl.adjustment:+}."

    # from here to the end of the method it's just formatting stuff
    # found by trial and error, mostly
    canvas.axes.set_xlabel("Date", labelpad=15)
    canvas.axes.set_ylabel(wl.data.weight_colname, labelpad=15)

    # pick reasonable values if we haven't seen enough data
    if (wl.data.end_date - wl.data.start_date).days < 14:
        canvas.axes.set_xlim(
            left = wl.data.start_date + timedelta(days=-1),
            right = wl.data.start_date + timedelta(days=15)
        )
    if len(wl.data.dates) == 0:
        canvas.axes.set_ylim(bottom=90, top=200)

    canvas.fig.suptitle("Weight Tracking")
    canvas.axes.set_title(info, fontsize=10, pad=20)
    locator = dates.AutoDateLocator(interval_multiples=False)
    locator.intervald[rrule.HOURLY] = [24]
    locator.intervald[rrule.MINUTELY] = [24 * 60]
    locator.intervald[rrule.SECONDLY] = [24 * 60 * 60]
    date_fmts = ['%b %Y', '%b %-d', '%b %-d', '%b %-d', '%b %-d', '%b %-d']
    if sys.platform == "win32":
        date_fmts = [x.replace('-', '#') for x in date_fmts]
    offset_fmts = ['', '%Y', '%Y', '%Y', '%Y', '%Y']
    formatter = dates.ConciseDateFormatter(locator, formats=date_fmts, offset_formats=offset_fmts)
    canvas.axes.xaxis.set_major_locator(locator)
    canvas.axes.xaxis.set_major_formatter(formatter)
    canvas.axes.grid(True)

    return canvas
