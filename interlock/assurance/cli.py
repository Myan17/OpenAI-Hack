"""Small local CLI for verifying release evidence in a CI job."""

import argparse
import json
from pathlib import Path
from typing import Sequence

from interlock.assurance.evidence import verify_evidence_bundle
from interlock.assurance.models import ReleaseEvidenceBundle
from interlock.assurance.store import AssuranceStore


def main(argv: Sequence[str] | None = None) -> int:
    """Run the local verifier and return a conventional CI-compatible exit status."""

    parser = argparse.ArgumentParser(prog="interlock-assurance")
    subparsers = parser.add_subparsers(dest="command", required=True)
    verify_parser = subparsers.add_parser("verify", help="verify one exported evidence bundle")
    verify_parser.add_argument("bundle", type=Path)
    create_parser = subparsers.add_parser("case-create", help="capture a non-authoritative assurance candidate")
    create_parser.add_argument("--db", required=True, type=Path)
    create_parser.add_argument("--title", required=True)
    create_parser.add_argument("--summary", required=True)
    create_parser.add_argument("--source", required=True)
    create_parser.add_argument("--owner", required=True)
    create_parser.add_argument("--expires-at-epoch", type=int)
    review_parser = subparsers.add_parser("case-review", help="approve or reject one pending candidate")
    review_parser.add_argument("--db", required=True, type=Path)
    review_parser.add_argument("--case-id", required=True, type=int)
    review_parser.add_argument("--resolution", required=True, choices=("approved", "rejected"))
    review_parser.add_argument("--reviewer", required=True)
    args = parser.parse_args(argv)
    if args.command == "verify":
        return _verify(args.bundle)
    if args.command == "case-create":
        return _create_case(args)
    if args.command == "case-review":
        return _review_case(args)
    parser.error("unsupported command")
    return 2


def _verify(path: Path) -> int:
    """Parse one JSON bundle and emit only the machine-readable verification result."""

    try:
        bundle = ReleaseEvidenceBundle.model_validate_json(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        print(json.dumps({"valid": False, "error": str(error)}))
        return 2
    valid = verify_evidence_bundle(bundle)
    print(json.dumps({"valid": valid}))
    return 0 if valid else 1


def _create_case(args: argparse.Namespace) -> int:
    """Capture a candidate locally without granting runtime authority."""

    try:
        case = AssuranceStore(args.db).create_candidate(
            title=args.title,
            summary=args.summary,
            source=args.source,
            owner=args.owner,
            expires_at_epoch=args.expires_at_epoch,
        )
    except ValueError as error:
        print(json.dumps({"created": False, "error": str(error)}))
        return 2
    print(case.model_dump_json())
    return 0


def _review_case(args: argparse.Namespace) -> int:
    """Resolve one candidate once, retaining an explicit reviewer identity."""

    try:
        case = AssuranceStore(args.db).review_candidate(
            args.case_id, args.resolution, reviewer=args.reviewer
        )
    except ValueError as error:
        print(json.dumps({"reviewed": False, "error": str(error)}))
        return 2
    if case is None:
        print(json.dumps({"reviewed": False, "error": "candidate is not pending"}))
        return 1
    print(case.model_dump_json())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
