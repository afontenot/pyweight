import sys

from PyQt5.QtWidgets import QApplication

import pyweight
from pyweight.wmmainwindow import MainWindow
import pyweight.qresources


def main():
    app = QApplication(sys.argv)
    app.setOrganizationName("pyweight")
    app.setOrganizationDomain("adam.sh")
    app.setApplicationName("pyweight")
    app.setApplicationVersion(pyweight.__VERSION__)
    window = MainWindow(app)
    window.show()
    app.exec()


if __name__ == "__main__":
    main()
