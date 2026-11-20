#!/usr/bin/env python3
"""Materialize the authored FX-006 synthetic catalogue without running a validator.

The catalogue owns expected outcomes. This builder only realizes deterministic
input recipes and records byte identities; it never derives an expected verdict.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path
import re


HERE = Path(__file__).resolve().parent
CATALOG = HERE / "catalog.json"
CASE_ID = re.compile(r"FX006-[0-9]{3}\Z")
MAX_CASE_BYTES = 4_194_304
MAX_CASES = 100
KINDS = {"analysis_result", "status_response", "rpc_error", "malformed_json", "boundary_result"}


def encoded(value: object) -> bytes:
    return (json.dumps(value, ensure_ascii=True, allow_nan=False, sort_keys=True,
                       separators=(",", ":")) + "\n").encode("utf-8")


def set_path(document: object, path: str, value: object, *, remove: bool = False) -> None:
    if not isinstance(path, str) or not path.startswith("/"):
        raise ValueError("Recipe edit requires an absolute JSON pointer")
    tokens = [token.replace("~1", "/").replace("~0", "~") for token in path[1:].split("/")]
    target = document
    for token in tokens[:-1]:
        target = target[int(token)] if isinstance(target, list) else target[token]
    key = int(tokens[-1]) if isinstance(target, list) else tokens[-1]
    if remove:
        del target[key]
    else:
        target[key] = copy.deepcopy(value)


def recipe_bytes(recipe: dict, seeds: dict[str, object]) -> bytes:
    kind = recipe.get("type")
    if kind == "seed":
        value = copy.deepcopy(seeds[recipe["seed"]])
        for edit in recipe.get("edits", []):
            if edit.get("op") not in {"set", "remove"}:
                raise ValueError("Unsupported recipe edit")
            set_path(value, edit["path"], edit.get("value"), remove=edit["op"] == "remove")
        if "aggregate_records" in recipe:
            total = recipe["aggregate_records"]
            if type(total) is not int or not 5 <= total <= 10_000:
                raise ValueError("Unsupported fixture record count")
            # This recipe is defined only for the one-item-per-section HIT seed.
            other = sum(len(value[section]) for section in ("findings", "timeline", "limitations", "chain_of_custody"))
            value["warnings"] = [f"SYNTHETIC BOUNDARY WARNING {i:04d}" for i in range(total - other)]
        if "warning_count" in recipe:
            count = recipe["warning_count"]
            if type(count) is not int or not 1 <= count <= 10_000:
                raise ValueError("Unsupported fixture warning count")
            value["warnings"] = [f"SYNTHETIC WARNING {i:04d}" for i in range(count)]
            value["warnings"][-1] = recipe["last_warning"]
        raw = encoded(value)
        if "pad_to_bytes" in recipe:
            target_size = recipe["pad_to_bytes"]
            if type(target_size) is not int or not len(raw) <= target_size <= MAX_CASE_BYTES:
                raise ValueError("Unsupported fixture byte target")
            # JSON whitespace changes byte size without changing source values.
            raw += b" " * (target_size - len(raw))
        if "truncate_bytes" in recipe:
            count = recipe["truncate_bytes"]
            if type(count) is not int or not 1 <= count < len(raw):
                raise ValueError("Unsupported truncation count")
            raw = raw[:-count]
    elif kind == "literal_json":
        raw = encoded(recipe["value"])
    elif kind == "raw_text":
        raw = recipe["text"].encode("utf-8")
    elif kind == "raw_hex":
        raw = bytes.fromhex(recipe["hex"])
    else:
        raise ValueError("Unsupported fixture recipe")
    if len(raw) > MAX_CASE_BYTES:
        raise ValueError("Fixture exceeds generator byte limit")
    return raw


def materialize_suite(output_dir: Path) -> Path:
    """Create inputs + manifest in a new/empty directory, never rewrite files."""
    output_dir = Path(output_dir)
    if output_dir.is_symlink() or (output_dir.exists() and (not output_dir.is_dir() or any(output_dir.iterdir()))):
        raise ValueError("Output directory must be new or empty and not a symlink")
    catalog_raw = CATALOG.read_bytes()
    catalog = json.loads(catalog_raw)
    if catalog.get("format_version") != 1 or catalog.get("synthetic") is not True:
        raise ValueError("Unsupported catalogue")
    if not isinstance(catalog.get("cases"), list) or not 1 <= len(catalog["cases"]) <= MAX_CASES:
        raise ValueError("Unsupported case count")
    seeds = {}
    for name, spec in catalog["seeds"].items():
        # Only the two already-authored local synthetic seed files are allowed.
        if spec["file"] not in {"completed-hit.json", "completed-no-ioc.json"}:
            raise ValueError("Unsupported seed file")
        seed_raw = (HERE.parent / "fixtures" / spec["file"]).read_bytes()
        if hashlib.sha256(seed_raw).hexdigest() != spec["sha256"]:
            raise ValueError("Seed content differs from the authored catalogue")
        seeds[name] = json.loads(seed_raw)
    manifest = {key: catalog[key] for key in ("format_version", "suite_id", "profile", "upstream_commit", "synthetic")}
    manifest["catalog_sha256"] = hashlib.sha256(catalog_raw).hexdigest()
    manifest["cases"] = []
    prepared = []
    seen = set()
    for case in catalog["cases"]:
        case_id = case.get("id")
        if not isinstance(case_id, str) or not CASE_ID.fullmatch(case_id) or case_id in seen:
            raise ValueError("Invalid or duplicate case ID")
        seen.add(case_id)
        if case.get("input_kind") not in KINDS:
            raise ValueError("Unsupported case input kind")
        raw = recipe_bytes(case["recipe"], seeds)
        item = {key: copy.deepcopy(case[key]) for key in ("id", "title", "tags", "input_kind", "profile", "expected_identity", "limits", "expected", "future_workflow")}
        if "input_assertions" in case:
            item["input_assertions"] = copy.deepcopy(case["input_assertions"])
        item.update(input_path=f"files/{case_id}.bin", sha256=hashlib.sha256(raw).hexdigest(), bytes=len(raw))
        manifest["cases"].append(item)
        prepared.append((item["input_path"], raw))
    # Validate every recipe before creating output; generated paths use only IDs.
    manifest_raw = (json.dumps(manifest, ensure_ascii=False, allow_nan=False, indent=2) + "\n").encode("utf-8")
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "files").mkdir()
    for relative, raw in prepared:
        with (output_dir / relative).open("xb") as stream:
            stream.write(raw)
    manifest_path = output_dir / "manifest.json"
    with manifest_path.open("xb") as stream:
        stream.write(manifest_raw)
    return manifest_path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path, help="New or empty destination directory")
    args = parser.parse_args()
    try:
        manifest = materialize_suite(args.output)
    except (ValueError, KeyError, TypeError, OSError) as error:
        parser.exit(2, f"Fixture materialization failed: {type(error).__name__}.\n")
    print(manifest)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
