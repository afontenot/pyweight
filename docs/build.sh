#!/usr/bin/env bash

shopt -s extglob
set -euo pipefail

cd "$(dirname "$0")"
for file in md/*.md; do pandoc -o "html/${file//+(*\/|.*)}.html" --mathjax -s "$file"; done
