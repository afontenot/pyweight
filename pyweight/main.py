import sys

from PyQt5.QtWidgets import QApplication

from pyweight.wmmainwindow import MainWindow


def main():
    app = QApplication(sys.argv)
    app.setOrganizationName("Adam Fontenot")
    app.setOrganizationDomain("adam.sh")
    app.setApplicationName("pyweight")
    app.setApplicationVersion("0.1")
    window = MainWindow(app)
    window.show()
    app.exec()
