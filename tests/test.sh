#!/usr/bin/env bash
set -Eeuo pipefail
R=/logs/verifier/reward.txt; T="$R.tmp.$$"; mkdir -p /logs/verifier; printf '0.000\n' > "$R"; trap 'printf "0.000\n" > "$R"; rm -f "$T"; exit 1' ERR INT TERM HUP
cd /tests
python3 -B -m pytest -q -p no:cacheprovider --junitxml=/logs/verifier/junit.xml -c /tests/pytest.ini /tests/test_outputs.py > /logs/verifier/pytest.log 2>&1
python3 -B - <<'PY' > "$T"
import xml.etree.ElementTree as ET
r=ET.parse('/logs/verifier/junit.xml').getroot(); s=r.find('testsuite') or r
assert int(s.attrib.get('tests',0))==12 and int(s.attrib.get('failures',0))==0 and int(s.attrib.get('errors',0))==0 and int(s.attrib.get('skipped',0))==0
print('1.000')
PY
mv -f "$T" "$R"; trap - ERR INT TERM HUP
