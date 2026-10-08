# Receiving the report writer with PR20's module allocator

The HTML report was independently received before PR20 integrated generated
pytest module-name reservation. PR20 changes a different section of the shared
`testpilot/loop.py` file and adds one README design-choice bullet. This bounded
supplement preserves that current allocator and qualifies the HTML output with
its resolved filenames, warnings, local fixtures, and partial repair aliases.

## Exact composition

| Boundary | Identity |
| --- | --- |
| Canonical receiving parent | `269e55332a9bb78a0a0e107cbab6b2e5c895ca57` |
| Canonical receiving tree | `2045a73704f752d374704657fccf90fd5e774258` |
| Complete 80-file manifest SHA256 | `510f4dc179c71970444e4e97389272b763b1ce3b1f6229d86e13c6a08769b29a` |
| Composed loop SHA256 | `cdbe364296b8a81ea852a5c70f757db894e52cb9a66db9cc9a6f60b4569d3539` |
| Composed README SHA256 | `a75d56db555f787886056157c9d07d625ab18c5f06299561ae9889f3610efe00` |
| Native archive SHA256 | `8f480e0b9edb7bfa29c4e75bbcf8f5298e9d735fdc3ca0a65205dd6b3bb0670a` |

Removing only the previously accepted HTML import, output key, and write call
reconstructs the current parent loop byte for byte. Removing the unchanged
HTML README section reconstructs the current parent README byte for byte.
The renderer, 19 focused tests, and two original capture drivers remain
identical to the independently received `fe791af1` projection. Every one of
the other 74 execution-file blobs matches the canonical current tree.

The original author archive and six-file independent packet are unchanged.
Their original baseline/candidate identities and the earlier `dc9735cb`
composition remain explicit. This supplement does not relabel those original
runs as executions of PR20 source.

## Focused native behavior

The existing 19 HTML tests pass with the composed loop. Two additional actual
CLI invocations use authored ScriptedModel replies, real pytest/coverage, and
disposable Git projects. They preserve an existing `legacy/test_calc.py` and
request generated `test_calc.py` files in two directories with different local
fixtures. The current allocator resolves them to:

- `tests/unit/test_calc_testpilot.py`
- `tests/integration/test_calc_testpilot_2.py`

Both runs finish with three total passing tests, of which two are generated.
The repair case initially fails the unit assertion, then updates it through
the original suggested name `tests/unit/test_calc.py`. The other generated
file survives that partial repair. The report retains the initial failed
source/result, final corrected source, resolved names, and literal mapping
warnings. All nonempty patches pass `git apply --check`; the input repositories
and all 80 execution-source files remain unchanged.

The CLI fixture is an explicit derivative of the original nine-case author
driver, specialized for this current allocator boundary. The original browser
driver is unchanged. It passes all **39 checks** on these two detached reports,
including four actual JSON/patch downloads, rendered final source and case
identities, keyboard navigation, narrow-screen tables, an actual print PDF,
and an offline JavaScript-disabled context. No application exceptions,
browser console errors, or external requests were observed.

These are author compatibility checks. The independent review separately
verifies canonical source preservation and the saved two-case evidence; its
own receipt is retained alongside this packet. No broad seven-case independent
rerun, full native suite rerun, provider call, or installed-runtime activation
is claimed by this supplement.

## Preserved evidence and storage boundary

`pr20-native.tar.xz` has 134 ordinary members. `native-manifest.json` lists the
other 133 artifacts, including the full current source projection, canonical
parent loop/README, complete current tree leaf listing, fixtures, outputs,
drivers, command receipts, screenshots, PDF, and source/environment records.

An initial attempt to write the new native command wrapper encountered
`ENOSPC`; its attempted invocation therefore reported `ENOENT`, and no product
qualification ran. The setup failure is preserved in
`native-storage-block.json`. Only this worker's already integrated,
reproducible Suite build dependencies were reclaimed. All source, lockfiles,
bundles, evidence, and 179 retained Playwright/dependency files stayed intact.
The subsequent successful native invocation is the one recorded here.

During archive transfer, a shell here-document also needed temporary disk
space. The same normal read route was continued with a small `python -c`
command that reads the already frozen archive without creating a shell
temporary file. Whole-archive identity, all members, and all artifact hashes
were verified after transfer. This did not change source, evidence, execution
criteria, transport, or access authority.

Run the saved-evidence verifier from the published layout:

```sh
python3 -B docs/receiving/html-report-066deeadcc8b/current-composition/verify_composition.py
```

It must reproduce `verification.json` exactly. It also reads the adjacent
original author archive to verify the unchanged README insertion and four
frozen source files. It verifies saved observations rather than executing
product code or a browser again.
