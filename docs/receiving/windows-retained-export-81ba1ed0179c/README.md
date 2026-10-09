# Windows retained-test review export

A Windows developer can now use the existing `export-tests` API and command to copy the final tests from a saved TestPilot report into one unused review directory. This adds a native platform capability to the earlier owner's explicitly Linux-only implementation. Exporting never executes those tests, calls a model, or changes a project.

```text
python -m testpilot export-tests --report "C:\path\saved report.json" --out "C:\path\new review"
```

The output directory must not exist; its parent must already exist. Review `export-manifest.json`, the exact original `source-report.json`, and the retained test files before using them. Historical report status is not a new execution result.

The fixed portable delivery is `TestPilot-Windows-review-export-r1.zip`: 62,274 bytes, SHA-256 `c51d50f114f79a36268d3b1c697aa99986ef282a3a271be31c88d46ed7ac8228`, 19 files. Its command uses the existing qualified `C:\Python314\python.exe`; its Python entry can instead be invoked with an existing Python 3.12 or later. No installation or global PATH change is required. The complete folder was freshly extracted into a path containing spaces and Unicode and invoked from another current directory. The full delivery/source manifest is inside the ZIP. This is a bounded exporter folder, not a complete TestPilot installation.

## Change and ownership

Released donor: `f92bf8e37b82df3ce54911001be891b54aceb40b`, tree `d15f0afbb2309b2c06e26750f5548b4c481dc62e`, from the released `estate-65ae877160f6` exporter scope. The Windows branch returns standard `os.rename` for same-parent directory publication; Windows refuses an existing destination. The Linux `renameat2(RENAME_NOREPLACE)` body and the rest of the exporter remain exact. Saved-report admission, manifest format, source hashing, temporary-stage cleanup, model, sandbox, adoption, recheck and other owners' source are unchanged.

The existing unsupported-platform test now selects an actually unsupported platform; six new Windows-specific maintained methods cover complete literal bytes, existing destinations, a late-created destination, injected prepublication write failure, invalid/missing inputs, and two actual native publishers contending for one destination. The earlier CLI parser/help text is unchanged, including its original Linux label on the `--out` help line.

## Actual qualification

- The unchanged original Windows CLI refused with exit 2 and its explicit Linux-only diagnostic; input and destination inventory remained exact. This is the original platform boundary, not a defect claim.
- All six new maintained Windows methods passed once on Python 3.14.3/MSI. The two publishers returned one success and one refusal; the complete winner was preserved with no mixed output or staging residue.
- The actual retained calc_clamp report exported through the ordinary CLI with every output byte and complete manifest checked.
- The private command exported from a fresh ZIP extraction, with spaces/Unicode and a different current directory; complete output and source bytes matched.
- Root froze independent complete expected objects before candidate exposure. Its separate native receiver passed all three groups: retained real report, synthetic mixed CRLF/CR/LF/Unicode/BOM/empty files, and portable case-collision refusal preserving the prior complete inventory.
- Author and independent Jobs exited 0 and settled without forced termination; all pinned source/interpreter inputs and resource floors passed. No exported tests were run and no model/network attempt occurred in the independent receiver's explicitly bounded audit.

Author result: `719f0f001eef4dae72b522de0d79b8eea7e63cea74e2ae203e2df7eb94fbd7d0`; outer: `80c9376d72504d8587d9ced370a3dc0b7191f850bb55134b15ae521be2f7c590`.
Independent result: `36d77c54a430884c53317f12defff2fea85bb822de87c40e210b06ff1de704c3`; outer: `fc21a99e0b448245c0d9dfbff2f9d58c5c48f71c295c7915cbeac3b54288ff4f`.

Root’s postresult source/result/package review found zero blockers for the qualified Windows scope. It reopened all nine independent expected/actual files and all 20 source projection rows, verified the exact Linux remainder, and read the portable command and requirements. Review SHA-256: `97a6b7000ba9def9cbdbd786741d4b20f5306217b3e9df8275f45eeeb07aabad`. It did not rerun the product.

## Explicit remaining limits

The planned single Linux compatibility observation is **held**: the ThinkPad failed the frozen 4 GiB available-memory admission before source import or product execution. The later read at 07:40:48 UTC observed 3,590,709,248 bytes and no output directory. No floor was reduced. Linux source preservation is verified; a new Linux runtime pass is not claimed.

The full project pytest suite, CI, network shares, hostile directory replacement and power-loss durability are not qualified by this increment. No GitHub Actions, PR, main update, merge, installation or shared security setting change was used.

The evidence index beside this guide identifies exact original/candidate source, raw streams, fixtures, the portable ZIP, frozen independent expectations and results, and resource-admission history. Durable native custody is `/srv/hamon-estate/coord/estate-81ba1ed0179c/testpilot-export-windows`; the usable Windows folder is `C:\Users\jacob\testpilot-export-windows-81ba1ed0179c\delivery`.

## Retrieve the fixed delivery and evidence

The adjacent [index.json](index.json) lists the carrier parts, byte counts and SHA-256 hashes. Join the `portable` part bytes in the listed order and base64-decode them to recover the 19-file user ZIP. The separate `evidence` carrier reconstructs the complete sealed source/receiving packet; it is not needed to use the exporter. Verify the advertised SHA-256 before extracting either archive. All source files are also directly retained on this feature branch; a PR was intentionally not opened because the repository’s PR workflow would run Actions.
