from __future__ import annotations

import argparse
from pathlib import Path

from validate_seo_aeo import validate_brief


GEO_DIMENSIONS = {
    "entity_consistency",
    "evidence_traceability",
    "citation_suitability",
    "cited_source_alignment",
    "documented_engine_control",
}


def main() -> None:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)
    command = subparsers.add_parser("validate-brief")
    command.add_argument("artifact", type=Path)
    command.add_argument("--bundle", type=Path, required=True)
    args = parser.parse_args()
    validate_brief(
        args.artifact,
        args.bundle,
        expected_domain="geo",
        expected_producer="seo-geo",
        allowed_dimensions=GEO_DIMENSIONS,
        pass_label="seo-geo",
    )


if __name__ == "__main__":
    main()
