from datetime import timedelta
from dateutil import rrule
from matplotlib import dates
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg
from matplotlib.figure import Figure

from scipy import interpolate

class MplCanvas(FigureCanvasQTAgg):
    def __init__(self, dpi=96):
        self.fig = Figure(dpi=dpi)
        self.axes = self.fig.add_subplot(111)
        super(MplCanvas, self).__init__(self.fig)

# make a MPL canvas containing the requested plot
def plot(data, settings):
    canvas = MplCanvas()

    # it's nice to plot something even if we can't interpolate
    # so we'll selectively disable things.
    can_interpolate = len(data.dates) > 1
    info = ""

    # discontinuity every `cycle` days in the range
    knots = [i * settings.cycle for i in range(1,1 + (data.end_date - data.start_date).days // settings.cycle)]

    # spline interpolation: k=1 means linear fit, knots = chosen discontinuities
    # we use day numbers instead of dates directly because LSQUnivariateSpline
    # can't handle dates; note that this is the number of days since the first
    # record (not number of entries), so linear interpolation remains valid

    # it's nice to plot *something* even if we can't interpolate
    if can_interpolate:
        interp = interpolate.LSQUnivariateSpline(data.daynumbers, data.weights, knots, k=1)

        # calculate daily difference, in calories, between chosen rate and calculated rate
        rate_diff = settings.rate - interp.derivative()(data.daynumbers[-1])
        calorie_mult = 3500
        if data.units == "kg":
            calorie_mult *= 0.4536
        adjust = int(calorie_mult * rate_diff)

        # Every `cycle` days, print out instructions
        if data.daynumbers[-1] % settings.cycle == 0:
            info = f"Consider adjusting intake by {adjust:+} calories per day."
        else:
            days_to_go = settings.cycle - (data.daynumbers[-1] % settings.cycle)
            info = f"Continue current intake for next {days_to_go} days."
            if settings.always_show_adj:
                info += f" Adjustment value is {adjust:+}."

    # plot using the original independent variable, the date, to get nicer output
    canvas.axes.plot(data.dates, data.weights, 'o', c="xkcd:burgundy", ms=4)
    if can_interpolate:
        canvas.axes.plot(data.dates, interp(data.daynumbers), c="xkcd:dark navy blue")

    # from here to the end of the method it's just formatting stuff
    # found by trial and error, mostly
    canvas.axes.set_xlabel("Date", labelpad=15)
    canvas.axes.set_ylabel(data.weight_colname, labelpad=15)

    # pick reasonable values if we haven't seen enough data
    if (data.end_date - data.start_date).days < 14:
        canvas.axes.set_xlim(
            left = data.start_date + timedelta(days=-1),
            right = data.start_date + timedelta(days=15)
        )
    if len(data.dates) == 0:
        canvas.axes.set_ylim(bottom=90, top=200)

    canvas.fig.suptitle("Weight Tracking")
    canvas.axes.set_title(info, fontsize=10, pad=20)
    locator = dates.AutoDateLocator(interval_multiples=False)
    locator.intervald[rrule.HOURLY] = [24]
    locator.intervald[rrule.MINUTELY] = [24 * 60]
    locator.intervald[rrule.SECONDLY] = [24 * 60 * 60]
    date_fmts = ['%b %Y', '%b %-d', '%b %-d', '%b %-d', '%b %-d', '%b %-d']
    offset_fmts = ['', '%Y', '%Y', '%Y', '%Y', '%Y']
    formatter = dates.ConciseDateFormatter(locator, formats=date_fmts, offset_formats=offset_fmts)
    canvas.axes.xaxis.set_major_locator(locator)
    canvas.axes.xaxis.set_major_formatter(formatter)
    canvas.axes.grid(True)

    return canvas
