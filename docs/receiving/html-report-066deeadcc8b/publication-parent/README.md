# Final publication parent

This source-only composition preserves canonical TestPilot main
`3e745e6b6a2f7e383fc6b43f12e69f7a221fb051`, tree
`56b8c198f3d88e133c6d641b0cc7c63de0dd6fcd`, with 728 ordinary blob leaves.
It follows the independently accepted native PR20 composition at
`269e55332a9bb78a0a0e107cbab6b2e5c895ca57`; that prior packet and its original
source identities remain unchanged in the sibling `current-composition/`.

## Preserved upstream behavior

Between those parents, PR21 gives coverage reporting a fresh temporary output
destination, accepts complete reports from coverage exit statuses 0 and 2,
and keeps absent or failed reporting unavailable. PR10 handles response-body
timeouts within the existing model retry budget and preserves a terminal HTTP
error when its diagnostic body times out. Both canonical files remain parent
leaves: this report overlay does not modify `testpilot/model.py` or
`testpilot/sandbox.py`.

The only upstream difference inside the shared loop is a Markdown message:
`Coverage: unavailable` replaces the earlier installation suggestion. Applying
exactly that inherited change to the last qualified loop produces the final
loop SHA256
`41506f3c29febd3b10c4dce43f7f8e0695c32885ddc08e56e1c96d5bb2f212a4`.
Removing the original three HTML additions reconstructs the latest canonical
loop byte for byte. All 22 other top-level definitions remain identical,
including the result and round schemas, pipeline, allocator use, and writer.

The README remains at the prior accepted composed SHA256
`a75d56db555f787886056157c9d07d625ab18c5f06299561ae9889f3610efe00`.
Removing its original HTML usage section reconstructs current canonical
README bytes. The renderer, focused tests, and two capture drivers remain at
their original independently reviewed source hashes.

`source-manifest.json` records the six proposed source files, exact upstream
files, and precise inherited production patches. `current-tree-blobs.json`
preserves the complete parent leaf listing. The `proposed/` and `upstream/`
directories make the reconstruction directly inspectable; they are evidence
copies and are not extra application entry points.

## Verification boundary

Run the standard-library source verifier from this directory or provide this
directory as its optional argument:

```sh
python3 -B verify_publication_parent.py
```

Keep the sibling `current-composition/pr20-native.tar.xz` at its documented
location. The output must match `verification.json`. The verifier checks the
canonical Git blobs, exact source hashes, current-loop reconstruction, the
previously qualified source archive, and the unchanged HTML additions.

**No new native product invocation was made on this final parent.** Original
77-file receiving, the 79-file compatibility run, and the 80-file allocator
run retain their separate identities. The final source combines their accepted
HTML feature with these canonical upstream changes; the exact PR head's hosted
checks are the final integration gate. Publication and integration receipts
record that head and the actual check outcomes rather than treating this
source-only reconstruction as a runtime test.
