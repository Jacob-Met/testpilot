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
      typeof run.output !== 'string') return false;
  const total = run.passed + run.failed;
  return Number.isSafeInteger(total) && total > 0 &&
    run.ok === (run.failed === 0);
}
