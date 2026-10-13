# Independent TestPilot CLI admission and explicit retry receiving

Anvil, 2026-10-13. Accepted as a preserved public-CLI admission/recovery control for [issue #103](https://github.com/Jacob-Met/testpilot/issues/103). Both the original and frozen repaired writer passed. The changed staging-failure behavior is qualified separately by Forge; this course does not claim that malformed-input admission was newly repaired.

## Authenticated inputs

Base: [ffc2590682f30c3ff23084aacb79a8f50111f273](https://github.com/Jacob-Met/testpilot/tree/ffc2590682f30c3ff23084aacb79a8f50111f273).

| Input | SHA-256 |
| --- | --- |
| Original `testpilot/recheck.py`, 12,115 bytes | `3eab07bd639994f897f76c0cd2b941d5e294c6d7c8132c82deb800e44d7079e6` |
| Frozen candidate writer, 12,770 bytes | `1b7d31f49cede49c45fe1fb0613b6e55fac292a7dece9b2645d1b55b141d95f6` |
| Independent runner, 10,329 bytes | `cc891b00dc648b4866a1c30d6cad47ea5585f19b10b1a81fe6625707b1769a25` |

The other thirteen package modules matched the original published Git blobs. All fourteen package files matched their pre-course bytes and native modes afterward. Native source files were mode 0664; no claim is made that native modes match Git checkout modes. The course was frozen after reading the original CLI, writer, guide and sandbox contract, before reading any candidate writer body. Candidate acceptance here is behavioral plus authenticated source identity; root owns production-diff review.

## Actual consequence

Each variant used three real `python -B -m testpilot recheck` subprocesses and a fresh isolated receiving directory:

1. Create a known-good neighboring report by executing one retained pytest test against an authored `add_one` project. The report contains exactly Markdown, JSON and HTML; the generated test passes and reports zero new model calls.
2. Submit a saved report with duplicate `test_files` JSON keys to a new sibling destination. The CLI returns 2, emits a duplicate-key diagnostic, writes no final destination, and executes no retained test. Neighboring output and the checked project remain unchanged.
3. Explicitly replace only the owned input file with valid bytes, then repeat the exact same CLI argument vector and destination. The CLI returns 0 and creates all three complete reports. The generated test passes. The HTML download embeds byte-for-byte the sibling JSON. The original historical status, retained test strings, and admitted source-file hash are preserved.

An owned external marker records exactly two executions, one per successful explicit CLI call. The refused call records none. Neighboring report bytes and modes remain unchanged, the project remains unchanged, tests exist only in the disposable sandbox, and the course's temporary directory is empty afterward.

| Variant | Native PID | Process result | Checks | Receipt bytes | Receipt SHA-256 |
| --- | --- | --- | --- | --- | --- |
| Original | 2986269 | exit 0 | 29 passed | 12,334 | `93efc76ac7cca17c24745560eeb095913691ebadf44791ff9fdd413800c88e75` |
| Candidate | 2987262 | exit 0 | 29 passed | 12,351 | `346efcc338d1e24b5050710caec7ea2bca5754b374c27d175ee2bedb7173d0db` |

The evidence comprises six actual CLI calls and four successful retained pytest executions in total. It does not count the 58 explicit checks as 58 distinct unit tests.

## Runtime and reproducibility

Authenticated host/account: `hamon-thinkpad`, `jacob` uid 1000, Linux, Python 3.14.4; Remote Desktop Commander route `cadafaf3-4d0b-4c4f-a0d3-34a95d2cec90`, configuration version 0.2.52. Original route `d55b2499-5e82-4805-819a-d0d7ddea1efe` rejected the read-only preflight while offline before any process launched; the verified alternate was used without duplicating an uncertain operation.

The runner supports explicit source and new working paths:

```bash
python3 -B receive-testpilot-admission-retry.py \
  --source /absolute/path/to/exact/original/source \
  --variant baseline --work /absolute/path/to/new/baseline-course

python3 -B receive-testpilot-admission-retry.py \
  --source /absolute/path/to/exact/frozen/candidate/source \
  --variant candidate --work /absolute/path/to/new/candidate-course
```

The source root contains the fourteen authenticated `testpilot/*.py` modules; Python must have pytest available. Source pins are enforced. Working paths must be new and their parents must not be symlinks. The runner uses explicit checks and create-only receipts. Successful and failed output paths, exact subprocess argv, stdout, stderr, fixture hashes, and pre/post source fingerprints are in the receipts.

Retained native stage: `/home/jacob/hamon/receiving/anvil-d3745ea0f44f-testpilot-admission-retry`. Original and candidate source roots were the read-only peer stages under `/home/jacob/hamon/receiving/forge-d3745ea0f44f-testpilot-recheck/{baseline,candidate}`.

Shared `/tmp` was full. Each CLI child used its own course-local `TMPDIR`, and both courses completed after the separately accepted owner cleanup restored home-filesystem capacity. This is a reversible process-local setting; no global service or temporary-directory policy changed.

## Evidence and limits

- [Frozen runner](receive-testpilot-admission-retry.py)
- [Original receipt](testpilot-baseline-admission-retry-receipt.json)
- [Candidate receipt](testpilot-candidate-admission-retry-receipt.json)

Both native receipt files were read back in full and transferred without reserialization; their exact byte counts and SHA-256 values match the native process outputs. The source stages, neighboring reports, checked project, fixtures and final reports remain retained.

This course uses authored local input and actual CLI/sandbox/pytest behavior. It makes no live-provider, installed-service, full-suite, optimized-mode, or operating-system network-audit claim. No model or provider call is introduced by the runner; the actual successful reports record zero new model calls. It does not inject a private writer fault, test an unserializable in-memory object through the CLI, or imply transactional rollback after a final publication move fails.
