# Offline saved-test recheck receiving

This packet qualifies the six-path implementation for issue #37. The page consumes the exact newly serialized `testpilot.recheck/1` result. It does not rerun tests or generation, load project files, apply retained tests, or fetch external resources.

## Source and author evidence

The original baseline is `7f44c4f134f4d56d37dd14c7c2d2aaa3c8c8749e`. The six contribution blobs and unchanged dependency closure are recorded in `source-publication.json`. `author-evidence.tar.gz` (45,455 bytes, SHA-256 `a72042ef969dbacfe75cef7d42330f17056cd73003022a5ead54ccebdad5bff8`) contains original and candidate changed source, exact receiving diffs, the author receipt and a nested original native baseline packet. Archive source files are evidence; normal tests are the repository's `tests/` files.

The original native baseline driver runs actual saved-test rechecks against an authored buggy and corrected Python project. The buggy result has three passed and two failed selected-suite cases; the corrected result has five passed. Both have four collected retained cases and zero model calls. It preserves the exact JSON and Markdown artifacts, authored inputs and command output; the original implementation produces no HTML. This is an authored saved-input fixture, not provenance from a model-generated test run.

The candidate's final native gate passes all 44 focused and existing recheck tests. It includes real buggy/fixed CLI execution, original JSON/Markdown serialization-byte equality, literal fields and exact raw JSON recovery, missing JUnit, timeout, no-tests, and visible control/surrogate rendering. A real POSIX file-size limit makes only HTML delivery fail after a passing recheck: native result remains `ok: true`, the command returns exit 2 with no success stdout, and partial output is not presented as completed delivery. Existing output-directory exclusivity and partial-delivery limits remain.

The writer's narrow diff leaves all eleven other recheck function/class AST bodies unchanged. The existing recheck test file changes only its expected output filename set from two artifacts to three. CLI, sandbox, model, collector, selection, generation writer and workflow source are inherited unchanged.

## Evidence limits

The 44-test gate is the selected native recheck suite, not a claim that the full hosted suite ran. Temporary shared-storage capacity stops during metadata/archive retention are preserved separately in the author receipt; no product test failed in those stops. Original JSON/Markdown bytes stay exact. HTML cannot represent every control/surrogate as a literal text node, so the reading view shows explicit escapes while the downloadable JSON bytes retain the original representation.

Independent browser/source receiving and the actual native hosted/integration results are recorded separately when complete.
