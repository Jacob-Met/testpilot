# Final CLI receiving: 63174afd

This addendum preserves the original e1d87442 author packet and the separate e2285d68 raw-diff gate. It qualifies comparison alongside merged PR #28 recheck on exact main 63174afd8e63a0ea562cf188b7d971522f017a30, tree cea947d9aeb2253466593044889a1bb548f8b7c4.

The complete nontruncated tree contains 1,334 entries. The incoming CLI, recheck module, sandbox, inherited recheck tests and guide were fetched at that exact commit and Git-blob verified. The receiving copy starts from these bytes. It inserts only the original comparison parser and early dispatch; removing those two additions reconstructs the complete incoming CLI, including the shared raw-diff loader, the recheck import/parser/dispatch, and existing run/targets behavior. The other six comparison contribution files, including README, remain unchanged from the original frozen source.

| Item | Evidence |
|---|---|
| Final CLI | 6,859 bytes; Git blob 1aedb4f7e4be08f275be9a50dcca454cf95f02a3 |
| Final CLI SHA256 | a9cd128e5a31aec3616c4a49f4aa25744f21af472ae683d877baa9c5a080e613 |
| 35-file source manifest SHA256 | 4bcdb3f6773673f19dbf6b93de0eb2cf0a4e61df108829a171a01185419ba1eb |
| Coexistence receipt SHA256 | bf15061af5a038f41fd5830108e154bbf8049fe417507fe1b5ed1491d44eb07c |
| Source preservation | All 28 inherited current files exact; original 31 and prior 32 source hashes unchanged |
| Focused tests | 5 passed in 1.87 seconds |
| Complete receiving driver | 6 successful receipt groups across 6 command processes |

The focused tests combine the two new comparison CLI cases with the unchanged owner's real reusable-recheck command test and both early output-admission cases.

The native command checks then:

1. Compare the original real bug/fix generation reports and require the exact frozen 48,157-byte HTML.
2. Recheck the saved buggy-run tests against the maintained fixed checkout. The current result has six suite passes, four retained generated passes, zero model calls, exact test contents, and the original report SHA256.
3. Refuse that distinct testpilot.recheck/1 result as a comparison input, creating no HTML and preserving the result bytes. This supported-schema boundary remains explicit.
4. Retain all four command names in help and run targets against the maintained raw diff.
5. Verify both original reports and the fixed project remain byte-identical.

An intentionally invalid provider setting remains active for the actual comparison/recheck/preview commands. No model construction occurs. No generation, collector, recheck schema, shared raw-diff semantics, or output behavior was changed to make this gate pass.

The parent independent receiver owns the final one-pair verification against these source bytes and all external publication. This receipt does not replace its independent reports or the earlier historical pins.
