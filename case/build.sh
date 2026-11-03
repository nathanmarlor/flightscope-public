#!/bin/bash
# Rebuild the whole case: STLs, clash check, stand-ins, fit-test prints, renders and the viewer's data files.
#   First time:  uv venv case/.venv --python 3.12 && VIRTUAL_ENV=case/.venv uv pip install -r case/requirements.txt
#   Then:        case/build.sh            (add --holes to also measure every screw hole, ~2 min)
# Stops if the clash check finds anything. Needs ImageMagick's convert for the PNG renders.
set -euo pipefail
cd "$(dirname "$0")"
P=.venv/bin/python
[ -x $P ] || { echo "no case/.venv - set it up as the top of this script says"; exit 1; }
$P flightscope_case.py | grep -v "^done"
out=$($P check.py); echo "$out" | grep -E "FOUL|CHECK|clashes"
echo "$out" | grep -q "clashes: 0" || { echo "clash check failed - fix before printing"; exit 1; }
$P exploded.py >/dev/null
$P fit_test.py | grep -v "^fit prints"
$P views.py
if [ "${1:-}" = "--holes" ]; then $P holes.py; fi   # before the SVG pass: importing the model re-exports its previews
for f in out/*.svg; do convert -density 110 -background white -flatten -strip -define png:exclude-chunks=date,time "$f" "${f%.svg}.png" && rm "$f"; done
echo "built -> case/out (STLs, PNGs), case/viewer_layout.js, case/viewer_parts.js"
