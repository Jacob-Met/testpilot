# Complete process identity in cancellation receiving

PR43's first hosted job failed only the escaped-child liveness assertion. This packet adds `-ww` to the `ps` argument list in `tests/test_sandbox_interrupt.py`, with one explanatory comment. The full worker-path match,zombie refusal,process-group guards,finite workers,reaping assertions and elapsed-time bounds remain unchanged. Production sandbox stays blob `84330f96ebd71b37dc40575fa2ac59ba53cf2a72`.

Native source commit `7e58c46ff7222608703929568bf453576f418b6c` freezes the7,024-byte test blob `35a8152aa41be8aafffcc1f5713bedbf2abd7533`, SHA256 `e43719dc30472dd3e9ff8b829b61a7d743de20974ca4991aa131c12014ab4818`. Removing the comment and argument reproduces original `184e969e57fc2a483b6a4e7b1709e16f66ce37e6` exactly. The parsed AST changes only that argument.

| Phase | Actual result |
| --- | --- |
| Standalone original oracle,short and long owned paths | Both live processes correctly identified; retained non-reproduction. |
| Exact public four-case test under native pytest | Two same-group controls pass;both escaped-session cases fail only child_running. |
| Observation-only original pytest run | Sixteen ps calls retained;eight live-child observations show81 bytes cut at80 columns,while -ww returns246 bytes including the full worker path. |
| One-argument candidate,observer absent | All four existing process cases pass. |

The observer returns every original subprocess result unchanged. Stable /proc command-line,start identity,state,group and session are retained before/after. The observed pytest descriptors have no terminal and COLUMNS is unset. Original red and complete diagnostic were frozen before correction. The passing standalone control prevents a claim that all GNU ps invocations truncate.

Native receiving uses Python3.14.4,pytest9.0.2 and procps-ng4.0.4 on the named ThinkPad. Candidate tests use the same twelve exact original source/context inputs through an explicit PYTHONPATH;only the test differs. All original and candidate bytes remain unchanged before/after. No runtime or dependency was installed.

The failed hosted job113460074077/run37820525113 checked out `c49cd45f805d9c8e998bb0f3a3bf06593296eee7`, tree `90122828c9c577c4fde436807c933b9899d8abe0`, parents `cec50d8df4499ba509615e179d82ef3861379bd2` and `95a3116c175debdf97fd9dc1c984a587a90a5d3b`. Its complete20,002-byte decoded log matches root's independent SHA256 `7563982662d40069caadd14a04d382836d25d70cab0cf1cc7050c5474f321068`. It reports397 passed,25 passed subtests,and two failures,but has no raw hosted ps trace. The native reproduction establishes the defect;a new hosted checkout still must pass.

The first packaging write failed with ENOSPC and left a zero-byte recipe that was never executed. That error is retained. The final archive and packet were instead assembled and verified in memory without cleanup,new filesystem writes or reruns. The source commit and raw native receipts remain authoritative;no final native evidence commit is claimed.

Native root: `/var/tmp/tp-18a24bf0c281-ps`, device `d55b2499-5e82-4805-819a-d0d7ddea1efe`. The archive retains all selected original sources,receivers,raw logs and focused fixture artifacts,plus the packaging failure. MEMBER-MANIFEST.json binds every other member by bytes,SHA256 and Git blob;every member was read back from the finished archive and verified. Prior harmless missing-rg and missing-new-directory setup errors remain separate from product failures. Native commits are selected-source custody,not upstream ancestry.

The five publication paths are one test replacement plus this review,qualification JSON,the evidence archive and the complete test-only diff. Root retains publication and merge authority.
