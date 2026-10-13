# Build backend minimum: complete source receiving

The production change is exactly one line in `pyproject.toml`:

```diff
-requires = ["setuptools>=69"]
+requires = ["setuptools>=77.0.3"]
```

The minimum is the tested setuptools 77.0.3 floor listed by the
[Python Packaging User Guide](https://packaging.python.org/en/latest/guides/writing-pyproject-toml/).
No statement here implies that every earlier 77.x version was exercised.

## Current source identity

| Item | Identity |
|---|---|
| Complete original source commit | `478f68adf01658a94a3ede22526da00f580785bd` |
| Complete original tree | `ca0756e20da9c87c90ebd24c45ab494bfa31d47b` |
| Candidate source tree before guide/receiving additions | `21a7dc49a1f62e48dda05c05f5e906bed69545ab` |
| Original pyproject Git blob | `952255ac87e2c7da57457fdbf3554914f17f6d05` |
| Candidate pyproject Git blob | `9228b2ba8975f07ab59bf5a7b4cb802a81c7fc03` |
| Candidate pyproject SHA-256 | `4f1ae62c2646a81bda26187e500b1194a1f07a7212a74552f796b248b5b55d0e` |

Every one of the 1,545 current Git leaves was received with its exact bytes and
mode. Of these, 1,522 joined an existing exact source snapshot and 23 were fetched
as complete current GitHub file bodies. The ordinary public Git fetch had first
timed out without receiving objects; that attempt is retained in the archive.
The complete connected tree reconstruction then succeeded. No selected-input
assumption was used for the final build source.

Only `pyproject.toml` differs among the 1,545 inherited source files. All 1,544
other leaves remain exact, including the current comparison modules, CLI, README,
tests and their separate receiving records. The guide and this receiving
directory are later inert documentation/evidence additions outside the declared
`testpilot` package and root license-file set.

## Complete-source original/candidate build pair

The new `receive_full_build.py` was frozen before the first full-source build at
`2026-10-13T00:56:04.018783+00:00`, SHA-256
`9d8ee0b592ffa1ad6beb848c4e2c87735796b741599fac6f2b3dd8c0a8db67a5`.
It checks the complete Git inventory, copies the full source into a fresh owned
build directory, and invokes pip's actual default build isolation with the single
pinned offline setuptools 77.0.3 wheel. It runs no product import, test suite,
installed CLI, provider, native device or workflow.

| Complete source | Actual result | Finished UTC |
|---|---|---|
| Original `setuptools>=69` | Exit 0; complete wheel accepted | `2026-10-13T00:56:06.425373+00:00` |
| Candidate `setuptools>=77.0.3` | Exit 0; complete wheel identical | `2026-10-13T00:58:46.163493+00:00` |

Both builds produced `testpilot-0.1.0-py3-none-any.whl`, 75,408 bytes, SHA-256
`3c349ebcbaa48f644bb1b8a6a04efc89da3b1e21105d93581ca6c6a2f5e6c90c`.
The entire wheel bytes match, and all 21 member bodies are received. They include
the fourteen exact current modules, the unchanged console entry point and
metadata, and both license files:

| License file | Bytes | SHA-256 |
|---|---:|---|
| `LICENSE` | 11,350 | `bd6ce0dba75b72f0a6827701d7a4b8e8f1e7eaf45b20c21270739fa4f48dfac5` |
| `NOTICE` | 124 | `4564e24959bca812ed0fa34d42786012dddbed523c02dd1bb5bdf424262be344` |

Wheel metadata names both license files. All 1,545 original input bytes and
modification times, and every inherited build-copy file body, remain unchanged.
The supported backend wheel is 1,255,678 bytes, SHA-256
`67122e78221da5cf550ddd04cf8742c8fe12094483749a792d56cd669d6cf58c`.
The actual frontend is Python 3.12.14 / pip 26.2.1. Fixed SOURCE_DATE_EPOCH permits
the whole-wheel byte comparison; this is not a timing benchmark.

## Preserved initial finding and scope correction

The first four-build campaign used source parent
`e222894c095e16aff19413e6e3f8a2b6201a059a`, with twelve modules and three selected
metadata files. Its frozen receiver, SHA-256
`e2c456eb9ea09e4ed17632896ed89f5836cf7fb47fa34f0affd0cf2d2f7aaa8b`, omitted the
existing `NOTICE`. The original receiver, expectations, raw logs, receipts and
63,303-byte reduced-fixture wheel are retained unchanged. References to complete
wheel equality in that original record describe the complete reduced-fixture
wheel; they do not establish complete repository package preservation.

| Initial fixture | Available backend | Actual outcome |
|---|---|---|
| Original `>=69` | 69.0.0 only | Backend installed; existing license schema rejected; no wheel |
| Original `>=69` | 77.0.3 only | Reduced-fixture wheel built |
| Candidate `>=77.0.3` | 69.0.0 only | Backend requirement refused before license validation; no wheel |
| Candidate `>=77.0.3` | 77.0.3 only | Same reduced-fixture wheel built |

The independent review at SHA-256
`09284c423b71529b362d2e072c4068784b6644db27d2003e62703f4d84cef4a7`
accepted the production line and requested the NOTICE qualification correction.
It is preserved verbatim as `original-notice-finding.json`. The later full-source
build pair and independent review close that specific evidence finding. Neither
the initial fixture nor its expected outcomes was rewritten after review.

Initial setup also retained a failed storage attempt and a failed dependency
acquisition without the ordinary inherited transport. Corrected ordinary PyPI
acquisition succeeded, and all actual builds subsequently used offline depots.
The later full-source Git acquisition timeout is retained separately. These
setup events do not count as product build outcomes.

## Independent source and record receiving

`independent-full-source-review.json`, 3,836 bytes, SHA-256
`c8a6647b56453f053c95d255f2ac417d597bff719171446c777b3b6b65d35d22`, accepts the
complete-source correction. The independent runtime worker recomputed both Git
trees from all 1,545 physical file bodies and modes, verified the sole pyproject
change, joined both actual isolated build receipts and four raw logs, and checked
all 21 wheel members and RECORD hashes. It also freshly received the unchanged
initial 56-member archive, both old receiver copies and the original NOTICE
finding. The reviewer performed no build replay, product import or source edit.

## Retained artifacts and reproduction

| Artifact | Bytes | SHA-256 |
|---|---:|---|
| Initial four-build archive, 56 members | 185,368 | `8ee8402375d4a7f99abfdd3237bfaed941901c129c9da368a7c3dd8626a633b8` |
| Complete-source build archive, 60 members | 519,972 | `1e117c75d6e3a4389072cbb4f151e28b2d8a54468e689af04e3cf050574772de` |
| Full-source original receipt | 7,866 | `fe9a844969b45c7ea41596f340702ac631882278f97e6b9dba2894665cf2005c` |
| Full-source candidate receipt | 7,923 | `d6295f53f3f2ba81e3cd093b94c2961a195e5d48334ccbb90d8a5e89f6255269` |

Both archives were reopened and every member compared with its source bytes.
The full-source archive contains both full input manifests, the complete parent
Git inventory, actual raw outputs, the frozen receiver and expectations, one
byte-identical qualified wheel, and small package-source inspection copies. The
full 1,545-file source is identified by the retained parent tree and manifests;
the inspection copies are not the source selection used by the full builds.
Third-party backend wheels are not embedded; their exact ordinary acquisition
record and hashes are retained.

For reproduction, export the complete pinned parent with `git archive` into two
fresh source directories, apply only the shown requires-line change to the
candidate, and use the archived `source-tree.json`. Supply a backend directory
containing exactly the pinned 77.0.3 wheel. Run the frozen receiver first with
`--phase original`, then with `--phase candidate --original-receipt` pointing to
the newly created original receipt. Use separate fresh `--out` directories; the
receiver itself makes complete private build copies. The source directories must
contain exactly the archived Git leaf inventory.

This record qualifies the build backend correction and package-byte
preservation. It does not replay runtime suites or add a native source-build
claim. The separately received Windows API and installed CLI results remain
pinned to their own 067cf459 and a1fb8acc source offers.
