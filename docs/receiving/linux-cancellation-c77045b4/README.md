# Additional native Linux receiving for TestPilot PR43

Accepted source boundary: complete published sandbox module from head95a3116c175debdf97fd9dc1c984a587a90a5d3b, blob84330f96ebd71b37dc40575fa2ac59ba53cf2a72, SHA2560adf5eb81f8fd15ca09170c5328e6ff4165e1a0f903221b9730de3b480be0b1b. Removing only its interrupt handler and restoring the original docstring reconstructs the current cec50d8df4499ba509615e179d82ef3861379bd2 sandbox byte for byte. This selected standard-library module is not a complete repository checkout.

The independently authored Linux receiver exercises actual processes and SIGINT, with a work barrier released only after the runner has exited. Baseline ordinary output/exit control passes. Its same-group leader and descendant remain active after cancellation and both write post-exit markers. Its escaped-session case also leaves the leader doing work.

All three candidate groups pass. Ordinary output and nonzero exit are preserved. Same-group cancellation returns with both work processes inactive and no later markers. A deliberately detached child remains active at parent exit, as expected outside the group boundary, then exits naturally after the receiver releases it; the killed leader writes no marker. Both cancellation returns take about0.314 seconds on this run. Four prior-output sentinels preserve bytes, inode, mode and write timestamps. The receiver needed no cleanup signals. Native Python3.14/Linux qualification does not substitute for full CLI, provider, Windows or complete-suite receiving.

The normative contract was authored before source retrieval, but the first native mkdir failed with ENOSPC. Source transport completed after that failed write. The original unchanged contract and this sequence are retained; no preinspection native Git freeze is claimed. The receiver source was committed with exact inputs before execution. Own helpers have finite deadlines and record PID, process group, session and Linux start ticks.

## Remaining hosted integration gate

Existing PR43 hosted job113460074077 on c49cd45f805d9c8e998bb0f3a3bf06593296eee7 failed2 tests, passed397 tests and25 subtests. Both failures are authored escaped-child liveness assertions. This failure remains a gate for the original owner and is not overridden by this narrower native result.

After accepting the independent matrix, a separate own-process probe investigated the authored ps command observer. On this ThinkPad, both normal and wide ps output contain the full long fixture path, so output truncation was not reproduced and the hosted cause remains unestablished. Exact authored test and full hosted log are retained for owner diagnosis. No product or authored test was changed; the accepted process matrix was not repeated.

Original estate18a24bf0c281 retains source authorship, current-parent composition and integration. This contribution supplies additional Linux receiving and an explicit unresolved CI handoff. No source, shared branch, runtime, service or provider was changed.

Replay in a fresh copy, since the receiver deliberately refuses existing run directories:
python3 -B receiver.py
