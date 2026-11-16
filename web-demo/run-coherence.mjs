// SPDX-License-Identifier: Apache-2.0
// Refuse internally contradictory *recorded* runs in both replay entry points.
// This is data consistency, not independent authentication of its origin.
export function recordedRunIsCoherent(run) {
  if (!run ||
      !Number.isSafeInteger(run.passed) || run.passed < 0 ||
      !Number.isSafeInteger(run.failed) || run.failed < 0 ||
      !Number.isSafeInteger(run.errors) || run.errors !== 0 ||
      !Number.isSafeInteger(run.skipped) || run.skipped !== 0 ||
      run.timed_out !== false || typeof run.ok !== 'boolean' ||
      typeof run.output !== 'string' ||
      !Number.isSafeInteger(run.returncode) ||
      !Array.isArray(run.cases)) return false;
  const total = run.passed + run.failed;
  if (!Number.isSafeInteger(total) || total === 0 ||
      run.cases.length !== total ||
      run.returncode !== (run.failed === 0 ? 0 : 1) ||
      run.ok !== (run.failed === 0)) return false;
  const observed = {passed: 0, failed: 0};
  for (const test of run.cases) {
    if (!test || !['passed', 'failed'].includes(test.outcome) ||
        typeof test.nodeid !== 'string' || !test.nodeid) return false;
    observed[test.outcome]++;
  }
  return observed.passed === run.passed && observed.failed === run.failed;
}
