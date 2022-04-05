# Welcome to Pyweight!

Pyweight is a simple desktop application for managing an individual's
weight. Pyweight makes it easy to track your weight over time and can
suggest changes to the number of calories you are eating to help you
hit targets for weight loss, gains, or even maintenance.

## Installing Pyweight

How you use Pyweight will depend on what platform you want to use it
on. Pyweight should run on any PC platform with support for its
dependencies, but has only been tested on Linux and Windows.

### Linux installation (from source)

One significant goal for future development is getting Pyweight in a
form where it can easily be packaged by Linux distribution
maintainers. At present, however, it can only be installed to a local
directory and run from its source files.

You can either use a
[released version](https://github.com/afontenot/pyweight/releases) of
the application (recommended) or simply run it from a clone of the
repository.

Dependencies:

 * Python (3.7+)
 * PyQt5
 * matplotlib
 * scipy

If you have expertise with packaging Python programs or want to
destribute this program for your Linux distribution, please file an
issue.

### Windows installation

Experimental builds of the program are available for Windows in the
[releases](https://github.com/afontenot/pyweight/releases).

These builds are available as single executable files and do not need
to be installed.

We would like to provide installation and updates for Pyweight on
Windows. If you want to help with this, please file an issue.

### Using Pyweight on other platforms

If you want to use Pyweight on other platforms, such as macOS, you
currently need to follow the instructions for Linux usage and install
Pyweight's source dependencies.

Pyweight is known to be able to start on macOS, but has not been
tested beyond that. We're currently looking for someone with the
knowledge to package Pyweight as a macOS application in a dmg file.
If you can help with this, please file an issue.

## Running Pyweight

Once you have Pyweight installed, you can either run the Pyweight
executable directly, or if you're running it from the source tree,

    python3 pyweight.py

should suffice.
