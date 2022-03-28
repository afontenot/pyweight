import pytest

from pyweight.wmmainwindow import MainWindow

# the tests we can do here are limited, because of heavy reliance on Qt

class FakeMainWindow(MainWindow):
    def __init__(self):
        self.app = "FakeApp"

def test_window_wrapper_created():
    mw = FakeMainWindow()
    assert(mw.app == "FakeApp")
