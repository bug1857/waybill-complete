/**
 * Cross-check the TypeScript engine against verified data.
 *
 * Two independent implementations agreeing is stronger evidence than either
 * alone, and this is the seam where the browser engine can silently diverge
 * from the Python one that produces the reported evidence.
 *
 * Scores each published optimal tour with the TypeScript distance code and
 * requires an exact match. Tours are supplied by the Python side, which parses
 * them from the real .opt.tour files, so neither side is trusted to produce the
 * input it is checked against.
 *
 * Exits non-zero on any mismatch.
 */

import { createTsplibInstance, TsplibName } from '../src/core/bench/datasets';
import { calculateTourCost } from '../src/core/eval/feasibility';
import { solveNearestNeighbour } from '../src/core/construct/nearestNeighbour';
import { solveClarkeWrightSavings } from '../src/core/construct/clarkeWright';

import { readFileSync } from 'node:fs';

const toursPath = process.argv[2];
if (!toursPath) {
  console.error('usage: tsx scripts/crosscheck.ts <tours.json>');
  console.error('The tours file is written by the Python side (make crosscheck).');
  process.exit(2);
}
const tours: Record<string, number[]> = JSON.parse(readFileSync(toursPath, 'utf8'));

let failures = 0;
console.log('instance    n     ts-scored  published  match   nn      cw');
console.log('-'.repeat(66));

for (const [name, tour] of Object.entries(tours)) {
  const inst = createTsplibInstance(name as TsplibName);
  const opt = inst.knownOptimum!;
  const scored = calculateTourCost([...tour, tour[0]], inst.distanceMatrix.matrix);
  const ok = scored === opt;
  if (!ok) failures++;

  const nn = solveNearestNeighbour(inst);
  const cw = solveClarkeWrightSavings(inst);

  console.log(
    `${name.padEnd(11)} ${String(inst.stops.length).padEnd(5)} ${String(scored).padEnd(10)} ` +
    `${String(opt).padEnd(10)} ${(ok ? 'YES' : 'NO').padEnd(7)} ` +
    `${String(nn.objective_value).padEnd(7)} ${cw.objective_value}`
  );
}

if (failures > 0) {
  console.error(`\n${failures} instance(s) did not reproduce their published optimum.`);
  console.error('The TypeScript distance convention or the generated data is wrong.');
  process.exit(1);
}
console.log('\nTS engine reproduces every published optimum exactly.');
