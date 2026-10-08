# Pytest execution selection — source-bound receiving

This change adds native pytest keyword and marker expressions to the generation CLI and API. The same literal selection is used for the baseline, generated verification and every repair. An actual selected generated pass remains required. Reports and prompts retain the selection, and saved-test recheck continues to run its existing configured suite without inheriting generation filters.

Final public source: `d9fdf111a9e6193351a6be2912a2e0551443f223`; parents `513f17454af378ee042ccd29dc930ef332a48734` and original candidate `b16b27d29061a1e22d020998ee9449d8c9b40bf7`; full source tree `60d99ea117e836d4faa31927d18f3fcf97da135d`. The independent reconstruction preserves 1,422 inherited leaves unchanged and adds/changes exactly six owned paths. All six public source files were read back and their actual bytes reproduce the frozen Git and SHA-256 identities.

## Distinct source epochs and actual results

| Source | Receiving | Actual result |
| --- | --- | --- |
| Original upstream `191cca4e`, bounded capture `9d1fcc58` | Six original feature controls | Ordinary generation passes; a deliberate unselected fixture fails by default; both proposed CLI flags refuse with exit 2; the existing lower-level runner accepts each native filter and an actual generated pass. |
| Same original source | Complete native baseline | 389 passed, 18 subtests passed, one existing one-second helper-start precondition failed. Its single unchanged isolated control passed in 3.06 seconds. The original full failure remains retained. |
| First candidate `1cb5b358` / public `b16b27d` | Focused producer cases and independent consumer groups | 13 producer cases pass; 13 independently frozen groups pass. These include exact report downloads, all execution phases, selected-generated admission, literal/default/empty values and unfiltered recheck exposing two deliberately excluded failures. The independent groups deliberately disabled coverage. |
| First candidate `1cb5b358` | Complete native candidate suite | 407 passed, 25 subtests passed, one unchanged 0.4-second detached-helper-start precondition failed. All 94 captured source files remained unchanged. Host load was observed around 35; no causal fix or broad native pass is claimed, and this gate was not retried. |
| First candidate, then correction `68ab4720` | Real coverage-enabled refusal | One refused baseline produced a misleading before/after comparison. Removing one argument omits that nonexistent comparison while retaining the actual 100% native measurement, exit 4 and zero model calls/rounds. Original and corrected reports are retained. |
| Current composition `c97c0be3` | Three actual CLI controls | Selected generation passes; invalid timeout and malformed diff inputs are refused before replacing the preceding real report. All 96 source pins remain unchanged. |
| Preserved first candidate, then `c97c0be3` | Independently frozen coverage addendum | Original FAIL and current PASS. Actual project hooks establish exactly one pytest session, exit 4, zero model calls/generation, retained 100% native coverage and no aggregate comparison on the final source. |

The final peer review statically proves that reversing only the owned CLI/README additions recovers the entire current upstream files. The incoming strict diff parser and two new upstream tests are exact. The loop differs from the first candidate by only the coverage-comparison argument removal; HTML, guide, sandbox and recheck source retain their qualified bytes.

The native source histories are explicitly bounded captures of source/tests/eval/config, not invented public Git ancestry. Native receiving used Python 3.14.4, pytest 9.1.1 and coverage 7.16.2. The unknown earlier Mac baseline process is excluded from every passing claim.

## Artifact custody

`producer-native-packet.tar.gz` retains the original witnesses, fixtures, raw reports, failed full-suite logs/XML, the isolated timing control, source freezes, focused producer results, coverage before/after reports, current CLI controls and public-source bindings. Its readable manifest and custody receipt pin every member.

The independent directory preserves the reviewer's exact four delivered files: review, manifest, custody receipt and sealed archive. The archive contains all 261 original files unchanged plus four review artifacts and a complete manifest. It was read without extraction.

Both archives are inert. Deliberately failing Python fixtures stay inside them so ordinary pytest discovery cannot execute receiving artifacts under documentation. No archived command is dispatched during publication, and no receipt is reconstructed from missing output.

The original 13 independent groups are not relabeled as executions on a later source. Their source preservation, the narrow coverage addendum and bounded current-parent controls qualify the final composition separately. Ordinary hosted CI remains the complete gate on the final PR head; the native full-suite failures above are preserved honestly.
