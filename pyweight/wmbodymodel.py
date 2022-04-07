from math import exp

from scipy.interpolate import LSQUnivariateSpline as LSpline
from scipy.special import lambertw

from pyweight.wmutils import lbs_to_kg

# Note: see the Technical Concepts page in the docs for more details


def delta_lean(delta_bw, fat_i):
    """Calculate how much the body's lean mass has changed during weight loss.

    According to Hall (2008), the amount of lean body mass lost can be estimated
    purely as a function of initial fat mass and the change in body weight. Using
    this information, we can trivially calculate how much fat mass was lost. With
    both these values available, we can calculate the calorie deficit associated
    with a particular change in weight using caloric density values for lean and
    fat mass also provided by Hall.
    https://www.ncbi.nlm.nih.gov/pmc/articles/PMC2376744/

    This is a modification of the formula given in Hall.

    The function derives from the claim that relative changes in fat and lean
    mass satisfy the equation

        L = 10.4 log (F) + A

    where A is a constant specific to the body-type and assumed not to change
    under weight-loss conditions. (It could change due to e.g. weight lifting.)

    Give this assumption, it is not hard to show that final fat (lean) mass is
    purely a function of intial fat (lean) mass and total mass change, and that
    the relation has the following formula.

    Args:
        delta_bw: total kg of mass change (positive = increasing)
        fat_i: kg of fat on the body at the outset of weight change
    """
    return (
        delta_bw
        + fat_i
        - 10.4
        * lambertw(1 / 10.4 * exp(delta_bw / 10.4) * fat_i * exp(fat_i / 10.4)).real
    )


# weight in kg, age in years, height in meters; returns kg body fat
def initial_body_fat_est(weight, age, height, gender_prop):
    """Estimates initial fraction of body weight that is fat.

    Based on the CUN-BAE equation. Far from perfect, better than nothing.
    https://pubmed.ncbi.nlm.nih.gov/22179957/

    A few notes:
      1. Flawed in that the study population was exclusively white.
      2. Cui et al. (2014) found this method to be among the best performing
         among tested methods. Not without bias, but surprisingly strong
         correlations even for non-white Americans.
         https://pubmed.ncbi.nlm.nih.gov/24576861/
      3. The most promising alternative I could find was Lee et al. (2017)
         https://pubmed.ncbi.nlm.nih.gov/29110742/
         There were several issues that I could see with using this model.
         One is that it's an entirely linear model. From other studies, I'm
         skeptical that e.g. height has a linear relationship with body fat
         percentage. Also, it uses race as an explicit variable. That might
         lead to more slightly more accurate results, but it would mean we
         have to ask the user for that information - meaning we have to be
         exclusionary, since not every race (or race-combination) is part of
         the model. I noticed that in some cases, increased weight had a
         *negative* correlation with weight in the model, which seems deeply
         counter-intuitive. Last, the model hasn't yet been validated by an
         external paper. I'm open to other alternatives, file a Github issue
         if you have one.

    Args:
        weight: body weight at outset of tracking, in kg
        age: age in years
        height: height in meters(!)
        gender_prop: the weights to assign to the body fat estimates for each
            gender; for most people will be 1 (male) or 0 (female).
    """
    bmi = weight / height**2
    bf_perc_female = (
        -34.299
        + 0.503 * age
        + 3.353 * bmi
        - 0.031 * bmi**2
        - 0.020 * bmi * age
        + 0.00021 * bmi**2 * age
    )
    bf_perc_male = (
        -44.988
        + 0.503 * age
        + 3.172 * bmi
        - 0.026 * bmi**2
        - 0.020 * bmi * age
        + 0.00021 * bmi**2 * age
    )
    return (
        weight * (bf_perc_male * gender_prop + bf_perc_female * (1 - gender_prop)) / 100
    )


def delta_e(initial_w, previous_w, current_w, fat_i):
    """Calculates calorie deficit associated with specified weight change.

    Uses the `delta_lean` function to determine how much of a specific
    period of weight change involved fat change, and how much lean change.
    Given this information, determines the caloric density of the change.

    Note that this method returns the calorie surplus or deficit associated
    with the *current* period - meaning the change from `previous_w` to
    `current_w`. The reason `initial_w` is relevant is that the *total* size
    of the weight loss affects the `delta_lean` estimate of current fat mass,
    and therefore, the density of the recent change.

    Args:
        initial_w: weight at beginning of tracking period (kg)
        previous_w: weight just before the change (kg)
        current_w: weight just after the change (kg)
        fat_i: fat mass on the same date as initial_w (kg)
    """
    previous_delta_lean = delta_lean(previous_w - initial_w, fat_i)
    full_delta_lean = delta_lean(current_w - initial_w, fat_i)
    current_delta_lean = full_delta_lean - previous_delta_lean
    weight_change = current_w - previous_w
    fat_mass_change = weight_change - current_delta_lean
    # density values from Hall (2008): pf = 39.5 MJ/kg, pl = 7.6 MJ/kg
    return 9441 * fat_mass_change + 1820 * current_delta_lean


def delta_e_auto(initial_w, previous_w, current_w, age, height, gender_prop):
    """Calculates calorie deficit assoc with weight change, automatic fat_i estimate.

    Identical to (and calls) `delta_e`, except that three additional parameters
    are first used to get an estimate of initial fat mass, which is used instead
    of a manually provided value.

    Args:
        initial_w: weight at beginning of tracking period (kg)
        previous_w: weight just before the change (kg)
        current_w: weight just after the change (kg)
        fat_i: fat mass on the same date as initial_w (kg)
        age: age in years
        height: height in meters(!)
        gender_prop: weights to assign to the body fat estimates for each gender
    """
    fat_i = initial_body_fat_est(initial_w, age, height, gender_prop)
    return delta_e(initial_w, previous_w, current_w, fat_i)


def gender_proportion(gender_selection, gender_prop) -> float:
    """Converts a text-based gender selection to a decimal gender property."""
    if gender_selection == "female":
        return 0.0
    if gender_selection == "male":
        return 1.0
    if gender_selection == "other":
        return gender_prop
    return 0.5


class WeightTracker:
    """Representation of a set of weight change data and associated properties.

    Takes data from a WeightTable (model) and
      * calculates an interpolated fit to the data
      * calculates adjustment advice that can be printed, if desired

    Attributes:
        data: a WeightTable that the WeightTracker is an assessment of
        settings: a Plan providing interpretive information (e.g. units)
        adjustment: difference between wanted and achieved calories this cycle
        interpolation: a ScyPy linear spline fit to the data
        knots: a list of points (in day numbers) where the spline bends
    """

    def __init__(self, data, settings):
        self.data = data
        self.settings = settings
        self._interpolation = None
        self._adjustment = None
        self._knots = None

    @property
    def knots(self) -> list:
        """Gets (and caches) a list of points every `cycle` days until end date."""
        if not self._knots:
            day_distance = (self.data.end_date - self.data.start_date).days
            number_of_cycles = day_distance // self.settings.cycle
            self._knots = [
                i * self.settings.cycle for i in range(1, number_of_cycles + 1)
            ]
        return self._knots

    @property
    def interpolation(self):
        """Gets (and caches) a least-squares linear spline fit to the data.

        Fits a spline to the user's entire weight history. The spline has knots
        at each of the cycle endpoints. This mirrors the behavior of a linear
        regression, but adds the additional constraint that the resulting fit
        must be continuous.

        Using the interpolation for determining weight values at arbitrary
        points in the history (e.g. the starting weight) is recommend, because
        the spline fit is assumed to be much more accurate than the raw value.
        """
        # if there's only one data point, nothing to interpolate
        if len(self.data.dates) <= 1:
            return None
        if not self._interpolation:
            # spline interpolation: k=1 means linear fit, knots = spline flex points
            # we use day numbers instead of dates directly because LSQUnivariateSpline
            # can't handle dates; note that this is the number of days since the first
            # record (not number of entries), so linear interpolation remains valid
            self._interpolation = LSpline(
                self.data.daynumbers, self.data.weights, self.knots, k=1
            )
        return self._interpolation

    @property
    def interpolation_metric(self):
        """Returns a function wrapping `interpolation` for imperial units."""
        if self.settings.units == "imperial":

            def interp_fn(d):
                return lbs_to_kg(self.interpolation(d))

            return interp_fn
        return self.interpolation

    @property
    def adjustment(self) -> int:
        """Get calorie difference between chosen rate and calculated rate.

        Returns a cached value, if available.

        This method wraps all the other module functions together,
        and provides a single value as output. It checks the settings
        to determine the cycle period, requests the knots and interpolation,
        and then calls `delta_e` to determine the calories associated with
        the user's data history. The difference between the expected and
        achieved calorie deficit (or surplus) is rounded to the nearest
        calorie and returned.
        """
        if self._adjustment:
            return self._adjustment
        # get interpolated weights for three control points in data
        today = self.data.daynumbers[-1]
        first_day = self.data.daynumbers[0]
        if len(self.knots) >= 1:
            last_cycle = self.knots[-1]
        else:
            last_cycle = first_day

        today_weight = self.interpolation_metric(today)
        first_day_weight = self.interpolation_metric(first_day)
        last_cycle_weight = self.interpolation_metric(last_cycle)

        # get caloric deficit associated with the current cycle *and*
        # caloric deficit associated with desired weight loss this cycle

        # use number of days into present cycle to calculate expected change
        days_in_current_cycle = today - last_cycle

        gender_prop = gender_proportion(
            self.settings.gender_selection, self.settings.gender_prop
        )

        if self.settings.body_fat_method == "automatic":
            cycle_delta_e = delta_e_auto(
                first_day_weight,
                last_cycle_weight,
                today_weight,
                self.settings.age,
                self.settings.height,
                gender_prop,
            )
            cycle_desired_delta_e = delta_e_auto(
                first_day_weight,
                last_cycle_weight,
                last_cycle_weight + (self.settings.wcrate * days_in_current_cycle),
                self.settings.age,
                self.settings.height,
                gender_prop,
            )
        else:
            cycle_delta_e = delta_e(
                first_day_weight,
                last_cycle_weight,
                today_weight,
                self.settings.manual_body_fat * first_day_weight,
            )
            cycle_desired_delta_e = delta_e(
                first_day_weight,
                last_cycle_weight,
                last_cycle_weight + (self.settings.wcrate * days_in_current_cycle),
                self.settings.manual_body_fat * first_day_weight,
            )

        # calculate adjustment from difference between desired and actual
        self._adjustment = round(
            (cycle_desired_delta_e - cycle_delta_e) / days_in_current_cycle
        )
        return self._adjustment
