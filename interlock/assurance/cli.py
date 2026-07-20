"""Small local CLI for verifying release evidence in a CI job."""

import argparse
import json
from pathlib import Path
from typing import Sequence

from pydantic import TypeAdapter

from interlock.assurance.evidence import verify_evidence_bundle
from interlock.assurance.models import ChangeManifest, ProposedChangeEnvelope, ReleaseEvidenceBundle, ReplayCaseResult
from interlock.assurance.multica_adapter import evaluate_fixture_change
from interlock.assurance.store import AssuranceStore
from interlock.engine.models import Policy
from interlock.engine.simulator import SimulationStep


_STEPS_ADAPTER = TypeAdapter(list[SimulationStep])


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
    attach_parser = subparsers.add_parser("fixture-attach", help="attach one local replay fixture to an active case")
    attach_parser.add_argument("--db", required=True, type=Path)
    attach_parser.add_argument("--case-id", required=True, type=int)
    attach_parser.add_argument("--policy", required=True, type=Path)
    attach_parser.add_argument("--steps", required=True, type=Path)
    replay_parser = subparsers.add_parser("case-replay", help="replay one active local fixture")
    replay_parser.add_argument("--db", required=True, type=Path)
    replay_parser.add_argument("--case-id", required=True, type=int)
    retire_parser = subparsers.add_parser("case-retire", help="retire one active assurance case")
    retire_parser.add_argument("--db", required=True, type=Path)
    retire_parser.add_argument("--case-id", required=True, type=int)
    retire_parser.add_argument("--actor", required=True)
    audit_parser = subparsers.add_parser("case-audit", help="export append-only lifecycle events")
    audit_parser.add_argument("--db", required=True, type=Path)
    audit_parser.add_argument("--case-id", required=True, type=int)
    export_parser = subparsers.add_parser("snapshot-export", help="export a deterministic local recovery snapshot")
    export_parser.add_argument("--db", required=True, type=Path)
    export_parser.add_argument("--output", required=True, type=Path)
    import_parser = subparsers.add_parser("snapshot-import", help="restore a snapshot into an empty local store")
    import_parser.add_argument("--db", required=True, type=Path)
    import_parser.add_argument("--input", required=True, type=Path)
    fixture_parser = subparsers.add_parser("fixture-evaluate", help="evaluate a local Multica-shaped fixture")
    fixture_parser.add_argument("--envelope", required=True, type=Path)
    fixture_parser.add_argument("--baseline", required=True, type=Path)
    fixture_parser.add_argument("--replays", required=True, type=Path)
    args = parser.parse_args(argv)
    if args.command == "verify":
        return _verify(args.bundle)
    if args.command == "case-create":
        return _create_case(args)
    if args.command == "case-review":
        return _review_case(args)
    if args.command == "fixture-attach":
        return _attach_fixture(args)
    if args.command == "case-replay":
        return _replay_case(args)
    if args.command == "case-retire":
        return _retire_case(args)
    if args.command == "case-audit":
        return _audit_case(args)
    if args.command == "snapshot-export":
        return _export_snapshot(args)
    if args.command == "snapshot-import":
        return _import_snapshot(args)
    if args.command == "fixture-evaluate":
        return _evaluate_fixture(args)
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


def _attach_fixture(args: argparse.Namespace) -> int:
    """Validate fixture files before binding them to one active reviewer-approved case."""

    try:
        policy = Policy.model_validate_json(args.policy.read_text(encoding="utf-8"))
        steps = _STEPS_ADAPTER.validate_json(args.steps.read_text(encoding="utf-8"))
        AssuranceStore(args.db).attach_replay_fixture(args.case_id, policy=policy, steps=steps)
    except (OSError, ValueError) as error:
        print(json.dumps({"attached": False, "error": str(error)}))
        return 2
    print(json.dumps({"attached": True, "case_id": args.case_id}))
    return 0


def _replay_case(args: argparse.Namespace) -> int:
    """Run an existing fixture through the deterministic local simulator only."""

    try:
        result = AssuranceStore(args.db).replay_active_case(args.case_id)
    except ValueError as error:
        print(json.dumps({"replayed": False, "error": str(error)}))
        return 2
    print(result.model_dump_json())
    return 0 if result.passed else 1


def _retire_case(args: argparse.Namespace) -> int:
    """Retire an active case while retaining the append-only lifecycle history."""

    try:
        case = AssuranceStore(args.db).retire_case(args.case_id, actor=args.actor)
    except ValueError as error:
        print(json.dumps({"retired": False, "error": str(error)}))
        return 2
    if case is None:
        print(json.dumps({"retired": False, "error": "candidate is not active"}))
        return 1
    print(case.model_dump_json())
    return 0


def _audit_case(args: argparse.Namespace) -> int:
    """Print only structured local lifecycle evidence for a known assurance case."""

    try:
        store = AssuranceStore(args.db)
        store.case(args.case_id)
        events = store.audit_events(args.case_id)
    except ValueError as error:
        print(json.dumps({"audit": False, "error": str(error)}))
        return 2
    print(json.dumps(events, sort_keys=True))
    return 0


def _export_snapshot(args: argparse.Namespace) -> int:
    """Write a deterministic, local-only recovery snapshot."""

    try:
        snapshot = AssuranceStore(args.db).export_snapshot()
        args.output.write_text(json.dumps(snapshot, sort_keys=True, separators=(",", ":")), encoding="utf-8")
    except (OSError, ValueError) as error:
        print(json.dumps({"exported": False, "error": str(error)}))
        return 2
    print(json.dumps({"exported": True, "output": str(args.output)}))
    return 0


def _import_snapshot(args: argparse.Namespace) -> int:
    """Restore validated evidence only when the target store is empty."""

    try:
        snapshot = json.loads(args.input.read_text(encoding="utf-8"))
        if not isinstance(snapshot, dict):
            raise ValueError("assurance snapshot must be an object")
        count = AssuranceStore(args.db).import_snapshot(snapshot)
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(json.dumps({"imported": False, "error": str(error)}))
        return 2
    print(json.dumps({"imported_cases": count}))
    return 0


def _evaluate_fixture(args: argparse.Namespace) -> int:
    """Evaluate JSON fixtures locally; this command never contacts an agent platform."""

    try:
        envelope = ProposedChangeEnvelope.model_validate_json(args.envelope.read_text(encoding="utf-8"))
        baseline = ChangeManifest.model_validate_json(args.baseline.read_text(encoding="utf-8"))
        replays = TypeAdapter(list[ReplayCaseResult]).validate_json(args.replays.read_text(encoding="utf-8"))
        evidence, callback = evaluate_fixture_change(envelope, baseline, replays)
    except (OSError, ValueError) as error:
        print(json.dumps({"evaluated": False, "error": str(error)}))
        return 2
    print(json.dumps({"evidence": evidence.model_dump(mode="json"), "callback": callback.model_dump(mode="json")}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
