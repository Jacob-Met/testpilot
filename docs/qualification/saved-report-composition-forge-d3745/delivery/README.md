# Worked saved-report delivery

The saved-report feature is adopted at `6f0aa5d9c4394d0f104a7b8b164c5765c2529f9c` through [PR 119](https://github.com/Jacob-Met/testpilot/pull/119). Its received source is `7cbef6964dbb32518c189ad1498a031da33037ba`; both use tree `4973cf65677d8daa0e005bef20deaf43cdfac247`.

## Open the result

- [Opening and recovery guide](https://docs.google.com/document/d/19UaD2WIueF05E73jgVBCs6PjNGh33BccEg_C40KqOYk/edit).
- [Worked HTML page](https://drive.google.com/file/d/1hWv5st5DOgcrROogoqUeGvGoU5XXmfrG/view): download and open locally.
- [Reconstruction receipt](https://drive.google.com/file/d/1ZuflsBr8awL5C7OCRkf5wIUKxzDpQnaw/view).

The HTML is 39,385 bytes, SHA-256 `b70d5a30d79b56fab426ed230ff47be2b375b6f448cf8482dd0e37ea0905f674`. It contains the archived calc_clamp report and its matching patch as exact embedded downloads. The recorded `suspected_code_bug` result remains historical. Opening the page does not call a model, run saved tests or apply a patch.

From a checkout containing the adopted feature:

```sh
python -m testpilot.saved_report --report eval/results/calc_clamp/report.json --patch eval/results/calc_clamp/testpilot.patch --out calc-clamp-review.html
```

Use a new destination in an existing directory. See the [maintained guide](../../../SAVED_REPORT_REVIEW.md) for refusal and recovery behavior.

## Exact recovery provenance

The original native receiving course completed before its remote host became unavailable. Its [unchanged native receipt](../composition-receipt.json) records the page size and full SHA-256, but the page body was not exported at that time.

Root created a separate cloud delivery copy by invoking the unchanged saved-report module once, against the exact 23 current files and three donor files in [the published packet](../input-packet.json). Every source Git identity was admitted, both archived inputs were checked, and all 26 source names, bytes and modes were preserved. The result matches the original native page's recorded size and SHA-256.

[The executed reconstruction script](reconstruct.py), [receipt](reconstruction-receipt.json), [stdout](reconstruction.stdout), [empty stderr](reconstruction.stderr) and [independent review](independent-review.json) are retained unchanged here. The script is an archived execution record: it expects `input-packet.json` beside itself and a fresh directory where `source/` and the output do not already exist. The ordinary module command above is the supported consumer route.

One initial cloud transfer added a trailing newline to the packet. The packet gate refused it before source materialization or product execution; removing exactly that transport-added byte restored the original 286,528-byte packet and full SHA-256. There was then one successful rendering command.

Loom independently compared all 26 source files with the complete published tree, the output with the original native receipt, and both embedded downloads with their archived bytes. It also checked passive HTML and internal links without rendering or rerunning it. Both full Drive downloads were independently read back byte-for-byte against the accepted HTML and reconstruction receipt.

This recovery is a new matching delivery copy, not retrieval of the original native HTML. It does not replace or extend the five-command native qualification, and adds no browser, Windows, full-suite or saved-test execution claim.

## Later retrieval of the original independent review

After the native route recovered, Anvil retrieved the [original native independent review](original-native-review.json) without rerunning the consumer. Its 3,019 bytes and SHA-256 `d3b41a5a7dee878b51984d91b27c1e5eb217aab46c99c1ab87b0eb5583f8e6cf` match the identity retained in the earlier retrospective review. Both records remain unchanged and separately named. This closes that raw-review retrieval gap; it adds no product execution or browser claim.
