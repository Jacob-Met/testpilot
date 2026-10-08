# Independent diff-admission receiving

This evidence-only directory preserves independent receiving of the accepted TestPilot implementation for issue #45. It changes no runtime, tests, configuration or installed service.

The received source is main `513f17454af378ee042ccd29dc930ef332a48734`, tree `ffded624f1e44bed9e10872dfb795dae2dda1a46`. PR #48, merged as `e5b7ac4a00704c0fad0c5d70da0aaafa40a722df`, supplies the hunk-validation implementation; its original source/evidence namespace is `6cc6795e89f4`. PR #49's later timeout admission is preserved. This receiving credits the incumbent implementation. Our alternate runtime was withdrawn and is retained only as historical evidence.

The unchanged independent corpus passes all 14 valid cases and 12 malformed cases, including complete target-record comparisons and 33 actual CLI invocations. Two additional CLI controls preserve an 8,192-character valid path and verify an 83-character malformed diagnostic. Automatic-run calls use receiver guards before client construction, model/provider calls, baseline tests, sandbox execution and report writing; none of those underlying operations ran. This is hunk structure/admission receiving, not a claim that every patch applies to a working tree.

`receiving-evidence.tar.gz` is the original frozen archive, published as binary without regeneration. It retains exact source snapshots, synthetic fixtures, genuine Git patches and command records, frozen expectations, raw receiving output, the original failing baseline, historical alternate v1/v2 qualifications, the separate root diagnostic counterexample, ENOSPC observations and the explicit supersession disposition. The historical alternate packet is a byte-bound nested archive. `final-convergence.json` and `receiving-readback.json` are exact copies of the sealed native receipts.

Verify and inspect the archive without extracting or changing anything:

```sh
python3 - <<'PY'
from pathlib import Path
import hashlib
import tarfile

path = Path("receiving-evidence.tar.gz")
payload = path.read_bytes()
expected = "cf63ac361e98d61a7bc3b5c043510b73fc120c01dd648338763fa1da0d0223da"
assert len(payload) == 307460
assert hashlib.sha256(payload).hexdigest() == expected
with tarfile.open(path, "r:gz") as archive:
    members = archive.getmembers()
    assert len(members) == 122
    assert all(member.isfile() for member in members)
    for member in members:
        print(member.name, member.size)
print("Verified unchanged archive:", expected)
PY
```

Ordinary archive listing is also available with `tar -tzf receiving-evidence.tar.gz`. The archive has 121 manifested files plus `receiving-manifest.json`. Separate native readback verified every file's bytes, hash and mode, and all archive members without extraction. Read the manifest before extracting into a new isolated directory.

| File | Bytes | SHA-256 |
| --- | ---: | --- |
| `receiving-evidence.tar.gz` | 307,460 | `cf63ac361e98d61a7bc3b5c043510b73fc120c01dd648338763fa1da0d0223da` |
| `final-convergence.json` | 8,283 | `998cc7d5b588cbbb2ed2ba969a087b9dbf14dd9618e3719e1214ecce13faa282` |
| `receiving-readback.json` | 930 | `0840551743500067377336ad21baac86390987893b411d3fcc7e5063bf3d3229` |

The receipts retain their original native paths and storage observations: the home filesystem filled, so supplemental evidence was sealed in isolated native `/tmp`. This directory preserves those exact bytes. No test was rerun and no frozen archive or receipt was rewritten for publication. Transport base64 is not part of the published evidence directory.
