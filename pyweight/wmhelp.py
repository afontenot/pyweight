import os
import shutil
import subprocess
import webbrowser


webdocs = "https://github.com/afontenot/pyweight/wiki"

def get_cmd_response(cmd):
    cmd = cmd.split()
    proc = subprocess.run(cmd, capture_output=True, text=True)
    return proc.stdout.strip()


def try_find_docs():
    paths = ["./docs", "/usr/share/pyweight/docs"]
    for path in paths:
        if os.path.exists(path + "html/index.html"):
            return path + "html/index.html"


def open_help():
    mime = shutil.which("xdg-mime")
    xdgopen = shutil.which("xdg-open")
    docpath = try_find_docs()
    if xdgopen:
        if mime:
            xdg_help_query = "xdg-mime query default x-scheme-handler/helpx"
            help_scheme_handler = get_cmd_response(xdg_help_query)
            if help_scheme_handler != "":
                subprocess.run(["xdg-open", "help:/pyweight"])
                return
        if docpath:
            subprocess.run(["xdg-open", docpath])
            return
    if docpath:
        webbrowser.open(docpath)
    else:
        webbrowser.open(webdocs)
