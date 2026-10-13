# Recorded failure diagnostics open on review

This increment makes saved TestPilot comparisons easier to scan: recorded
`failed` and `error` cases start expanded in each Final diagnostics column.
Passed and skipped cases and the retained output tail start collapsed.
Every disclosure still uses native keyboard and pointer controls. Opening a
recorded diagnostic does not make missing JUnit evidence complete or imply
that two equally named cases represent identical tests.

The implementation is one call in `testpilot/compare_html.py`; the admitted
report data, reader, report ordering, text escaping, exact JSON downloads,
styles and no-script policy are unchanged. Source and review ownership is
recorded in [issue122](https://github.com/Jacob-Met/testpilot/issues/122).

## Source and useful reading copy

The original main is `8cd5cdb79923100072b228ae1a92f9d4cda806dc`.
The tested product commit is `4524553d34612a4b7f202f853246b287b37c8561`,
tree `4054b80ffe6ba955fa3ac6a1ba2a45c0e6c6acce`.
The final publication adds these records and a guide link without changing
the tested renderer or test module.

| File | Exact tested Git blob |
| --- | --- |
| Original renderer | `40da0f674798583bd25a177021759aa38b3c5b7b` |
| Candidate renderer | `6893d082285e6963b3761c886330185c286e38b8` |
| New focused tests | `256539161d8035006c18aadaddefd68fec76266c` |
| Unchanged reader | `11d8bbd4939b749760bd2b5fc26326a79ece1e40` |

[The source manifest](source-manifest.json) lists the complete 15-module
runtime closure and original/candidate packet identities. All package
modules were received normally; no substitute import namespace was used.

Open the [existing comparison guide](https://docs.google.com/document/d/1zJRklgTVr-mKdfjLm2sSvyGyvQig-S92XktMe9AuIaY/edit)
for the delivered fictional example. The same exact
[mixed comparison HTML](independent/candidate-producer-v1/pages/mixed.html)
is retained here, together with the [incomplete-evidence example](independent/candidate-producer-v1/pages/incomplete.html).
Save the HTML and open it directly. Its two JSON links download the original
fictional reports; the page needs no JavaScript or network connection.
These examples are saved data, not requests to execute the report-listed code.

The mixed page is 23,452 bytes, SHA-256
`ea3a17013a8aab2a2033100b1ab3169b19a3ca72635584311e3ff598d2339936`,
Git `5eaa189302707caa6ff3d3ed67b2a413317cffe6`.
The independent [saved-copy receipt](delivery/saved-copy-receiving.json)
records one fresh HTTP 200 download with those exact bytes and conserved
native source identity. This delivery observation is separate from the
browser course and is not an installed or hosted application update.

## Focused author tests

The author used the existing ThinkPad Python 3.14.4 and pytest installation.
The original and candidate were staged in distinct fresh source directories;
each complete 18-file source inventory and its source packet retained exact
bytes, mode, nanosecond mtime and inode. Bytecode and pytest cache writing
were disabled, and temporary files stayed in owned output directories.

| Epoch | Actual result | Raw record |
| --- | --- | --- |
| Original with new expectations | 3 expected initial-open assertion failures; 2 empty-result controls pass; pytest exit 1 | [Original receipt](author/original/receiving.json), [stdout](author/original/pytest.stdout.txt), [JUnit](author/original/junit.xml) |
| Candidate | 9 selected, 9 pass, 0 skip; pytest exit 0 | [Candidate receipt](author/candidate/receiving.json), [stdout](author/candidate/pytest.stdout.txt), [JUnit](author/candidate/junit.xml) |

The five new cases cover both columns, duplicate case occurrences, empty
diagnostics, all four admitted outcome labels, exact original downloads,
absent/false JUnit flags and absent/empty final cases. Four existing selected
checks cover immutable original downloads, incomplete execution evidence,
duplicate target context and lexical Decimal precision. Both stderr streams
are empty. No report-listed tests, model calls or generation routes ran.

The [executed author driver](author/receive_author.py) and
[collected process returns](author/process-collections.json) preserve the
original expected-failure distinction. Its top-level success means the
observed original result matched the frozen expectation, not that the
original passed the new assertions.

For ordinary maintained source validation:

~~~bash
python -m pytest -q tests/test_compare_diagnostics.py
~~~

## Independent supported producer and browser receiving

The independent receiver froze [four fictional report strings and criteria](independent/fixture-packet-v1.json)
before seeing the candidate. They include all four admitted outcomes, repeated
labels with distinct occurrences, empty failure/error messages, null generated
file attribution, literal markup and control characters. The Before report
has a UTF-8 BOM and CRLF; the After report has LF. A separate page covers an
absent JUnit flag and a final result of null.

Both variants were generated by the ordinary `python -B -m testpilot compare`
command on ThinkPad Python 3.14.4. Each variant had two CLI children, all exit 0;
all eight raw streams are retained alongside the corresponding receipt.
Complete 15-module source, input, driver and packet inventories stayed exact.
The existing Veria Python 3.11.9 only drove Playwright and Chrome; it was not
used as a supported TestPilot product runtime.

| Epoch | Actual result | Raw record |
| --- | --- | --- |
| Original producer | Two CLI children exit 0 | [Receipt](independent/original-producer-v1/receiving.json), [executed driver](independent/produce_original.py) |
| Original browser v1 | 16 checks pass; one observer selector count fails; exit 1 | [Receipt](browser/original-browser-v1/receiving.json), [observer](browser/receive_browser_v1.py) |
| Original browser v2 | 22 checks pass; one observer visible-text check fails inside a correctly collapsed detail; exit 1 | [Receipt](browser/original-browser-v2/receiving.json), [observer](browser/receive_browser_v2.py) |
| Original browser v3 | 87 checks pass, two actual exact JSON downloads; exit 0 | [Receipt](browser/original-browser-v3/receiving.json), [observer](browser/receive_browser_v3.py) |
| Candidate producer | Two CLI children exit 0 | [Receipt](independent/candidate-producer-v1/receiving.json), [executed driver](independent/produce_candidate.py) |
| Candidate browser v1 | 87 checks pass, two actual exact JSON downloads; exit 0 | [Receipt](browser/candidate-browser-v1/receiving.json), same final observer |

The first observer correction changes only two case-disclosure selectors.
The second changes one hidden-text observation to exact retained paragraph
text. Neither changes the frozen report data, original renderer, expected
disclosure states or product. The original HTML was generated once and reused
for those observations. The successful original course was sealed before
candidate exposure; the same final observer then received the candidate once.

The completed browser courses used Chrome 154.0.8037.97 with JavaScript
disabled. They independently received ordered case outcomes and literal text,
empty-message fallbacks, attribution and missing-evidence labels. The original
cases were all closed. Candidate initial states were:

| Page and role | Case order | Initial open states |
| --- | --- | --- |
| Mixed Before | failed, passed, failed, skipped, error, error | true, false, true, false, true, true |
| Mixed After | error, passed, failed, skipped, error | true, false, true, false, true |
| Incomplete Before | failed, passed | true, false |
| Final-null After | No case records | No case disclosures |

Native Tab/Enter and pointer controls toggle and restore the disclosure;
the document fits the 390-pixel viewport. Both JSON downloads match the
frozen input bytes, including BOM, line endings and extra fields.
Print-media observation makes all diagnostic contents visible and returning
to screen preserves disclosure state. Each successful course makes only the
two expected local-file document requests, with no external requests, page
errors, console errors or stored state.

A separate exact-text comparison removes only seven added open attributes in
the mixed page and one in the incomplete page to recover each original HTML
byte-for-byte. The disclosure attributes are the entire rendered-byte delta.

The [process collection capture](browser/process-collections-v1.json) retains
the actual tool returns for all six producer/browser epochs. Every course,
including the failed observer attempts, conserves its complete intake and
driver/packet identities. Managed browser disconnection is observed; browser
OS exit is not measured. The [visual review](browser/visual-review-v1.json)
binds the actual desktop and narrow screenshots read by the independent
receiver. Screenshot bytes remain in its native output; this source record
does not substitute a regenerated image.

## Evidence boundaries

The 22 producer records and 13 browser records were transferred as exact
base64-bound native files and independently rechecked for byte count,
SHA-256 and Git blob identity before publication. Raw receipts and their
large native timestamp/inode values were not reserialized. The separate
author records and saved-copy delivery receipt retain their own scopes.

The retained scripts record these bounded historical courses, including
their original native paths and prerequisite runtimes. They do not install
dependencies or make the captured environments portable. The product's
normal comparison command and maintained tests remain the reusable route.

This qualification makes no claim about physical printing, universal font
coverage, accessibility certification, report truth, generated-test quality,
a provider, an installed application, or hosted deployment. The historical
saved-run comparison courses remain distinct.
