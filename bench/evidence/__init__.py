"""Public API for Waybill's versioned evidence pipeline."""

from bench.evidence.bundle import (
    EvidenceBundle,
    EvidenceIntegrityError,
    EvidenceRecord,
    write_bundle,
)
from bench.evidence.provenance import (
    GitState,
    ProvenanceError,
    capture_git_state,
    capture_manifest,
    sha256_file,
)
from bench.evidence.report import (
    ReportProvenanceError,
    render_markdown,
    verify_markdown_report,
    write_markdown_report,
)
from bench.evidence.runner import EvidenceRunner
from bench.evidence.schema import (
    SCHEMA_VERSION,
    EvidenceManifest,
    EvidenceResult,
    RunBudget,
    utc_timestamp,
)

__all__ = [
    "SCHEMA_VERSION",
    "EvidenceBundle",
    "EvidenceIntegrityError",
    "EvidenceManifest",
    "EvidenceRecord",
    "EvidenceResult",
    "EvidenceRunner",
    "GitState",
    "ProvenanceError",
    "ReportProvenanceError",
    "RunBudget",
    "capture_git_state",
    "capture_manifest",
    "render_markdown",
    "sha256_file",
    "utc_timestamp",
    "verify_markdown_report",
    "write_bundle",
    "write_markdown_report",
]
