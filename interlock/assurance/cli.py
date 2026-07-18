"""Small local CLI for verifying release evidence in a CI job."""

import argparse
import json
from pathlib import Path
from typing import Sequence

from interlock.assurance.evidence import verify_evidence_bundle
from interlock.assurance.models import ReleaseEvidenceBundle


def main(argv: Sequence[str] | None = None) -> int:
    """Run the local verifier and return a conventional CI-compatible exit status."""

    parser = argparse.ArgumentParser(prog="interlock-assurance")
    subparsers = parser.add_subparsers(dest="command", required=True)
    verify_parser = subparsers.add_parser("verify", help="verify one exported evidence bundle")
    verify_parser.add_argument("bundle", type=Path)
    args = parser.parse_args(argv)
    if args.command == "verify":
        return _verify(args.bundle)
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


if __name__ == "__main__":
    raise SystemExit(main())
