# Isolated native TestPilot wheel receiving

The exact corrected v2 kit was installed and received in a new, separate ThinkPad
environment on 2026-10-13. The application and original calc_clamp sample remain
unchanged from commit d2596c1a4be11072344c4ea98752cce789865ec4, tree
3b6d270f655310fa2f98cab9bccffca23ec146cf.

## Actual result

Host hamon-thinkpad ran /usr/bin/python3 3.14.4 as jacob (UID 1000), with existing
system pytest 9.0.2. A new venv using --system-site-packages installed the exact
wheel through pip --no-index --no-deps. All 14 installed modules match the pinned
source and wheel, and their import location is inside the new environment.

| Actual child command | Exit |
| --- | ---: |
| Create new venv | 0 |
| Read available pytest version | 0 |
| Install local wheel | 0 |
| Inspect installed module identity | 0 |
| Show TestPilot help | 0 |
| Preview calc_clamp targets | 0 |
| Run original scripted calc_clamp example | 1 (expected) |

The final run reports suspected_code_bug, three failed and three passed tests,
and four generated cases. It selects only clamp and writes report.html,
report.md, report.json and testpilot.patch. The failing implementation remains
visible: this is successful receiving of an intentionally failing example,
not a passing repair. All 31 extracted kit files retain their exact bytes,
modification times, modes and inodes. The native target preview and generated
patch are byte-identical to the cloud run; report timing values differ.

Controller PID 3138406 completed with exit 0 after collecting all seven child
PIDs. That controller result is separate from the scripted child's expected
exit 1. Seven recorded receiving checks pass. The independent custody review
recomputed all artifact, input, module, stdout/stderr and report bindings and
inspected the raw routed start/completion records; it did not rerun the program.

## Exact evidence and correction history

- Kit v2: 107,866 bytes; SHA256 8b3c856751ae9bd24b74474b68624e38e97d9157429aafc6c9d671676be00a4d.
- Wheel: 75,206 bytes; SHA256 c471d961e1b26051209b2d8bdcf0629b1f0185b25ae6c0d0d733bacca344d246.
- Corrected native export: 26,147 bytes; SHA256 7abfc681176fbba84c70395d67941b5a6bec2453c7c4fa03a075ade8a261eadb; 23 members, 22 manifest payloads.
- Native receipt: SHA256 198b0697dcf56df48823614286b98285115d4edadc64df3b5be89bd98e17db94.
- Routed custody: SHA256 0218001efe808999f9a70f345a7be5db17dd8e5f562069d9079ae7cadfebc8da.

The first native export ended two metadata files with a literal backslash-n.
Readback caught the invalid JSON. Only their serialization was corrected;
application execution and its receipt were unchanged. staging-first-write.txt
and first-export-manifest.txt preserve both original metadata files. The
complete companion also preserves the original export ZIP. This export error
is separate from the earlier kit v1 source-tree labeling correction described
in the parent README. Both failed attempts remain inspectable.

receive_native.py is the archived controller with its original absolute paths,
not a portable installer. Use the parent START_HERE.md for the supported sample
commands. This evidence qualifies an isolated installed wheel on native Linux.
It does not adopt an existing estate installation, validate browser appearance,
exercise a live model/provider, qualify Windows/macOS, or rerun the full suite.
