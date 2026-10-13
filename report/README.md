# Generated reports

Do not type benchmark results into this directory. Generate Markdown from a
validated evidence bundle:

```sh
python -m bench.evidence render artifacts/evidence.json --output report/results.md
```

See `docs/evidence-pipeline.md` for the evidence schema and provenance model.
