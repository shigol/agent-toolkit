// Read data only. Never execute a worker artifact in the privileged result job.
const fs = require('node:fs');
const path = require('node:path');

function data(root, name) {
  const file = path.join(root, name);
  if (!fs.existsSync(file)) return null;
  const stat = fs.lstatSync(file);
  if (!stat.isFile() || stat.isSymbolicLink() || stat.size > 65536) throw Error('Invalid bounded worker report');
  return JSON.parse(fs.readFileSync(file, 'utf8'));
}

function result(root, metadata) {
  const checkpoint = data(root, 'checkpoint.json');
  const patch = data(root, 'patch-report.json');
  const input = checkpoint?.input_tokens;
  const known = checkpoint?.usage_known === true && Number.isSafeInteger(input) && input >= 0;
  const notStarted = metadata.execution === 'skipped';
  if (patch && (!Array.isArray(patch.held) || patch.held.length > 10000)) throw Error('Malformed held-path report');
  const pendingPatch = path.join(root, 'changes.patch');
  const hasPatch = fs.existsSync(pendingPatch) && fs.lstatSync(pendingPatch).isFile() && fs.statSync(pendingPatch).size > 0;
  return {run_id: Number(metadata.run_id), request_id: String(metadata.request_id), worker: metadata.worker,
    save: metadata.save, branch: metadata.branch || '', has_patch: hasPatch,
    held_count: patch?.held.length || 0, input_tokens: known ? input : 0,
    usage_known: known || notStarted, checkpoint_status: checkpoint?.status || 'not_available'};
}

module.exports = {result};
