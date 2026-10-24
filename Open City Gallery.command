#!/bin/bash
# Double-click me: opens the city gallery in your web browser.
# It lists every city built in the output folder, newest first, with "Open in 3D" buttons,
# and updates itself when new cities or pictures appear. Close this window to stop it.
cd "$(dirname "$0")" || exit 1
exec .venv/bin/python -m citygen gallery
