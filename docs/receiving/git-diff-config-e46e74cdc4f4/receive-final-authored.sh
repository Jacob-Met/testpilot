#!/usr/bin/env bash
set -u
baseline_root=${1:?baseline source root required}
candidate_root=${2:?candidate source root required}
receipt_root=${3:?receipt directory required}
python_bin=${4:-python3}
test_file="$candidate_root/tests/test_cli_git_diff_config.py"
printf '%s  %s\n' f31e4b275c06b1064ac6da89e7463e4647197ab9232d6df71a46fd8de162dd45 "$test_file" | sha256sum --check || exit 91
printf '%s  %s\n' 01dc85e0d4d1b0616f8c9616a6515e9e8236922c4a12ea20d47e13c5d5b85975 "$candidate_root/testpilot/__main__.py" | sha256sum --check || exit 92
[ "$(git -C "$baseline_root" rev-parse HEAD)" = 191cca4e416286a9e1fa4b5d5daf5fc30b936db6 ] || exit 93
git -C "$baseline_root" diff --exit-code -- testpilot || exit 94
mkdir -p "$receipt_root"
"$python_bin" --version
sha256sum "$baseline_root/testpilot/__main__.py" "$candidate_root/testpilot/__main__.py" "$test_file"
PYTHONPATH="$baseline_root" "$python_bin" -B "$test_file" -v > "$receipt_root/authored-original-final.log" 2>&1
baseline_status=$?
PYTHONPATH="$candidate_root" "$python_bin" -B "$test_file" -v > "$receipt_root/authored-candidate-final.log" 2>&1
candidate_status=$?
printf 'baseline_exit=%s\ncandidate_exit=%s\n' "$baseline_status" "$candidate_status"
cat "$receipt_root/authored-original-final.log"
cat "$receipt_root/authored-candidate-final.log"
[ "$baseline_status" -eq 1 ] && [ "$candidate_status" -eq 0 ]
