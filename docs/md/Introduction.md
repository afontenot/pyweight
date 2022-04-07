# Welcome to PyWeight!

PyWeight is a simple desktop application for managing your
weight. PyWeight makes it easy to track your weight over time and can
suggest changes to the number of calories you are eating to help you
hit targets for weight loss, gains, or even maintenance.

## Installing PyWeight

How you use PyWeight will depend on what platform you want to use it
on. PyWeight should run on any PC platform with support for its
dependencies, but has only been tested on Linux and Windows.

### Linux installation (from source)

One significant goal for future development is getting PyWeight in a
form where it can easily be packaged by Linux distribution
maintainers. At present, however, it can only be installed to a local
directory and run from its source files.

You can either use a
[released version](https://github.com/afontenot/pyweight/releases) of
the application (recommended) or simply run it from a clone of the
repository.

Dependencies:

 * Python (3.6+)
 * PyQt5
 * matplotlib
 * scipy

If you have expertise with packaging Python programs or want to
distribute this program for your Linux distribution, please file an
issue.

### Windows installation

Experimental builds of the program are available for Windows in the
[releases](https://github.com/afontenot/pyweight/releases).

These builds are available as single executable files and do not need
to be installed.

We would like to provide installation and updates for PyWeight on
Windows. If you want to help with this, please file an issue.

### Using PyWeight on other platforms

If you want to use PyWeight on other platforms, such as macOS, you
currently need to follow the instructions for Linux usage and install
PyWeight's source dependencies.

PyWeight is known to be able to start on macOS, but has not been
tested beyond that. We're currently looking for someone with the
knowledge to package PyWeight as a macOS application in a dmg file.
If you can help with this, please file an issue.

## Running PyWeight

Once you have PyWeight installed, you can either run the PyWeight
executable directly, or if you're running it from the source tree,

    python3 -m pyweight

should suffice.
