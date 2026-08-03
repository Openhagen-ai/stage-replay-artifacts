#!/usr/bin/env python3
"""Validate the public ledgers and recompute the arXiv-v1 empirical claims."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import re
from collections import defaultdict
from collections.abc import Iterable
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
BOOTSTRAP_REPLICATES = 20_000
BOOTSTRAP_SEED = 20260728
SHA_RE = re.compile(r"^[0-9a-f]{64}$")
ROW_RE = re.compile(r"^r[0-9]{4}$")

MATCHED_HEADER = [
    "row_id",
    "source_row_sha256",
    "precision",
    "prefix_token_count",
    "prefix_sha256",
    "live_replica_cache_exact",
    "live_replica_logits_exact",
    "live_replica_suffix_exact",
    "prefill_replica_cache_exact",
    "prefill_replica_logits_exact",
    "prefill_replica_suffix_exact",
    "functional_state_equal",
    "all_storage_disjoint",
    "live_prefill_cache_exact",
    "cache_max_abs_diff",
    "cache_mean_abs_diff",
    "live_prefill_logits_exact",
    "logit_max_abs_diff",
    "logit_mean_abs_diff",
    "boundary_argmax_equal",
    "live_suffix_sha256",
    "live_replica_suffix_sha256",
    "prefill_suffix_sha256",
    "prefill_replica_suffix_sha256",
    "suffix_equal",
    "first_suffix_divergence_index",
    "trace_equal",
    "merge_equal",
    "answer_equal",
    "live_correct",
    "prefill_correct",
    "integrity_pass",
]

FIXED_HEADER = [
    "row_id",
    "source_row_sha256",
    "precision",
    "prefix_token_count",
    "prefix_sha256",
    "incremental_replica_cache_exact",
    "incremental_replica_logits_exact",
    "incremental_replica_suffix_exact",
    "prefill_replica_cache_exact",
    "prefill_replica_logits_exact",
    "prefill_replica_suffix_exact",
    "functional_state_equal",
    "all_storage_disjoint",
    "incremental_prefill_cache_exact",
    "cache_max_abs_diff",
    "cache_mean_abs_diff",
    "cache_delta_l2_norm",
    "cache_left_l2_norm",
    "cache_right_l2_norm",
    "cache_relative_l2_diff",
    "incremental_prefill_logits_exact",
    "logit_max_abs_diff",
    "logit_mean_abs_diff",
    "boundary_argmax_equal",
    "incremental_suffix_sha256",
    "incremental_replica_suffix_sha256",
    "prefill_suffix_sha256",
    "prefill_replica_suffix_sha256",
    "suffix_equal",
    "first_suffix_divergence_index",
    "trace_equal",
    "merge_equal",
    "answer_equal",
    "incremental_correct",
    "prefill_correct",
    "integrity_pass",
]

BRIDGE_HEADER = [
    "row_id",
    "source_row_sha256",
    "selection_index",
    "new_prefix_token_count",
    "new_prefix_sha256",
    "historical_prefix_token_count",
    "historical_prefix_sha256",
    "live_matches_historical_prefix",
    "boundary_cache_sequence_len",
    "post_decode_cache_sequence_len",
    "live_clone_cache_exact",
    "live_clone_logits_exact",
    "teacher_clone_cache_exact",
    "teacher_clone_logits_exact",
    "functional_state_equal",
    "all_storage_disjoint",
    "live_teacher_cache_exact",
    "live_teacher_logits_exact",
    "boundary_argmax_equal",
    "live_suffix_sha256",
    "teacher_suffix_sha256",
    "live_teacher_suffix_exact",
    "all_48_layers_exact",
    "integrity_pass",
]

HISTORICAL_HEADER = [
    "row_id",
    "source_live_row_sha256",
    "source_incremental_row_sha256",
    "prefix_commitment_equal",
    "live_incremental_suffix_equal",
    "live_replica_suffix_equal",
    "prefill_suffix_equal",
    "prefill_replica_suffix_equal",
    "comparison_objects_equal",
    "cache_live_replica_fingerprint_equal",
    "cache_live_prefill_fingerprint_equal",
    "cache_prefill_replica_fingerprint_equal",
    "logits_live_replica_fingerprint_equal",
    "logits_live_prefill_fingerprint_equal",
    "logits_prefill_replica_fingerprint_equal",
    "cache_common_scalar_leaves_per_section",
    "logit_common_scalar_leaves_per_section",
    "audit_pass",
]

TRANSPLANT_HEADER = [
    "row_id",
    "source_row_sha256",
    "checkpoint_alias",
    "selection_index",
    "selection_basis",
    "historical_stratum",
    "historical_stratum_reproduced",
    "prefix_token_count",
    "prefix_sha256",
    "incremental_replica_exact",
    "prefill_replica_exact",
    "functional_state_equal",
    "boundary_argmax_equal",
    "all_storage_disjoint",
    "all_48_layer_pairs_transplanted",
    "incremental_native_suffix_sha256",
    "prefill_native_suffix_sha256",
    "incremental_cache_into_prefill_suffix_sha256",
    "prefill_cache_into_incremental_suffix_sha256",
    "baseline_divergent",
    "incremental_cache_into_prefill_recovers_donor",
    "prefill_cache_into_incremental_recovers_donor",
    "bidirectional_donor_recovery",
    "exact_control_novel_trajectory",
    "integrity_pass",
]

STOCK_HEADER = [
    "row_id",
    "source_row_sha256",
    "selection_index",
    "input_token_count",
    "pair_replica_tokens_exact",
    "pair_replica_logprobs_exact",
    "singleton_pair_tokens_exact",
    "singleton_pair_logprobs_exact",
    "first_token_divergence_index",
    "first_logprob_divergence_index",
    "singleton_output_token_count",
    "paired_output_token_count",
    "max_abs_aligned_selected_token_logprob_difference",
]


class VerificationError(RuntimeError):
    """A released artifact or claim failed validation."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise VerificationError(f"expected JSON object: {path.name}")
    return value


def read_csv_exact(path: Path, header: list[str]) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames != header:
            raise VerificationError(f"unexpected schema in {path.name}")
        rows = list(reader)
    if any(set(row) != set(header) for row in rows):
        raise VerificationError(f"malformed row in {path.name}")
    return rows


def as_bool(value: str, *, field: str) -> bool:
    if value == "true":
        return True
    if value == "false":
        return False
    raise VerificationError(f"{field} is not canonical boolean text")


def as_optional_int(value: str) -> int | None:
    return None if value == "" else int(value)


def validate_identity(row: dict[str, str], *hash_fields: str) -> None:
    if not ROW_RE.fullmatch(row["row_id"]):
        raise VerificationError("invalid opaque row identifier")
    for field in hash_fields:
        if not SHA_RE.fullmatch(row[field]):
            raise VerificationError(f"invalid SHA-256 in {field}")


def verify_checksums() -> None:
    checksum_path = ROOT / "SHA256SUMS"
    entries: dict[str, str] = {}
    for line in checksum_path.read_text(encoding="utf-8").splitlines():
        digest, relative = line.split("  ", 1)
        if not SHA_RE.fullmatch(digest):
            raise VerificationError("invalid SHA256SUMS digest")
        path = Path(relative)
        if path.is_absolute() or ".." in path.parts or relative in entries:
            raise VerificationError("unsafe or duplicate SHA256SUMS path")
        entries[relative] = digest
    actual_files = {
        path.relative_to(ROOT).as_posix()
        for path in ROOT.rglob("*")
        if path.is_file() and path.name != "SHA256SUMS"
    }
    if actual_files != set(entries):
        raise VerificationError("bundle contains unlisted or missing files")
    for relative, expected in entries.items():
        path = ROOT / relative
        if path.is_symlink() or sha256_file(path) != expected:
            raise VerificationError(f"checksum failure: {relative}")

    manifest = load_json(ROOT / "release_manifest.json")
    inventory = manifest.get("file_inventory")
    if not isinstance(inventory, list):
        raise VerificationError("manifest file inventory is missing")
    for item in inventory:
        if not isinstance(item, dict):
            raise VerificationError("invalid manifest inventory item")
        relative = item.get("path")
        if relative not in entries or item.get("sha256") != entries[relative]:
            raise VerificationError("manifest/checksum inventory disagreement")
        if item.get("bytes") != (ROOT / relative).stat().st_size:
            raise VerificationError("manifest byte count disagreement")


def wilson_interval(successes: int, total: int, *, z: float) -> list[float]:
    if total <= 0:
        return [0.0, 0.0]
    proportion = successes / total
    denominator = 1.0 + z * z / total
    center = (proportion + z * z / (2.0 * total)) / denominator
    half = (
        z
        * math.sqrt(proportion * (1.0 - proportion) / total + z * z / (4.0 * total * total))
        / denominator
    )
    return [max(0.0, center - half), min(1.0, center + half)]


def rate_payload(values: Iterable[bool], *, z: float = 1.96) -> dict[str, Any]:
    vector = list(values)
    count = int(sum(vector))
    return {
        "count": count,
        "n": len(vector),
        "rate": count / len(vector),
        "wilson_95_ci": wilson_interval(count, len(vector), z=z),
    }


def bootstrap_mean_ci_pp(values: np.ndarray, *, stream: int) -> list[float]:
    rng = np.random.default_rng(BOOTSTRAP_SEED + stream)
    estimates = np.empty(BOOTSTRAP_REPLICATES, dtype=np.float64)
    for start in range(0, BOOTSTRAP_REPLICATES, 1_000):
        count = min(1_000, BOOTSTRAP_REPLICATES - start)
        indices = rng.integers(0, len(values), size=(count, len(values)))
        estimates[start : start + count] = values[indices].mean(axis=1) * 100.0
    return [float(value) for value in np.quantile(estimates, [0.025, 0.975])]


def exact_mcnemar(left_only: int, right_only: int) -> float:
    discordant = left_only + right_only
    if discordant == 0:
        return 1.0
    tail = sum(math.comb(discordant, k) for k in range(min(left_only, right_only) + 1))
    return min(1.0, 2.0 * tail / (2**discordant))


def median(values: Iterable[float]) -> float:
    return float(np.median(np.asarray(list(values), dtype=np.float64)))


def validate_matrix_rows(
    rows: list[dict[str, str]], *, fixed: bool
) -> dict[str, list[dict[str, str]]]:
    if len(rows) != 400:
        raise VerificationError("each matrix must contain 400 rows")
    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        validate_identity(
            row,
            "source_row_sha256",
            "prefix_sha256",
            "incremental_suffix_sha256" if fixed else "live_suffix_sha256",
            "incremental_replica_suffix_sha256" if fixed else "live_replica_suffix_sha256",
            "prefill_suffix_sha256",
            "prefill_replica_suffix_sha256",
        )
        if row["precision"] not in {"bf16", "fp32"}:
            raise VerificationError("unexpected precision")
        grouped[row["precision"]].append(row)
    for precision in ("bf16", "fp32"):
        grouped[precision].sort(key=lambda row: row["row_id"])
        if len(grouped[precision]) != 200:
            raise VerificationError("precision population is incomplete")
        ids = [row["row_id"] for row in grouped[precision]]
        if ids != [f"r{index:04d}" for index in range(200)]:
            raise VerificationError("matrix row order is incomplete")

        for row in grouped[precision]:
            prefix_count = int(row["prefix_token_count"])
            if prefix_count <= 0:
                raise VerificationError("invalid prefix length")
            suffix_left = row["incremental_suffix_sha256" if fixed else "live_suffix_sha256"]
            suffix_right = row["prefill_suffix_sha256"]
            suffix_equal = as_bool(row["suffix_equal"], field="suffix_equal")
            divergence = as_optional_int(row["first_suffix_divergence_index"])
            if suffix_equal != (suffix_left == suffix_right):
                raise VerificationError("suffix equality/hash disagreement")
            if suffix_equal != (divergence is None):
                raise VerificationError("suffix equality/divergence disagreement")

            left_prefix = "incremental" if fixed else "live"
            for field in (
                f"{left_prefix}_replica_cache_exact",
                f"{left_prefix}_replica_logits_exact",
                f"{left_prefix}_replica_suffix_exact",
                "prefill_replica_cache_exact",
                "prefill_replica_logits_exact",
                "prefill_replica_suffix_exact",
                "functional_state_equal",
                "all_storage_disjoint",
                "boundary_argmax_equal",
                "integrity_pass",
            ):
                if not as_bool(row[field], field=field):
                    raise VerificationError(f"integrity field failed: {field}")
            if row[f"{left_prefix}_replica_suffix_sha256"] != suffix_left:
                raise VerificationError("left replica commitment mismatch")
            if row["prefill_replica_suffix_sha256"] != suffix_right:
                raise VerificationError("prefill replica commitment mismatch")
    return grouped


def matrix_precision_summary(
    rows: list[dict[str, str]], *, fixed: bool, stream: int
) -> tuple[dict[str, Any], dict[str, np.ndarray]]:
    left = "incremental" if fixed else "live"
    cache_exact_field = "incremental_prefill_cache_exact" if fixed else "live_prefill_cache_exact"
    logits_exact_field = (
        "incremental_prefill_logits_exact" if fixed else "live_prefill_logits_exact"
    )
    left_correct_field = "incremental_correct" if fixed else "live_correct"

    suffix_mismatch = np.asarray(
        [not as_bool(row["suffix_equal"], field="suffix_equal") for row in rows],
        dtype=np.int8,
    )
    answer_mismatch = np.asarray(
        [not as_bool(row["answer_equal"], field="answer_equal") for row in rows],
        dtype=np.int8,
    )
    correctness_left = np.asarray(
        [as_bool(row[left_correct_field], field=left_correct_field) for row in rows],
        dtype=np.int8,
    )
    correctness_right = np.asarray(
        [as_bool(row["prefill_correct"], field="prefill_correct") for row in rows],
        dtype=np.int8,
    )
    correctness_difference = correctness_right - correctness_left
    correctness_flip = (correctness_difference != 0).astype(np.int8)
    logits_mismatch = np.asarray(
        [not as_bool(row[logits_exact_field], field=logits_exact_field) for row in rows],
        dtype=np.int8,
    )
    divergences = [as_optional_int(row["first_suffix_divergence_index"]) for row in rows]
    divergences = [value for value in divergences if value is not None]
    left_only = int(np.count_nonzero(correctness_difference == -1))
    right_only = int(np.count_nonzero(correctness_difference == 1))

    summary: dict[str, Any] = {
        "rows": len(rows),
        f"{left}_replica_exact_rows": sum(
            as_bool(row[f"{left}_replica_cache_exact"], field="replica")
            and as_bool(row[f"{left}_replica_logits_exact"], field="replica")
            and as_bool(row[f"{left}_replica_suffix_exact"], field="replica")
            for row in rows
        ),
        "prefill_replica_exact_rows": sum(
            as_bool(row["prefill_replica_cache_exact"], field="replica")
            and as_bool(row["prefill_replica_logits_exact"], field="replica")
            and as_bool(row["prefill_replica_suffix_exact"], field="replica")
            for row in rows
        ),
        "functional_state_equal_rows": sum(
            as_bool(row["functional_state_equal"], field="functional_state_equal") for row in rows
        ),
        "all_storage_disjoint_rows": sum(
            as_bool(row["all_storage_disjoint"], field="all_storage_disjoint") for row in rows
        ),
        "cache_exact_rows": sum(
            as_bool(row[cache_exact_field], field=cache_exact_field) for row in rows
        ),
        "cache_max_abs_diff_median": median(float(row["cache_max_abs_diff"]) for row in rows),
        "cache_mean_abs_diff_median": median(float(row["cache_mean_abs_diff"]) for row in rows),
        "logits_exact_rows": sum(
            as_bool(row[logits_exact_field], field=logits_exact_field) for row in rows
        ),
        "logit_max_abs_diff_median": median(float(row["logit_max_abs_diff"]) for row in rows),
        "logit_mean_abs_diff_median": median(float(row["logit_mean_abs_diff"]) for row in rows),
        "immediate_argmax_different_rows": sum(
            not as_bool(row["boundary_argmax_equal"], field="boundary_argmax_equal") for row in rows
        ),
        "suffix_disagreement": rate_payload(suffix_mismatch.astype(bool)),
        "trace_disagreement": rate_payload(
            not as_bool(row["trace_equal"], field="trace_equal") for row in rows
        ),
        "merge_disagreement": rate_payload(
            not as_bool(row["merge_equal"], field="merge_equal") for row in rows
        ),
        "answer_disagreement": rate_payload(answer_mismatch.astype(bool)),
        "first_divergence": {
            "n": len(divergences),
            "min": min(divergences) if divergences else None,
            "median": median(divergences) if divergences else None,
            "max": max(divergences) if divergences else None,
        },
        "first_token_divergence_rows": sum(value == 0 for value in divergences),
        f"{left}_correct": int(correctness_left.sum()),
        "prefill_correct": int(correctness_right.sum()),
        "accuracy_delta_prefill_minus_left_pp": float(correctness_difference.mean() * 100.0),
        "accuracy_paired_bootstrap_95_ci_pp": bootstrap_mean_ci_pp(
            correctness_difference.astype(np.float64), stream=stream
        ),
        "correctness_label_disagreement": rate_payload(correctness_flip.astype(bool)),
        f"{left}_only_correct": left_only,
        "prefill_only_correct": right_only,
        "mcnemar_exact_two_sided_p": exact_mcnemar(left_only, right_only),
        "integrity_pass_rows": sum(
            as_bool(row["integrity_pass"], field="integrity_pass") for row in rows
        ),
    }
    if fixed:
        summary["cache_relative_l2_diff_median"] = median(
            float(row["cache_relative_l2_diff"]) for row in rows
        )
    return summary, {
        "suffix_mismatch": suffix_mismatch,
        "answer_mismatch": answer_mismatch,
        "correctness_flip": correctness_flip,
        "correctness_difference": correctness_difference,
        "logits_mismatch": logits_mismatch,
    }


def cross_precision(vectors: dict[str, dict[str, np.ndarray]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    streams = {
        "suffix_mismatch": 20,
        "answer_mismatch": 21,
        "correctness_flip": 22,
        "logits_mismatch": 23,
    }
    for endpoint, stream in streams.items():
        bf16 = vectors["bf16"][endpoint]
        fp32 = vectors["fp32"][endpoint]
        difference = fp32 - bf16
        bf16_only = int(np.count_nonzero(difference == -1))
        fp32_only = int(np.count_nonzero(difference == 1))
        result[endpoint] = {
            "bf16_count": int(bf16.sum()),
            "fp32_count": int(fp32.sum()),
            "delta_fp32_minus_bf16_pp": float(difference.mean() * 100.0),
            "paired_bootstrap_95_ci_pp": bootstrap_mean_ci_pp(
                difference.astype(np.float64), stream=stream
            ),
            "bf16_only": bf16_only,
            "fp32_only": fp32_only,
            "mcnemar_exact_two_sided_p": exact_mcnemar(bf16_only, fp32_only),
        }
    effect = vectors["fp32"]["correctness_difference"] - vectors["bf16"]["correctness_difference"]
    result["accuracy_effect_difference"] = {
        "delta_fp32_minus_bf16_pp": float(effect.mean() * 100.0),
        "paired_bootstrap_95_ci_pp": bootstrap_mean_ci_pp(effect.astype(np.float64), stream=30),
    }
    return result


def summarize_matrix(path: Path, *, fixed: bool) -> dict[str, Any]:
    rows = read_csv_exact(path, FIXED_HEADER if fixed else MATCHED_HEADER)
    grouped = validate_matrix_rows(rows, fixed=fixed)
    streams = {"bf16": 100 if fixed else 0, "fp32": 101 if fixed else 1}
    summaries: dict[str, Any] = {}
    vectors: dict[str, dict[str, np.ndarray]] = {}
    for precision in ("bf16", "fp32"):
        summaries[precision], vectors[precision] = matrix_precision_summary(
            grouped[precision], fixed=fixed, stream=streams[precision]
        )
    prefix_exact = sum(
        left["prefix_sha256"] == right["prefix_sha256"]
        and left["prefix_token_count"] == right["prefix_token_count"]
        for left, right in zip(grouped["bf16"], grouped["fp32"], strict=True)
    )
    output = {
        "cross_precision_prefix_exact_rows": prefix_exact,
        "bf16": summaries["bf16"],
        "fp32": summaries["fp32"],
    }
    if fixed:
        output["cross_precision"] = cross_precision(vectors)
    return output


def summarize_bridge() -> dict[str, Any]:
    rows = read_csv_exact(ROOT / "data/live_teacher_bridge.csv", BRIDGE_HEADER)
    if len(rows) != 12:
        raise VerificationError("prospective bridge must have 12 rows")
    for row in rows:
        validate_identity(
            row,
            "source_row_sha256",
            "new_prefix_sha256",
            "historical_prefix_sha256",
            "live_suffix_sha256",
            "teacher_suffix_sha256",
        )
        if int(row["boundary_cache_sequence_len"]) != int(row["new_prefix_token_count"]):
            raise VerificationError("bridge boundary length is inconsistent")
        if int(row["post_decode_cache_sequence_len"]) < int(row["boundary_cache_sequence_len"]):
            raise VerificationError("bridge post-decode cache length is invalid")
        if as_bool(row["live_teacher_suffix_exact"], field="bridge suffix") != (
            row["live_suffix_sha256"] == row["teacher_suffix_sha256"]
        ):
            raise VerificationError("bridge suffix commitment disagreement")
    new_lengths = [int(row["new_prefix_token_count"]) for row in rows]
    historical_lengths = [int(row["historical_prefix_token_count"]) for row in rows]
    return {
        "rows": len(rows),
        "integrity_pass_rows": sum(
            as_bool(row["integrity_pass"], field="integrity_pass") for row in rows
        ),
        "live_matches_historical_prefix_rows": sum(
            as_bool(
                row["live_matches_historical_prefix"],
                field="live_matches_historical_prefix",
            )
            for row in rows
        ),
        "new_prefix_length_range": [min(new_lengths), max(new_lengths)],
        "historical_prefix_length_range": [
            min(historical_lengths),
            max(historical_lengths),
        ],
        "live_teacher_cache_exact_rows": sum(
            as_bool(row["live_teacher_cache_exact"], field="cache exact") for row in rows
        ),
        "live_teacher_logits_exact_rows": sum(
            as_bool(row["live_teacher_logits_exact"], field="logits exact") for row in rows
        ),
        "live_teacher_suffix_exact_rows": sum(
            as_bool(row["live_teacher_suffix_exact"], field="suffix exact") for row in rows
        ),
        "all_48_layers_exact_rows": sum(
            as_bool(row["all_48_layers_exact"], field="all layers exact") for row in rows
        ),
    }


def summarize_historical_bridge() -> dict[str, Any]:
    rows = read_csv_exact(ROOT / "data/historical_bridge_audit.csv", HISTORICAL_HEADER)
    if len(rows) != 200:
        raise VerificationError("historical bridge must have 200 rows")
    fields = [
        "prefix_commitment_equal",
        "live_incremental_suffix_equal",
        "live_replica_suffix_equal",
        "prefill_suffix_equal",
        "prefill_replica_suffix_equal",
        "comparison_objects_equal",
        "cache_live_replica_fingerprint_equal",
        "cache_live_prefill_fingerprint_equal",
        "cache_prefill_replica_fingerprint_equal",
        "logits_live_replica_fingerprint_equal",
        "logits_live_prefill_fingerprint_equal",
        "logits_prefill_replica_fingerprint_equal",
        "audit_pass",
    ]
    for index, row in enumerate(rows):
        validate_identity(row, "source_live_row_sha256", "source_incremental_row_sha256")
        if row["row_id"] != f"r{index:04d}":
            raise VerificationError("historical bridge order drifted")
        if int(row["cache_common_scalar_leaves_per_section"]) != 1158:
            raise VerificationError("cache fingerprint schema drifted")
        if int(row["logit_common_scalar_leaves_per_section"]) != 14:
            raise VerificationError("logit fingerprint schema drifted")
    return {
        "rows": len(rows),
        **{
            f"{field}_rows": sum(as_bool(row[field], field=field) for row in rows)
            for field in fields
        },
        "cache_common_scalar_leaves_per_section": 1158,
        "logit_common_scalar_leaves_per_section": 14,
    }


def summarize_transplant(path: Path, *, checkpoint_alias: str) -> dict[str, Any]:
    rows = read_csv_exact(path, TRANSPLANT_HEADER)
    expected_rows = 32 if checkpoint_alias == "C0" else 48
    if len(rows) != expected_rows:
        raise VerificationError("transplant ledger row count is wrong")
    for row in rows:
        validate_identity(
            row,
            "source_row_sha256",
            "prefix_sha256",
            "incremental_native_suffix_sha256",
            "prefill_native_suffix_sha256",
            "incremental_cache_into_prefill_suffix_sha256",
            "prefill_cache_into_incremental_suffix_sha256",
        )
        if row["checkpoint_alias"] != checkpoint_alias:
            raise VerificationError("checkpoint alias drifted")
        baseline_divergent = (
            row["incremental_native_suffix_sha256"] != row["prefill_native_suffix_sha256"]
        )
        if as_bool(row["baseline_divergent"], field="baseline_divergent") != baseline_divergent:
            raise VerificationError("baseline divergence commitment disagreement")
        incremental_recovery = (
            row["incremental_cache_into_prefill_suffix_sha256"]
            == row["incremental_native_suffix_sha256"]
        )
        prefill_recovery = (
            row["prefill_cache_into_incremental_suffix_sha256"]
            == row["prefill_native_suffix_sha256"]
        )
        if (
            as_bool(row["incremental_cache_into_prefill_recovers_donor"], field="recovery")
            != incremental_recovery
        ):
            raise VerificationError("incremental donor recovery disagreement")
        if (
            as_bool(row["prefill_cache_into_incremental_recovers_donor"], field="recovery")
            != prefill_recovery
        ):
            raise VerificationError("prefill donor recovery disagreement")
        if not baseline_divergent:
            novel = not (incremental_recovery and prefill_recovery)
            if as_bool(row["exact_control_novel_trajectory"], field="novel trajectory") != novel:
                raise VerificationError("exact-control trajectory disagreement")
        for field in (
            "incremental_replica_exact",
            "prefill_replica_exact",
            "functional_state_equal",
            "boundary_argmax_equal",
            "all_storage_disjoint",
            "all_48_layer_pairs_transplanted",
            "integrity_pass",
        ):
            if not as_bool(row[field], field=field):
                raise VerificationError(f"transplant integrity failed: {field}")
    divergent = [row for row in rows if as_bool(row["baseline_divergent"], field="divergent")]
    exact = [row for row in rows if row not in divergent]
    incremental_recovery = [
        as_bool(row["incremental_cache_into_prefill_recovers_donor"], field="recovery")
        for row in divergent
    ]
    prefill_recovery = [
        as_bool(row["prefill_cache_into_incremental_recovers_donor"], field="recovery")
        for row in divergent
    ]
    joint_recovery = [
        as_bool(row["bidirectional_donor_recovery"], field="joint recovery") for row in divergent
    ]
    novel = [
        as_bool(row["exact_control_novel_trajectory"], field="novel trajectory") for row in exact
    ]
    z = 1.959963984540054
    return {
        "rows": len(rows),
        "integrity_pass_rows": sum(
            as_bool(row["integrity_pass"], field="integrity_pass") for row in rows
        ),
        "baseline_divergence": rate_payload((row in divergent for row in rows), z=z),
        "baseline_exact_rows": len(exact),
        "incremental_cache_into_prefill_donor_recovery": rate_payload(incremental_recovery, z=z),
        "prefill_cache_into_incremental_donor_recovery": rate_payload(prefill_recovery, z=z),
        "bidirectional_donor_recovery": rate_payload(joint_recovery, z=z),
        "exact_control_novel_trajectory": rate_payload(novel, z=z),
    }


def summarize_stock() -> dict[str, Any]:
    rows = read_csv_exact(ROOT / "data/stock_qwen_control.csv", STOCK_HEADER)
    if len(rows) != 10:
        raise VerificationError("stock control must have ten rows")
    for row in rows:
        validate_identity(row, "source_row_sha256")
    return {
        "rows": len(rows),
        "pair_replica_token_exact_rows": sum(
            as_bool(row["pair_replica_tokens_exact"], field="pair tokens") for row in rows
        ),
        "pair_replica_logprob_exact_rows": sum(
            as_bool(row["pair_replica_logprobs_exact"], field="pair logprobs") for row in rows
        ),
        "singleton_pair_token_exact_rows": sum(
            as_bool(row["singleton_pair_tokens_exact"], field="singleton tokens") for row in rows
        ),
        "singleton_pair_logprob_exact_rows": sum(
            as_bool(row["singleton_pair_logprobs_exact"], field="singleton logprobs")
            for row in rows
        ),
    }


def recompute() -> dict[str, Any]:
    matched = summarize_matrix(ROOT / "data/matched_live_prefill.csv", fixed=False)
    fixed = summarize_matrix(ROOT / "data/fixed_prefix_2x2.csv", fixed=True)
    return {
        "schema": "stage-replay-paper-claims-v1",
        "matched_live_prefill": matched,
        "fixed_prefix_2x2": fixed,
        "prospective_bridge": summarize_bridge(),
        "historical_bridge": summarize_historical_bridge(),
        "transplant_primary": summarize_transplant(
            ROOT / "data/kv_transplant_primary.csv", checkpoint_alias="C0"
        ),
        "transplant_later": summarize_transplant(
            ROOT / "data/kv_transplant_later.csv", checkpoint_alias="C1"
        ),
        "stock_qwen_diagnostic": summarize_stock(),
    }


def compare(expected: Any, actual: Any, *, path: str = "$") -> None:
    if isinstance(expected, dict):
        if not isinstance(actual, dict) or set(expected) != set(actual):
            raise VerificationError(f"claim keys differ at {path}")
        for key in expected:
            compare(expected[key], actual[key], path=f"{path}.{key}")
        return
    if isinstance(expected, list):
        if not isinstance(actual, list) or len(expected) != len(actual):
            raise VerificationError(f"claim list differs at {path}")
        for index, (left, right) in enumerate(zip(expected, actual, strict=True)):
            compare(left, right, path=f"{path}[{index}]")
        return
    if isinstance(expected, float):
        if not isinstance(actual, int | float) or not math.isclose(
            expected, float(actual), rel_tol=1e-12, abs_tol=1e-12
        ):
            raise VerificationError(f"numeric claim differs at {path}: {expected!r} != {actual!r}")
        return
    if expected != actual:
        raise VerificationError(f"claim differs at {path}: {expected!r} != {actual!r}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="verify frozen claims")
    parser.add_argument("--output", type=Path, help="optional JSON output path")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if np.__version__ != "2.4.2":
        raise VerificationError(
            f"NumPy 2.4.2 is required for exact bootstrap replay; found {np.__version__}"
        )
    verify_checksums()
    actual = recompute()
    if args.check:
        compare(load_json(ROOT / "paper_claims.json"), actual)
    rendered = json.dumps(actual, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    if args.check:
        print("PASS: all released checksums, schemas, and arXiv-v1 claims match.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
