# Evidence pipeline

Waybill records each solver result together with the exact source, input,
matrix, runtime, configuration, budget, and seed that produced it. The result
and its manifest are serialized into a versioned `evidence.json`; the bundle's
SHA-256 covers every field except the hash field itself. Loading a bundle
recomputes that hash and rejects tampering.

The evidence code is standard-library-only and lives in `bench/evidence/`.
Solver code does not write reports directly. Instead, a benchmark runner uses
`EvidenceRunner.register_solve_report(...)`, writes the bundle atomically, and
then generates Markdown from the validated bundle.

```python
from bench.evidence import EvidenceRunner, write_markdown_report

runner = EvidenceRunner(repo_root=".", metadata={"experiment": "phase-2"})
runner.register_solve_report(
    report,
    input_path="data/tsplib/eil51.tsp",
    matrix_hash=instance.matrix.content_hash,
    solver_config={"start_node": 0},
    budget=budget,
)
bundle = runner.write("artifacts/evidence.json")
write_markdown_report(bundle, "report/results.md")
```

`EvidenceRunner` copies all mutable mappings into canonical JSON before storing
them. A bundle cannot be created without at least one result, and strict loading
rejects missing or unknown schema fields, duplicate JSON keys, mixed units, and
a mismatched content hash.

## Command line

Validate a bundle and render its report:

```sh
python -m bench.evidence validate artifacts/evidence.json
python -m bench.evidence render artifacts/evidence.json --output report/results.md
```

The `record` subcommand is available for integration with a process that emits
one solver result. Run `python -m bench.evidence record --help` for its complete
schema. Programmatic registration is preferred because it avoids transcribing
measurements at a shell prompt.

## Input integrity

Every committed `.tsp` and `.opt.tour` input is named in
`data/tsplib/SHA256SUMS.json`, with its byte size and SHA-256. Verify all inputs
before benchmarking:

```sh
python -m tools.verify_data_manifest
# equivalent:
python -m bench.evidence verify-data
```

Verification fails for changed, missing, or unmanifested TSPLIB input files.
If a benchmark dataset is intentionally updated, review the provenance and the
file changes before updating the checksum manifest.

## Report provenance

`render_markdown(bundle)` accepts only an `EvidenceBundle`. Its fixed text is
labels and claim-discipline language; all measurements, identifiers, hashes,
configuration values, and runtime facts come from the bundle. Generated reports
carry the bundle SHA-256 and a per-record SHA-256. Treat report edits as display
changes only: regenerated output remains the evidence-bearing version.
`verify_markdown_report(bundle, text)` enforces byte-for-byte regeneration and
therefore rejects handwritten result numbers or any other manual report edit.
