# Comparison source downloads: authored qualification

The product candidate is `941c81c710e2742498fa3748a939434420b89fb2`, tree `8b922ca6b3c6f44ff92ff70d44d13da9df6962b4`, on original main `3441b6a2e708977ebfc75400d795501f357f656c`. This is a source preparation checkpoint. Independent browser receiving is a separate qualification and remains pending here.

## Change and custody

Only `testpilot/compare_html.py`, `docs/COMPARE.md` and the new `tests/test_compare_generated_downloads.py` change. All 2,009 other terminal entries retain their original mode, type and Git identity; the candidate has 2,012 terminal entries with no removals. Removing the new `_generated_downloads` definition and its single call restores original renderer `0fd6c65058fd847342633a28fe6c8c8157b8cfc5` byte for byte. The reader, ordinary comparison command, history code, diagnostic index and original JSON construction remain unchanged.

The two source packets each contain the same sixteen-module normal CLI closure. Only the candidate renderer differs. The original copy also contains the authored new test as a deliberately added observation instrument; that test is not claimed to exist on original main.

## Actual authored courses

Both courses ran on local Python 3.12.14 using the standard-library command recorded in their receipts:

```sh
python -B -m unittest discover -s tests -p test_compare_generated_downloads.py -v
```

The original course selected seven methods: two existing-behavior controls passed and five assertions failed because the original page has no per-side source-download controls. Its test child returned 1. The candidate selected the same seven methods and all passed; its test child returned 0. Each course includes one ordinary `python -B -m testpilot compare` subprocess, whose retained source strings are data only. No generated source or provider is executed.

`author-original-v1/` and `author-candidate-v1/` preserve their separate actual receipts and stdout/stderr bytes. The receipts contain the exact command, Python runtime and complete source inventories before and after execution, including modes, nanosecond mtimes and inode witnesses. Both complete inventories match. The capture wrappers were inline local Python commands; no separately saved executable wrapper is represented as their executed observer.

The installed local runtime did not include pytest. The inherited pytest suites were not run, replaced or emulated. Their unchanged source is available for review, and this checkpoint makes no new claim about them. The new focused methods are maintained standard-library tests.

## Bounds

These methods cover strict UTF-8 source bytes, recorded leading U+FEFF, empty strings, absent sides, unpaired-surrogate refusal per side, literal paths, long/control/newline text, fixed role/index filenames, unchanged original JSON bytes and the ordinary comparison CLI. Browser-native download behavior, keyboard interaction, narrow layouts and print behavior require the separately owned independent receiving course. No hosted application or existing user report was modified.
