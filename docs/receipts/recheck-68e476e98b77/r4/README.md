# R4: preserve accepted raw diff input and saved-test recheck

Current receiving parent: `e2285d68b2ea5eb2158c0a7e0d936ce5d56f8ff5`, full tree `22da6a890c2befaf72d3826103538491b07793df`. This receives PR27's raw Git/file/stdin diff loader after the original recheck publication.

Only `testpilot/__main__.py` changes among our five product files. Its recheck import, parser arguments and early dispatch are byte-identical to R3. Removing those three additions reproduces the entire incoming CLI byte-for-byte. The accepted `_read_diff`, `_preview_targets` and interpreter resolver are preserved exactly; recheck returns before reading a diff or constructing a model. The other four owned product blobs remain unchanged. All 953 unrelated current-parent leaves and modes are retained by full-tree composition, including the raw-diff guide, seven native tests and original owner evidence.

## Bounded native receiving

On ordinary-user Linux Python 3.14.4, eight tests plus twelve subtests passed: all seven incoming raw-diff transport methods and the existing recheck CLI bypass/reuse case. The incoming generation tests intentionally use the unchanged ScriptedModel, valid Python source with ASCII/UTF-8/Latin-1/CP1252 and file/Git/binary-stdin routes; their own temporary native Git patch/application and pytest checks run unchanged. No live provider is used.

Two additional actual recheck commands consume the same original maintained `calc_clamp` report. The unchanged buggy fixture returns exit 1 with three retained failures and one pass; its maintained fixed source returns exit 0 with all four retained cases passed. Both preserve exact retained tests, original report, author fixtures, source and current checkout bytes, and record zero model calls. `bounded-qualification.json`, the two complete result JSON files, native driver and raw command outputs retain those separate executions. No broad native suite was repeated.

## Source and storage custody

The first home-volume guard stopped before any R4 source or product execution. A paired read observed zero available bytes on the home ext4 volume, while `/tmp` and `/dev/shm` were distinct memory filesystems. Qualification used the new exclusive `/dev/shm/testpilot-recheck-r4-68e476e98b77` root with the unchanged 128 MiB free-space guard. This is explicitly volatile native storage; it is not described as a durable receiver. Original R1/R2/R3 sources and archives remain on the home volume, unchanged.

`source-composition.json` binds all thirty materialized input files, the exact CLI seam and full incoming delta. It retains the source/checkout identity of the earlier successful hosted run: 321 tests and six subtests on the merge of R3 into old `aded01e`, not this new parent. Current-head hosted CI remains separate.
