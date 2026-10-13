# Import the pinned fanout receiving bundle

`import_fanout_bundle.py` replaces the manual shallow-bundle import for this receiving example. It accepts only the exact `fanout-pair.bundle` supplied with the native packet, creates a new local worktree, and verifies the source before it reports success. It uses Python's standard library and the installed Git; it does not fetch, install anything, or run project tests.

The accepted input is 353,498 bytes with SHA-256 `c018ae94ddb33d6ebaaeac84d82f1af9f5f05db170e60af08a585c3ddea742c0`. The original checkout was shallow at `0317b4bc80638a8e952857aa5966b0e20d1fab72`. The helper preserves that boundary and detaches the new worktree at `522c40bd3f40359d598b62cf2947d74b14c20a31`. It does not reconstruct or claim history before the declared boundary.

## Use the existing packet

Keep the original packet and its evidence intact. Point the helper at its extracted `inputs/fanout-pair.bundle` and choose a new output directory whose parent already exists:

```sh
fanout_receiving_bundle='/absolute/extracted/inputs/fanout-pair.bundle'
fanout_import_output='/absolute/path/to/new-fanout-import'

python3 -B /absolute/path/to/import_fanout_bundle.py \
  --bundle "$fanout_receiving_bundle" \
  --output "$fanout_import_output"
```

On exit 0, `IMPORT.json` contains `accepted: true`, both raw commit/tree identities and the verified manifest of all 116 files in `worktree/`. Pass that worktree to the already qualified receiving wrapper:

```sh
python3 -B /absolute/extracted/inputs/receive.py \
  --testpilot-source /absolute/extracted/inputs/selected-testpilot \
  --fanout "$fanout_import_output/worktree" \
  --python /absolute/path/to/python3 \
  --output /absolute/path/to/new-regression-result
```

The second command is the actual TestPilot regression course. Importing the bundle alone does not execute or establish a new regression result. The original completed course remains separately pinned to its source, environment and archive.

## What the importer verifies

The helper reads a bounded number of bytes and checks the exact bundle size and hash before it creates output. It rejects a linked input, an existing output, and a missing output parent. It copies the verified bytes into the new output as `source.bundle`, so Git consumes the captured input rather than rereading a potentially changing external file.

It initializes a fresh worktree with an empty Git template, disables inherited Git configuration and replacement/lazy-fetch behavior, and disables hooks for its own Git operations. It declares the original shallow boundary, unbundles the captured source, checks out the exact after commit and runs Git fsck. Both raw commits are rehashed; their first tree lines must match the recorded trees. Every checked-out source file is then matched to its Git blob and executable mode. The complete 116-file inventory must total 1,149,457 bytes, and the final worktree must be clean with the expected detached head and unchanged shallow boundary.

This is a receiver for one reviewed packet, not a general Git dependency resolver or importer for arbitrary bundles. An installed Git must support `--no-lazy-fetch`; the original receiving environment used Git 2.53.0. A normal existing checkout that already contains both exact commits can continue to be used directly with `receive.py`.

## Failure and evidence

Input-admission failures return exit 2 before creating the requested output. A failure after output creation returns exit 1 and retains the new directory. `operations/` contains the exact Git commands, their working directories, return codes, timeouts and binary stdout/stderr. A Git timeout has a null return code and preserves any partial output. Each Git operation has a 40-second deadline.

`IMPORT.json` records `accepted: false` and the error when an import does not finish. If the filesystem cannot accept the final receipt, the helper reports that failure on stderr and returns 1; it does not remove the partial output. Inspect preserved failures before choosing a different new output path. The helper never reuses or replaces an existing checkout.

The input bundle, the original regression results and other estate worktrees are not modified by the importer. Qualification records distinguish the local refusal/timeout probes from any completed native import. Project tests, model requests and provider integrations remain outside the import step.

## Completed qualification

This is an additive companion to the six-file receiving example in [PR101](https://github.com/Jacob-Met/testpilot/pull/101), accepted at `ffc2590682f30c3ff23084aacb79a8f50111f273`. Those six files remain unchanged. The companion consists of this guide, the importer and `IMPORT-QUALIFICATION.json`.

The frozen 8,740-byte helper has SHA-256 `8a565da0666f26c0e0a072b092553d759797cc1a0ec70f7befd4f8a101abc554`. One import-only run on hamon-thinkpad, Python 3.14.4 and Git 2.53.0 completed with exit 0. All nine Git operations completed without timeout. An independent check compared every one of the 116 checked-out files, all executable modes and both raw commits with the original Git objects; the source total was 1,149,457 bytes. The earlier checkout, its index and the original regression evidence remained unchanged. No TestPilot or project test course was repeated.

Six separate local controlled probes covered size/hash refusal, linked input, missing output parent, existing-output preservation and timeout evidence. They launched no actual Git process; the timeout was deliberately injected and retained binary partial output plus a false receipt. These failure probes are distinct from the completed native import.

The sealed native archive is `testpilot-import-helper-native.tar.gz`, 26,309 bytes, SHA-256 `ed06367c36d9192a62cdc6382b953329f68f00069c9077b710c83451370055c4`. Its 25 payloads retain the helper, preflight, exact operations, complete import receipt and independent verification. The archive does not duplicate the bundle or checkout: the original 493,079-byte regression packet already retains the exact bundle. `IMPORT-QUALIFICATION.json` records the corresponding pins and scope.
