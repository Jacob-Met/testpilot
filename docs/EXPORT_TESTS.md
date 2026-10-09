# Export retained tests for review

On Linux, turn the final retained files in a saved generation or recheck report into a new review directory:

```sh
python -m testpilot export-tests --report report.json --out review-tests
```

The output parent must already exist. Choose a name that does not exist, including as a broken symlink. The command refuses symlink parents, traversal components, and path spellings that collide under case folding. It does not overwrite or merge a directory.

The directory contains:

- The admitted top-level `test_files` at their original `tests/...` paths, encoded as UTF-8 without newline conversion. Empty files and absent final newlines are preserved.
- `source-report.json`, an exact byte copy of the admitted report, including repair rounds, rejected attempts, and other recorded metadata.
- `export-manifest.json`, with schema `testpilot.export-tests/1`, source path/SHA-256/recorded status, and sorted file paths, byte counts, and SHA-256 hashes.

Only final top-level retained files become test files. Earlier repair-round files remain available in the copied report. A historical status such as `suspected_code_bug` or `no_tests` is preserved; `exported_for_review` describes publication and does not claim that any test passes. The manifest explicitly records zero test runs and model calls. Exporting never invokes the model, runner, or project mutation.

Admission reuses the existing saved-report reader and its limits: a regular UTF-8 JSON report no larger than 16 MiB, one to 128 retained test files, and no more than 4 MiB of retained UTF-8 content. Existing schema, path, duplicate-key and type rules remain in force. Invalid input is left untouched.

Publication stages the complete directory beside its destination, checks the report hash again, then uses Linux `renameat2(RENAME_NOREPLACE)`. Concurrent attempts at the same destination have one winner; a loser cannot replace it. A prepublication refusal removes only that invocation's private stage. Unsupported operating systems or filesystems without this primitive refuse instead of falling back to an overwrite-capable rename. This is not a Windows delivery and does not promise resistance to an external malicious process changing filesystem ancestry.

A successful CLI exit is 0 with a JSON summary. Input or publication refusal is exit 2 with a JSON error on stderr and no success output. If publication succeeds but the console write fails, the valid directory remains and the diagnostic explicitly says it was published; it does not claim rollback. This publication contract is not a power-loss durability guarantee.

The Python API is `testpilot.export_tests.export_saved_tests(report_path, out_dir)`; it returns the saved manifest and raises `ExportTestsError` on refusal. Human review can happen directly in the exported directory. Applying or running those files is a separate deliberate operation.
