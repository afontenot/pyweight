import os
import shutil
import subprocess
import webbrowser


webdocs = "https://github.com/afontenot/pyweight/wiki"


def get_cmd_response(cmd):
    """Capture the output from running a process."""
    cmd = cmd.split()
    proc = subprocess.run(cmd, capture_output=True, text=True)
    return proc.stdout.strip()


def try_find_docs():
    """Search for documentation root.

    Assuming local docs are available, they should be stored in
    either a standard system location or in the current directory.

    In the case that we're running pyweight from a source dir, it
    could also be the parent directory.
    """
    paths = ["./docs", "../docs", "/usr/share/pyweight/docs"]
    for path in paths:
        if os.path.exists(path + "/html/index.html"):
            return os.path.abspath(path + "/html/index.html")


def open_help():
    """Looks for documentation and opens it sensibly, cross platform.

    Most of this is for Linux, which has built in help viewers we can
    use (with the help:/progname scheme). If not on Linux or a viewer
    isn't available, use a web browser. Falls back to online docs.

    Note that some of this code is currently deactivated.
    """
    mime = shutil.which("xdg-mime")
    xdgopen = shutil.which("xdg-open")
    doc_path = try_find_docs()
    if mime and xdgopen:
        # note: the typo in the query is on purpose
        # this is currently WIP for testing
        xdg_help_query = "xdg-mime query default x-scheme-handler/helpx"
        help_scheme_handler = get_cmd_response(xdg_help_query)
        if help_scheme_handler != "":
            subprocess.run(["xdg-open", "help:/pyweight"])
            return
    if doc_path:
        webbrowser.open(doc_path)
    else:
        webbrowser.open(webdocs)
