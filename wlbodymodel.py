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
    return delta_bw + fat_i - 10.4 * lambertw(1/10.4 * exp(delta_bw/10.4)*fat_i*exp(fat_i/10.4)).real

# Estimate from CUN-BAE equation. Far from perfect, better than nothing.
# https://pubmed.ncbi.nlm.nih.gov/22179957/
# weight in kg, age in years, height in meters
def initial_body_fat_est(weight, age, height, gender_prop):
    bmi = weight / height ** 2
    bf_perc_female = (
        -34.299 + 
        +0.503 * age +
        +3.353 * bmi +
        -0.031 * bmi**2 +
        -0.020 * bmi * age +
        +0.00021 * bmi**2 * age
    )
    bf_perc_male = (
        -44.988 + 
        +0.503 * age +
        +3.172 * bmi +
        -0.026 * bmi**2 +
        -0.020 * bmi * age +
        +0.00021 * bmi**2 * age
    )
    return weight * (bf_perc_male * gender_prop + bf_perc_female * (1 - gender_prop)) / 100

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



# represents a set of weight change data and associated variables
class WeightLoss():
    def __init__(self, data, settings):
        self.data = data # data from a WeightTable
        self.settings = settings # a WlSettings
        self._interpolation = None
        self._adjustment = None
        self._knots = None
        
    # discontinuity every `cycle` days in the range
    @property
    def knots(self):
        if not self._knots:
            number_of_cycles = 1 + (self.data.end_date - self.data.start_date).days // self.settings.cycle
            self._knots = [i * self.settings.cycle for i in range(1, number_of_cycles)]
        return self._knots
    
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
            self._interpolation = LSpline(self.data.daynumbers, self.data.weights, self.knots, k=1)
        return self._interpolation
    
    ## calculate daily difference, in calories, between chosen rate and calculated rate
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
        weight_mult = ((self.data.units != "kg") and 0.45359237) or 1
        today_weight = self.interpolation(today) * weight_mult
        first_day_weight = self.interpolation(first_day) * weight_mult
        last_cycle_weight = self.interpolation(last_cycle) * weight_mult
        rate_kg = self.settings.rate * weight_mult
        
        # get caloric deficit associated with the current cycle *and*
        # caloric deficit associated with desired weight loss this cycle
        
        # use number of days into present cycle to calculate expected wl
        days_in_current_cycle = today - last_cycle
        
        # convert to meters
        height_meters = self.settings.height
        if self.settings.height_unit == "in":
            height_meters *= 0.0254
        elif self.settings.height_unit == "cm":
            height_meters *= 0.01        
        
        if self.settings.body_fat_method == "automatic":
            cycle_delta_e = delta_e_auto(
                first_day_weight,
                last_cycle_weight,
                today_weight,
                self.settings.age,
                height_meters,
                self.settings.gender_prop
            )
            cycle_desired_delta_e = delta_e_auto(
                first_day_weight,
                last_cycle_weight,
                last_cycle_weight + (rate_kg * days_in_current_cycle),
                self.settings.age,
                height_meters,
                self.settings.gender_prop
            )
        else:
            cycle_delta_e = delta_e(
                first_day_weight,
                last_cycle_weight,
                today_weight,
                self.settings.manual_body_fat * first_day_weight
            )
            cycle_desired_delta_e = delta_e(
                first_day_weight,
                last_cycle_weight,
                last_cycle_weight + (rate_kg * days_in_current_cycle),
                self.settings.manual_body_fat * first_day_weight
            )

        # calculate adjustment from difference between desired and actual
        self._adjustment = round((cycle_desired_delta_e - cycle_delta_e) / days_in_current_cycle)
        return self._adjustment
