import csv
import pytest

from datetime import datetime, timedelta
from io import StringIO
from pyweight.wmbodymodel import *
from pyweight.wmdatamodel import WeightTable
from pyweight.wmprofile import Profile


# FIXME: figure out how to make a fixture from this
class FakeData:
    def __init__(self, unique_path, today=None, weight=100):
        settings_path = str(unique_path / "settings.ini")
        self.profile = Profile(settings_path)
        self.profile.units.set("metric")
        self.profile.height.set(150)
        self.profile.wcrate.set(-0.1)
        self.blank_lbs_csv = '"Date", "Mass (kg)"'
        self.weight_i = weight
        self.weight = weight
        self.today = today
        self.csv_io = None
        self.weighttable = None
        self.weighttracker = None
        if not self.today:
            self.today = datetime.fromisoformat("2000-01-01")

    def add_day(self, weight=None, weight_change=None):
        weight_str = ""
        if weight is not None:
            self.weight = weight
            weight_str = self.weight
        elif weight_change is not None:
            self.weight += weight_change
            weight_str = self.weight
        self.blank_lbs_csv += f"\n{self.today.strftime('%Y/%m/%d')},{weight_str}"
        self.today += timedelta(days=1)

    @property
    def table(self):
        if self.csv_io:
            self.csv_io.close()
        self.csv_io = StringIO(self.blank_lbs_csv)
        csv_r = csv.reader(self.csv_io)
        return WeightTable(None, csv_r)

    @property
    def tracker(self):
        wt = self.table
        return WeightTracker(wt, self.profile)


# approximate figures taken from chart in Hall (2008)
def test_delta_lean():
    # test individual: initial fat mass 38 kg
    body_mass_change = -5 # kg
    predicted_wl_energy_density = 32.2 # MJ/kg
    lean_change = body_mass_change * (39.5 - predicted_wl_energy_density) / 31.9
    assert(round(lean_change, 3) == -1.144) # validate test
    # enforce within 1/10 kg
    assert(abs(delta_lean(-5, 38) - lean_change) < 0.1)

    # test individual: initial fat mass 20 kg
    body_mass_change = -25 # kg
    predicted_wl_energy_density = 24.8 # MJ/kg
    lean_change = body_mass_change * (39.5 - predicted_wl_energy_density) / 31.9
    assert(round(lean_change, 3) == -11.520) # validate test
    assert(abs(delta_lean(-25, 20) - lean_change) < 0.1)

def test_initial_body_fat_est():
    # test individual: age 25, female, BMI 30
    weight = 76.8 # kg
    height = 1.6 # meters
    bmi = weight / height ** 2
    assert(round(bmi, 6) == 30) # validate test
    result = initial_body_fat_est(
        weight = weight,
        age = 25,
        height = height,
        gender_prop = 0
    )
    assert(31.251 == round(result, 3))

    # test individual: age 50, male, BMI 20
    weight = 80 # kg
    height = 2 # meters
    bmi = weight / height ** 2
    assert(round(bmi, 6) == 20) # validate test
    result = initial_body_fat_est(
        weight = weight,
        age = 50,
        height = height,
        gender_prop = 1
    )
    assert(13.922 == round(result, 3))

def test_initial_body_fat_est_with_genderprop():
    # test individual: age 40, 60% male, BMI 25
    weight = 81 # kg
    height = 1.8 # meters
    bmi = weight / height ** 2
    assert(round(bmi, 6) == 25) # validate test
    male_result = initial_body_fat_est(
        weight = weight,
        age = 40,
        height = height,
        gender_prop = 1
    )
    female_result = initial_body_fat_est(
        weight = weight,
        age = 40,
        height = height,
        gender_prop = 0
    )
    expected_result = 0.6 * male_result + 0.4 * female_result
    actual_result = initial_body_fat_est(
        weight = weight,
        age = 40,
        height = height,
        gender_prop = 0.6
    )
    assert(round(expected_result, 6) == round(actual_result, 6))

# TODO: try to find a delta_e correctness test from research papers

def test_delta_e_stability():
    assert(-32570 == round(delta_e(80, 70, 65, 25)))

def test_delta_e_sanity():
    # multi stage weight loss: caloric deficits should sum the same
    # for any size of stages; e.g. two 5 kg stages = one 10 kg stage
    stage_1 = delta_e(80, 70, 65, 25)
    stage_2 = delta_e(80, 65, 60, 25)
    one_step = delta_e(80, 70, 60, 25)
    assert(round(one_step) == round(stage_1 + stage_2))

def test_knots(tmp_path):
    # with cycle days, no knots
    fd = FakeData(tmp_path)
    for _ in range(fd.profile.cycle):
        fd.add_day(weight_change=0)
    assert(fd.tracker.knots == [])

    # with cycle + 1 days, one knot at cycle (knot appears after day ends)
    fd.add_day(weight_change=0)
    assert(fd.tracker.knots == [fd.profile.cycle])

def test_knots_with_missing_days(tmp_path):
    # check whether knot still appears with cycle + 1 days
    # when we make 2 of them blank
    fd = FakeData(tmp_path)
    pre_days = (fd.profile.cycle - 1) // 2
    post_days = (fd.profile.cycle - 1) - pre_days
    for _ in range(pre_days):
        fd.add_day(weight_change=0)
    for _ in range(2): # two blank days
        fd.add_day()
    for _ in range(post_days):
        fd.add_day(weight_change=0)
    assert(fd.tracker.knots == [fd.profile.cycle])

def test_interpolation(tmp_path):
    fd = FakeData(tmp_path)
    for _ in range(fd.profile.cycle):
        fd.add_day(weight_change=0)
    for _ in range(fd.profile.cycle):
        fd.add_day(weight_change=fd.profile.wcrate)
    expected = [fd.weight_i, fd.weight_i, fd.weight_i + fd.profile.cycle * fd.profile.wcrate]
    # can't compare numpy arrays directly
    actual = [round(x, 10) for x in fd.tracker.interpolation.get_coeffs()]
    assert(actual == expected)

def test_adjustment_sanity_1(tmp_path):
    # perfect adhesion -> adjustment of 0
    fd = FakeData(tmp_path)
    for _ in range(fd.profile.cycle):
        fd.add_day(weight_change=fd.profile.wcrate)
    assert(fd.tracker.adjustment == 0)

def test_adjustment_sanity_2(tmp_path):
    # no change -> adjustment = delta_e
    fd = FakeData(tmp_path)
    for _ in range(fd.profile.cycle):
        fd.add_day(weight_change=0)
    body_fat_i = initial_body_fat_est(fd.weight_i, fd.profile.age, fd.profile.height * 0.01, fd.profile.gender_prop)
    target_weight = fd.weight_i + fd.profile.wcrate * fd.profile.cycle
    correct = round(delta_e(fd.weight_i, fd.weight, target_weight, body_fat_i) / fd.profile.cycle)
    assert(fd.tracker.adjustment == correct)

