#!/usr/bin/env python3
"""Validate E2 schemas, examples, artifact links, hashes, and cross-field rules."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any, Iterable

from jsonschema import Draft202012Validator, FormatChecker
from jsonschema.exceptions import ValidationError


ROOT = Path(__file__).resolve().parent
SCHEMA_DIR = ROOT / "contracts" / "v1"
REQUEST_DIR = ROOT / "examples" / "requests"
RESPONSE_DIR = ROOT / "examples" / "responses"
INVALID_DIR = ROOT / "examples" / "invalid"


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def validator(name: str) -> Draft202012Validator:
    schema = load_json(SCHEMA_DIR / name)
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema, format_checker=FormatChecker())


REQUEST_VALIDATOR = validator("create-request.schema.json")
CREATE_RESPONSE_VALIDATOR = validator("create-response.schema.json")
JOB_VALIDATOR = validator("job.schema.json")
ARTIFACT_VALIDATOR = validator("artifact.schema.json")


def artifact_path(uri: str) -> Path:
    prefix = "artifact://"
    if not uri.startswith(prefix):
        raise ValueError(f"unsupported artifact URI: {uri}")
    relative = Path(*uri[len(prefix) :].split("/"))
    path = (ROOT / "artifacts" / relative).resolve()
    artifact_root = (ROOT / "artifacts").resolve()
    if artifact_root not in path.parents:
        raise ValueError(f"artifact URI escapes artifact root: {uri}")
    return path


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(65536), b""):
            digest.update(block)
    return digest.hexdigest()


def iter_artifact_refs(value: Any) -> Iterable[dict[str, Any]]:
    if isinstance(value, dict):
        if {"artifact_id", "type", "uri", "producer_job_id", "sha256"} <= value.keys():
            yield value
        for child in value.values():
            yield from iter_artifact_refs(child)
    elif isinstance(value, list):
        for child in value:
            yield from iter_artifact_refs(child)


def validate_artifact_ref(ref: dict[str, Any], expected_job_id: str | None = None) -> None:
    ARTIFACT_VALIDATOR.validate(ref)
    if expected_job_id and ref["producer_job_id"] != expected_job_id:
        raise ValueError(
            f"artifact {ref['artifact_id']} producer_job_id does not match {expected_job_id}"
        )
    path = artifact_path(ref["uri"])
    if not path.is_file():
        raise ValueError(f"artifact does not exist: {ref['uri']}")
    actual = sha256(path)
    if actual != ref["sha256"]:
        raise ValueError(
            f"artifact hash mismatch for {ref['uri']}: expected {ref['sha256']}, got {actual}"
        )


def validate_request_semantics(document: dict[str, Any]) -> None:
    job_type = document["job_type"]
    job_input = document["input"]
    if job_type == "INCREMENTAL_CHECK":
        baseline = job_input["baseline"]
        if baseline["commit"] != job_input["base_commit"]:
            raise ValueError("baseline.commit must equal base_commit")
        if baseline["configuration_id"] != job_input["environment"]["configuration_id"]:
            raise ValueError("baseline configuration must match execution environment")
        if not artifact_path(baseline["actual_graph_uri"]).is_file():
            raise ValueError("baseline actual graph is not readable")
    elif job_type == "REPAIR":
        report_path = artifact_path(job_input["error_report_uri"])
        report = load_json(report_path)
        findings = report.get("findings", [])
        if not findings:
            raise ValueError("repair input must contain at least one finding")
        if any(item.get("type") != "MISSING" for item in findings):
            raise ValueError("REPAIR may consume MISSING findings only")
        if report.get("repository_commit") != job_input["repository"]["commit"]:
            raise ValueError("repair report commit must match repository.commit")
        if report.get("configuration_id") != job_input["environment"]["configuration_id"]:
            raise ValueError("repair report configuration must match execution environment")


def validate_request(path: Path) -> dict[str, Any]:
    document = load_json(path)
    REQUEST_VALIDATOR.validate(document)
    validate_request_semantics(document)
    return document


def validate_job(path: Path) -> dict[str, Any]:
    document = load_json(path)
    JOB_VALIDATOR.validate(document)
    for ref in iter_artifact_refs(document.get("output")):
        validate_artifact_ref(ref, document["job_id"])

    if document["job_type"] == "FULL_CHECK" and document["status"] == "SUCCEEDED":
        report_ref = document["output"]["error_report"]
        report = load_json(artifact_path(report_ref["uri"]))
        counts = {"MISSING": 0, "REDUNDANT": 0}
        for finding in report.get("findings", []):
            if finding.get("type") in counts:
                counts[finding["type"]] += 1
        summary = document["output"]["findings_summary"]
        if summary != {"missing": counts["MISSING"], "redundant": counts["REDUNDANT"]}:
            raise ValueError("findings_summary does not match the referenced report")

    if document["job_type"] == "INCREMENTAL_CHECK" and document["status"] == "SUCCEEDED":
        if document["output"]["base_commit"] != document["input"]["base_commit"]:
            raise ValueError("incremental output base_commit must match input base_commit")
    return document


def run_suite() -> None:
    checks = 0
    for path in sorted(REQUEST_DIR.glob("*.json")):
        validate_request(path)
        print(f"PASS request       {path.relative_to(ROOT)}")
        checks += 1

    for path in sorted(RESPONSE_DIR.glob("*-accepted.json")):
        CREATE_RESPONSE_VALIDATOR.validate(load_json(path))
        print(f"PASS 202 response  {path.relative_to(ROOT)}")
        checks += 1

    for path in sorted(RESPONSE_DIR.glob("*-succeeded.json")):
        validate_job(path)
        print(f"PASS job response  {path.relative_to(ROOT)}")
        checks += 1

    failure_path = RESPONSE_DIR / "full-check-failed.json"
    validate_job(failure_path)
    print(f"PASS failure model {failure_path.relative_to(ROOT)}")
    checks += 1

    expected_failures = {
        "bad-job-type.json": "schema",
        "incremental-missing-baseline.json": "schema",
        "incremental-baseline-mismatch.json": "semantic",
        "repair-with-redundant-finding.json": "semantic",
    }
    for filename, failure_kind in expected_failures.items():
        path = INVALID_DIR / filename
        try:
            validate_request(path)
        except (ValidationError, ValueError) as exc:
            is_schema = isinstance(exc, ValidationError)
            actual_kind = "schema" if is_schema else "semantic"
            if actual_kind != failure_kind:
                raise AssertionError(
                    f"{filename} failed as {actual_kind}, expected {failure_kind}: {exc}"
                ) from exc
            print(f"PASS rejected({failure_kind}) {path.relative_to(ROOT)}")
            checks += 1
        else:
            raise AssertionError(f"invalid example was accepted: {filename}")

    print(f"\nAll {checks} contract checks passed.")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--request", type=Path, help="validate one creation request")
    parser.add_argument("--job", type=Path, help="validate one query-job response")
    args = parser.parse_args()
    try:
        if args.request:
            validate_request(args.request.resolve())
            print(f"PASS request {args.request}")
        elif args.job:
            validate_job(args.job.resolve())
            print(f"PASS job {args.job}")
        else:
            run_suite()
    except (OSError, ValueError, ValidationError, AssertionError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
