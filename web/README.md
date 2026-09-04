# Waybill — web interface

React + Vite front end for the Waybill routing engine.

## Provenance

The interface, components, and the TypeScript solver implementations were
imported from [`bug1857/Waybill-G`](https://github.com/bug1857/Waybill-G)
at commit `32c217a`, a parallel implementation of this project's brief built
with Google AI Studio.

The UI work is good and was kept largely intact. The data and several
correctness issues were not, and are documented below so the difference between
what was inherited and what was changed is auditable.

## What was changed on import, and why

### 1. All benchmark data was replaced

`src/core/bench/datasets.ts` originally inlined TSPLIB coordinates directly into
source. Checked against the real archive files:

| Instance | Problem | Effect |
|---|---|---|
| `eil51` | none — coordinates matched exactly | correct |
| `berlin52` | **17 of 52 coordinates wrong** | published optimal tour scored **16,883** against a published **7,542** |
| `bayg29` | `EDGE_WEIGHT_TYPE: EXPLICIT` treated as Euclidean | distances **6.07× off**; its own suite reported a 621% nearest-neighbour gap |

Coordinates now come from `src/data/instances.generated.ts`, produced by
`python -m tools.generate_web_data` from the checksummed files in
`../data/tsplib/`. Each instance is verified before export: its published
optimal tour is scored with this project's own implementation and must match.
`tests/test_web_data.py` fails if that file is edited by hand.

`bayg29` was dropped rather than corrected — it is matrix-defined, and returns
once the TypeScript side can represent an explicit matrix.

### 2. Misleading provenance labels corrected

`createAsymmetricRoadMatrix` generates asymmetry from `Math.sin(i*13 + j*7)`.
It labelled its output `provider: 'OSRM_ROAD_ASYMMETRIC'` and
`source: 'Real Asymmetric OSRM Simulation'`. There is no OSRM in this code path.

Now labelled `SYNTHETIC_ASYMMETRIC`, with provenance strings saying so. Real
road matrices come from `adapters/distance/osrm.py` on the Python side.

### 3. Hand-written findings removed

`ReportSummary.tsx` stated a "96.4% pruning ratio" and "92% of maximum
attainable fleet optimization in less than 5 ms". Running the project's own
`runBoundQualityComparison(14)` returns **89.2%**. Neither figure was produced by
any run. Both are now marked pending measurement.

This is the failure the evidence bundle in §04 of the architecture plan exists
to make impossible.

### 4. Unit handling fixed

Solvers hardcoded `objective_units: 'metres'` regardless of the matrix, and the
UI divided by 1000 to display kilometres. TSPLIB costs are **abstract integers**
with no physical interpretation, so eil51's tour showed as `0.46 km` instead of
`458`. Units now derive from the matrix, and `src/lib/format.ts` formats each
unit correctly without converting across them.

### 5. Display fixes

An unconstrained TSP vehicle uses `MAX_SAFE_INTEGER` as a sentinel, which was
rendered literally (`51 / 9007199254740991 pkgs`). It now reads "no capacity
limit". The panel titled "Real Route Graph" was renamed, since it contradicted
the synthetic label beside it.

## What was kept, and is good

- The whole interface and component layout.
- **The 2-opt asymmetry correction**, which is right: it sums
  `matrix[v][u] - matrix[u][v]` across the reversed segment rather than using the
  four-term delta, with correct loop bounds. This is the hardest single detail in
  the brief.
- `src/core` contains no UI imports — the layering was respected.
- The distance convention: JavaScript's `Math.round` rounds half away from zero
  for non-negative values, which matches TSPLIB's `nint` exactly. On corrected
  data the engine reproduces every published optimum.

## Commands

```bash
make web-setup    # install dependencies
make web-dev      # run the dev server
make web-build    # production build
make crosscheck   # verify the TS engine against the verified data
make web-data     # regenerate instance data from data/tsplib/
```

`make crosscheck` is the important one. Python parses the published optimal
tours from the real `.opt.tour` files; TypeScript scores them. Neither side
supplies the input it is judged against, so two independent implementations
have to agree.

## Status

This engine runs in the browser and is useful for interactive exploration. It is
**not** the source of reported evidence. Under revision 3 of the architecture
plan, `bench/` on the Python side emits an evidence bundle, and the report and
demo render from that. Until then, treat numbers shown here as illustrative and
cross-checked, not as measured results.
