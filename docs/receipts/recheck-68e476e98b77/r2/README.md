# R2: current input composition and portable test fixture

Qualified parent: `e1d87442eeecc8cf1b44ee3547849d5c1d030876`, tree
`1466e2d4a2a1f2ce4fe5293e55e0b7f7e0b3797a`.

The production-owned recheck, CLI and sandbox bytes, plus RECHECK.md, are
unchanged from R1. Only the new nondefault-Python regression fixture changes:
it uses the established test_cli_python `.pth` pattern to reuse the caller's
installed pytest tooling without depending on global base-Python packages.
The original R1 source, logs and complete archive remain immutable.

Accepted current-main PR23's collector and PR24's HTML-report module, loop
and README are received as exact upstream blobs. Every other incoming leaf
and mode is retained by full current-parent tree composition. The separate
fence/patch PR22 was not part of this observed parent and is not imported.

Bounded native checks on this source:

- The one changed fixture case passes in an isolated no-pip venv with explicit
  tooling reuse; the final Python symlink and actual venv identity remain intact.
- Three unchanged real-report CLI controls preserve their R1 outcomes:
  buggy code fails three retained cases and passes one; the maintained fix
  passes all four; a current existing-suite failure remains a failure even
  when all four retained cases pass.
- Every source/report/checkout hash checked before and after is unchanged;
  all three CLI invocations retain the invalid-backend tripwire and zero new
  model calls.

`bounded-qualification.json`, raw affected-case output and the exact native
driver retain this separate run. The earlier 57 passes/six subtests/one optional
coverage skip remain R1 results; they are not relabeled as a full R2 rerun.
Root's independent source/forged-history review is a separate receiving record.
