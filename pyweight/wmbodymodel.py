from math import exp

from scipy.interpolate import LSQUnivariateSpline as LSpline
from scipy.special import lambertw

# A set of equations for working out how many calories are associated with a
# given amount of weight loss.
#
# According to Hall (2008), the amount of lean body mass lost can be estimated
# purely as a function of initial fat mass and the change in body weight. Using
# this information, we can trivially calculate how much fat mass was lost. With
# both these values available, we can calculate the calorie deficit associated
# with a particular change in weight using caloric density values for lean and
# fat mass also provided by Hall.
# https://www.ncbi.nlm.nih.gov/pmc/articles/PMC2376744/


# This is a modification of the formula given in Hall (2008)
def delta_lean(delta_bw, fat_i):
    return (
        delta_bw
        + fat_i
        - 10.4
        * lambertw(1 / 10.4 * exp(delta_bw / 10.4) * fat_i * exp(fat_i / 10.4)).real
    )


# Estimate from CUN-BAE equation. Far from perfect, better than nothing.
# https://pubmed.ncbi.nlm.nih.gov/22179957/
#
# A few notes:
# 1. Flawed in that the study population was exclusively white.
# 2. Cui et al. (2014) found this method to be among the best performing
#    among tested methods. Not without bias, but surprisingly strong
#    correlations even for non-white Americans.
#    https://pubmed.ncbi.nlm.nih.gov/24576861/
# 3. The most promising alternative I could find was Lee et al. (2017)
#    https://pubmed.ncbi.nlm.nih.gov/29110742/
#    There were several issues that I could see with using this model.
#    One is that it's an entirely linear model. From other studies, I'm
#    skeptical that e.g. height has a linear relationship with body fat
#    percentage. Also, it uses race as an explicit variable. That might
#    lead to more slightly more accurate results, but it would mean we
#    have to ask the user for that information - meaning we have to be
#    exclusionary, since not every race (or race-combination) is part of
#    the model. I noticed that in some cases, increased weight had a
#    *negative* correlation with weight in the model, which seems deeply
#    counter-intuitive. Last, the model hasn't yet been validated by an
#    external paper. I'm open to other alternatives, file a Github issue
#    if you have one.

# weight in kg, age in years, height in meters; returns kg body fat
def initial_body_fat_est(weight, age, height, gender_prop):
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


# calculate total caloric deficit associated with a given amount of weight loss
# all parameters are in kilograms
def delta_e(initial_w, previous_w, current_w, fat_i):
    previous_delta_lean = delta_lean(previous_w - initial_w, fat_i)
    full_delta_lean = delta_lean(current_w - initial_w, fat_i)
    current_delta_lean = full_delta_lean - previous_delta_lean
    weight_change = current_w - previous_w
    fat_mass_change = weight_change - current_delta_lean
    # density values from Hall (2008): pf = 39.5 MJ/kg, pl = 7.6 MJ/kg
    return 9441 * fat_mass_change + 1820 * current_delta_lean


# variant of delta_e that estimates the initial body fat mass
# age in years, height in meters, gender_prop is a proportion
def delta_e_auto(initial_w, previous_w, current_w, age, height, gender_prop):
    fat_i = initial_body_fat_est(initial_w, age, height, gender_prop)
    return delta_e(initial_w, previous_w, current_w, fat_i)


# works out the correct gender proportion based on whether the user chose an
# explicit gender or not; if not, use the gender_prop value
def gender_proportion(gender_selection, gender_prop):
    gender_proportion = 0.5
    if gender_selection == "female":
        gender_proportion = 0
    elif gender_selection == "male":
        gender_proportion = 1
    elif gender_selection == "other":
        gender_proportion = gender_prop
    return gender_proportion


def height_in_meters(height, unit):
    if unit == "in":
        height *= 0.0254
    elif unit == "cm":
        height *= 0.01
    return height


# represents a set of weight change data and associated variables
class WeightTracker:
    def __init__(self, data, settings):
        self.data = data  # data from a WeightTable
        self.settings = settings  # a WMSettings
        self._interpolation = None
        self._adjustment = None
        self._knots = None

    # discontinuity every `cycle` days in the range
    @property
    def knots(self):
        if not self._knots:
            day_distance = (self.data.end_date - self.data.start_date).days
            number_of_cycles = day_distance // self.settings.cycle + 1
            self._knots = [i * self.settings.cycle for i in range(1, number_of_cycles)]
        return self._knots

    # caches (and returns) a spline fit
    @property
    def interpolation(self):
        # if there's only one data point, nothing to interpolate
        if len(self.data.dates) <= 1:
            return None
        if not self._interpolation:
            # spline interpolation: k=1 means linear fit, knots = chosen discontinuities
            # we use day numbers instead of dates directly because LSQUnivariateSpline
            # can't handle dates; note that this is the number of days since the first
            # record (not number of entries), so linear interpolation remains valid
            self._interpolation = LSpline(
                self.data.daynumbers, self.data.weights, self.knots, k=1
            )
        return self._interpolation

    # calculate daily difference, in calories, between chosen rate and calculated rate
    # note: you may only call adjustment if there are at least two data points,
    # because it depends on an spline fit across the data; otherwise self.interpolation()
    # won't return a callable.
    @property
    def adjustment(self):
        if self._adjustment:
            return self._adjustment
        # get interpolated weights for three control points in data
        today = self.data.daynumbers[-1]
        first_day = self.data.daynumbers[0]
        if len(self.knots) >= 1:
            last_cycle = self.knots[-1]
        else:
            last_cycle = first_day
        weight_mult = 1 if self.data.units == "kg" else 0.45359237
        today_weight = self.interpolation(today) * weight_mult
        first_day_weight = self.interpolation(first_day) * weight_mult
        last_cycle_weight = self.interpolation(last_cycle) * weight_mult
        rate_kg = self.settings.wcrate * weight_mult

        # get caloric deficit associated with the current cycle *and*
        # caloric deficit associated with desired weight loss this cycle

        # use number of days into present cycle to calculate expected change
        days_in_current_cycle = today - last_cycle

        # convert to meters
        height_meters = height_in_meters(
            self.settings.height, self.settings.height_unit
        )

        gender_prop = gender_proportion(
            self.settings.gender_selection, self.settings.gender_prop
        )

        if self.settings.body_fat_method == "automatic":
            cycle_delta_e = delta_e_auto(
                first_day_weight,
                last_cycle_weight,
                today_weight,
                self.settings.age,
                height_meters,
                gender_prop,
            )
            cycle_desired_delta_e = delta_e_auto(
                first_day_weight,
                last_cycle_weight,
                last_cycle_weight + (rate_kg * days_in_current_cycle),
                self.settings.age,
                height_meters,
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
                last_cycle_weight + (rate_kg * days_in_current_cycle),
                self.settings.manual_body_fat * first_day_weight,
            )

        # calculate adjustment from difference between desired and actual
        self._adjustment = round(
            (cycle_desired_delta_e - cycle_delta_e) / days_in_current_cycle
        )
        return self._adjustment
