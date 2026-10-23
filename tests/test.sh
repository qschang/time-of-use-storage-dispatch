#!/usr/bin/env bash
set -Eeuo pipefail
R=/logs/verifier/reward.txt; T="$R.tmp.$$"; mkdir -p /logs/verifier; chmod 0444 /tests/test_outputs.py /tests/score.py 2>/dev/null || true; printf '0.000\n' > "$R"; trap 'printf "0.000\n" > "$R"; rm -f "$T"; exit 1' ERR INT TERM HUP
cd /tests
timeout 300 python3 -B -m pytest -q -p no:cacheprovider --junitxml=/logs/verifier/junit.xml -c /tests/pytest.ini /tests/test_outputs.py > /logs/verifier/pytest.log 2>&1
python3 -B /tests/score.py --config /tests/scoring.json --junit /logs/verifier/junit.xml --report-out /logs/verifier/scoring-report.json --reward-out "$T"
mv -f "$T" "$R"; trap - ERR INT TERM HUP
