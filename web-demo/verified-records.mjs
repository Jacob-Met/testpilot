// SPDX-License-Identifier: Apache-2.0
// Bind every displayed case to the bytes of its separately retained record.
// This detects drift between the manifest and saved evidence; neither file is
// a publisher signature, and this does not independently rerun Python.
function sameJSON(left, right) {
  if (left === right) return true;
  if (!left || !right || typeof left !== 'object' || typeof right !== 'object' ||
      Array.isArray(left) !== Array.isArray(right)) return false;
  if (Array.isArray(left)) return left.length === right.length &&
    left.every((value, index) => sameJSON(value, right[index]));
  const keys = Object.keys(left);
  return keys.length === Object.keys(right).length &&
    keys.every(key => Object.hasOwn(right, key) && sameJSON(left[key], right[key]));
}

async function recordForCase(item) {
  const file = item.files?.['record.json'];
  const expectedURL = `data/cases/${item.id}/record.json`;
  if (!file || file.url !== expectedURL || !Number.isSafeInteger(file.bytes) ||
      file.bytes <= 0 || !/^[0-9a-f]{64}$/.test(file.sha256)) {
    throw new Error(`${item.id}: missing or invalid recorded byte declaration`);
  }
  const response = await fetch(file.url, {cache: 'no-store', mode: 'same-origin', redirect: 'error'});
  if (!response.ok) throw new Error(`${item.id}: record HTTP ${response.status}`);
  const bytes = await response.arrayBuffer();
  if (bytes.byteLength !== file.bytes) throw new Error(`${item.id}: record byte count mismatch`);
  const digest = await crypto.subtle.digest('SHA-256', bytes);
  const sha256 = Array.from(new Uint8Array(digest), b => b.toString(16).padStart(2, '0')).join('');
  if (sha256 !== file.sha256) throw new Error(`${item.id}: record SHA-256 mismatch`);
  const record = JSON.parse(new TextDecoder('utf-8', {fatal: true}).decode(bytes));
  if (!record || typeof record !== 'object' || Array.isArray(record)) {
    throw new Error(`${item.id}: verified record is not an object`);
  }
  const {files: declaredFiles, ...visible} = item;
  const {files: storedFiles, ...saved} = record;
  const sourceFiles = {...declaredFiles};
  delete sourceFiles['record.json'];
  if (!sameJSON(visible, saved) || !sameJSON(sourceFiles, storedFiles)) {
    throw new Error(`${item.id}: displayed evidence differs from verified record`);
  }
  return {id: item.id, sha256, bytes};
}

export async function verifyCaptureRecords(data) {
  if (!Array.isArray(data?.cases) || !globalThis.crypto?.subtle) {
    throw new Error('Record SHA-256 requires HTTPS or localhost');
  }
  const entries = await Promise.all(data.cases.map(recordForCase));
  return new Map(entries.map(entry => [entry.id, entry]));
}
