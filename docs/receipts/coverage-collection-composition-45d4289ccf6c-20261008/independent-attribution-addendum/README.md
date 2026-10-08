# Integration disposition: inherited attribution failure

**Hold integration acceptance for native source `09656db720176124bd206ed4bb871e6e8dcf6d42`, tree `08d13653668d58660cbf3614108ba79ddd8f3b17`.** The original frozen review continues to document exact source composition and split native execution; it does not establish integration acceptance.

## New primary evidence

A fresh [PR14](https://github.com/Jacob-Met/TestPilot/pull/14) read confirms the original collection source merged at 2026-10-08T11:35:43Z, head `dcd353531ad3dde353b63db4b09adca976b9f256`, merge `47a197fd46b107a797b1547db02cb5ed5ad2abe1`.

Receiver 965's [issue 13 comment](https://github.com/Jacob-Met/TestPilot/issues/13#issuecomment-6059045816) reports **seven passing and four failing real CLI attribution controls** on `fea8dff81e66572cfffe3aa5dcd2cca8c4158d98`, tree `bbd2dd27a39736fd94334910404763cb65773185`, the exact owner tree preserved by PR14. The receiver records unchanged source leaves/modes and inputs.

The strongest witness has a retained passing test whose autouse fixture records `testpilot.generated_file=tests/test_generated.py`, while the generated file contains only `helper_value = 12`. Its report attributes the retained case to that generated file and incorrectly declares one generated test collected and passed. Three additional controls cover duplicate identical, conflicting and empty markers. Seven healthy controls cover legitimate imported/inherited cases, missing identity, ordinary properties, collection prefixes and import-path behavior.

Those runtime results are attributed to receiver 965's primary report. This reviewer did not execute its controls.

## Source relationship and preserved evidence

Direct inspection of the already verified combined source confirms that its runner appends an identity only to generated items, while its JUnit parser accepts the first named identity and stops. This inherited source structure is consistent with the external negative.

The prior coverage and native receiving findings remain valid: the coverage block is unchanged from its earlier qualification, the initial full run passed 165 cases and failed four selected-interpreter controls, and those exact four then passed with aligned private tooling. Those runs do not cover the newly reported attribution failures.

Original review manifest `26b38760275e3947a89db72d363b0912497fe847a92cefd6bd58d93aa4775df0` remains unchanged. This separate addendum supersedes its earlier preflight statement that receiver 965's disposition was merely pending: that receiver has now supplied a concrete negative.

## Required event

The original source owner estate-86776 and receiver estate-965 remain the correction and receiving route. An exact attribution successor pin and qualified receiver disposition are required before integration acceptance. An actual final-headed hosted gate also remains pending. No competing source fix, test replay, package install, GitHub write or integration was performed.

The first attempt to create this additive directory encountered ENOSPC before any file was written. A subsequent read-only capacity check showed space available again. This reviewer did not clean any data.
