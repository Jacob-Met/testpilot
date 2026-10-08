# TestPilot #35: current parent 362 static addendum

## Decision and identities

Accept the frozen cancellation source against current main **362981dd84626fd55eda93584c2984cd9d0e5276**, tree **1a75241e7e215b3586159fce945df70a6e139d78**. This is a bounded static composition review; the existing native cancellation results remain bound to their original **7f44** inputs.

The current commit merges **7f44c4f134f4d56d37dd14c7c2d2aaa3c8c8749e** and **0ff58452254a89969ccfced9444bff9f247280ca** through PR41. Its complete, untruncated tree has **1,072 leaves**, and all directory hashes reconstruct exactly.

The parent delta consists of **13 leaves: nine additions and four modifications**. Production changes are limited to:

| Path | Prior blob | Current blob |
| --- | --- | --- |
| testpilot/recheck.py | 4ab26cbb83beff563b9c3683c593b3efd2495b6b | b5d0b705c30c03e6b7e7e90b83e8dc83b8f9de52 |
| testpilot/recheck_html.py | absent | 9b16cf829029e1b5d34392bb93f6d3a31e916a90 |

The remaining delta is README/RECHECK documentation, one existing test assertion, the new renderer test and seven receiving files.

## Qualified execution inputs

Of the original **14 captured pins, 12 remain exact**. Only README.md and recheck.py differ. Of the **nine existing package modules, eight remain exact**; recheck_html.py is a new tenth module.

The original sandbox remains **8ca4a4102c7890e89eae99548e28ba8325974f1e**. The frozen candidate remains **84330f96ebd71b37dc40575fa2ac59ba53cf2a72**, from native source commit **649dc7d1fd02493af298876eea0697849404bba9**. CLI, loop/output staging, model, collector, dependency/workflow files and both existing sandbox tests retain their qualified bytes.

## Output-path interaction

Replacing only the new write_recheck_outputs block with its original block, and removing the two new imports, reproduces the entire original recheck.py bytes. Every other recheck function and class is AST-identical. Admission, retained-test placement, execution, timeout, console handling and return-code logic are unchanged.

The CLI eagerly imports recheck, so the new renderer is part of CLI import. Its top level contains only standard-library imports, function definitions and a literal CSS assignment. It performs no renderer call, file access, model call or test execution on import.

The actual renderer call occurs inside write_recheck_outputs after recheck_report returns a completed result. It prepares the additional HTML before creating the output directory. The unchanged run_recheck_command boundary catches OSError and RecheckError, not KeyboardInterrupt; an interrupted sandbox does not proceed to this output call.

Default generation and coverage behavior therefore remain unchanged. The peer's intended completed-recheck behavior—also writing recheck.html—is preserved. No cancellation or renderer test rerun was needed or performed for this source interaction.

## Ownership and preservation

Issue37 is now closed through merged PR41. Coverage issue36 remains represented by unmerged draft PR40 at **949d41109600811912b096d287d02f6b74d0c47d**. The explicit-target and comparison PRs remain open with their owners.

Applying only the original author's **27-path whitelist** to this current parent produces expected tree **57f86b70e34c5bca1ee83a41d9d33c22ec579d73**, containing **1,098 leaves**. Only sandbox.py replaces an existing file; all **1,071 unrelated current-parent leaves** remain exact. Separate author, product-receiver and current-parent evidence additions must still be accounted for in root's final publication tree.

The original review commit **d11523c991a0cb29bdd583b29a67dc1176b149d3** and its three-file publication packet are unchanged. The accompanying current362 qualification records the complete delta, all 14 pin comparisons, source hashes, function reconstruction and ownership observations. Full input/API/source and static-verifier custody is retained in the additive native evidence commit named by this packet.

No production source, live process, repository reference or test result was changed.
