# TestPilot demo script (draft, not rendered)

Target: about 107 seconds at 150 words per minute, 267 words, 13 steps.
Viewport 1440 x 900. Start page: `http://localhost:4302/`, Clamp boundaries, Diff stage.

| Step | Narration | On screen |
|---|---|---|
| 1 | TestPilot helps developers check a code change. It writes tests for the functions the change touched, runs them, and reports what it found. | Clamp boundaries fixture, Diff stage, verdict headline visible. |
| 2 | This page replays two recorded runs. The first one starts with a small change to a clamp function, which keeps a number inside a range. | Same screen; "A small change to clamp()" heading and the input diff. |
| 3 | The verdict comes first. The generated tests found a real bug: the function swaps its low and high limits, so every value in range comes back as the high limit. | Red verdict: "Bug found in calc.py: clamp() swaps lo/hi ...". |
| 4 | Next, the tests TestPilot wrote for that change. | Tests tab: the planner reply and generated test file. |
| 5 | Then the run. The tests fail on the changed code. TestPilot keeps those failures, because they point at the bug. | Run tab: timeline with "Code bug suspected" and pytest output. |
| 6 | Last, the check against the fixed version of the code. The same tests pass once the limits are the right way round. | Oracle tab: "Generated tests, oracle fix: 4 pass / 0 fail". |
| 7 | The second example is harder. Here the generated tests pass, even though a bug remains. | Even-length median fixture selected, Diff stage, amber verdict. |
| 8 | The bug is in the median function. For a list with an even number of items, it returns one middle value, not the average of the two. | Diff tab: the median change in the input diff. |
| 9 | The generated tests only use odd-length lists, so they all pass. | Run tab: "Generated suite passed, boundary still untested". |
| 10 | A separate boundary check, written by hand, uses an even-length list. It fails on the same code, and passes after the fix. | Oracle tab: "Boundary witness, changed code: 1 pass / 1 fail" and "oracle fix: 2 pass / 0 fail". |
| 11 | Each result has a download for the exact patch, the case record, and the full log, so every line can be checked. | Same screen; download links at the top of the stage bar. No download is clicked. |
| 12 | Nothing here calls a model. The replies were written ahead of time, and the test runs were recorded, as the label under the verdict says. | Same screen; "Authored ScriptedModel replies ... No live model calls." line. |
| 13 | That is the whole loop: a change, generated tests, a run, and a check against the fix. | Same screen. End. |

Dry run: `demo/steps/01.png` to `demo/steps/13.png`, captured headless at 1440 x 900 with every selector matched exactly once and no page errors.
