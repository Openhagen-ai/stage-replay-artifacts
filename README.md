# Stage-Replay Artifacts

Claim-verification artifacts for **Stage-Replay Divergence Follows the KV
Cache: Fixed-Prefix Precision Controls and Bidirectional Cache
Transplantation**.

- **Paper:** [arXiv:2607.28495v1](https://arxiv.org/abs/2607.28495v1)
- **Artifact release:** `v1.0.0`
- **Citation metadata:** [`CITATION.cff`](CITATION.cff)
- **Field definitions:** [`DATA_DICTIONARY.md`](DATA_DICTIONARY.md)

> [!IMPORTANT]
> This is a claim-verification release, not an end-to-end model-reproduction
> package. It supports independent recomputation of the paper's reported
> statistics and integrity checks. The two adapted checkpoints are identified
> by cryptographic digests but are not distributed.

## Verified headline results

The bundled analyzer recomputes the following endpoints from the public
ledgers:

| Experiment | Recomputed result |
|---|---|
| Fixed-prefix BF16 crossing | 166/200 suffixes, 49/200 answers, and 20/200 correctness labels differ; both construction-specific replica pairs are exact on 200/200 rows |
| Fixed-prefix FP32 crossing | 0/200 suffix, answer, or correctness-label disagreements on the tested prefixes; the 95% Wilson upper bound is 1.9% |
| Prospective live/incremental bridge | Cache tensors across all 48 layers, boundary logits, and decoded suffixes are exact on 12/12 rows |
| Whole-cache transplantation | Bidirectional donor recovery is 24/24 on the primary panel and 43/43 on the outcome-blind later-checkpoint panel; naturally exact controls produce no new trajectory on 0/8 and 0/5 rows |

These are claim-level checks over the released evidence, not an independent
regeneration of model trajectories.

## Quick verification

Use Python 3.12 and the pinned dependency in
[`requirements.txt`](requirements.txt). Run the verifier from a **clean GitHub
Download ZIP or release-archive extraction**, not from a Git checkout:
fail-closed verification rejects unlisted files, including `.git` metadata.

```bash
python3 -m venv ../stage-replay-release-venv
../stage-replay-release-venv/bin/pip install -r requirements.txt
../stage-replay-release-venv/bin/python analysis/recompute.py --check
```

A successful run independently recomputes the frozen claims in
[`paper_claims.json`](paper_claims.json), including central counts, Wilson
intervals, paired bootstrap intervals, exact McNemar tests, cache-drift
medians, bridge results, and bidirectional transplantation outcomes.

The check fails on an unlisted or modified file, checksum mismatch, schema
drift, missing row, changed row order, failed integrity gate, or disagreement
with a frozen claim.

## Evidence included

| Component | Public evidence |
|---|---|
| Retained-live vs. fresh-prefill comparison | 400 row-level observations: 200 per precision |
| Fixed-prefix precision crossing | 400 row-level observations with aggregate per-item cache-drift summaries |
| Live/incremental bridge | 12 prospective rows plus a 200-row historical trajectory and numerical-fingerprint audit |
| Full-cache transplantation | Six-arm ledgers for the 32-row primary panel and 48-row outcome-blind later-checkpoint panel |
| Public-stock diagnostic | Ten-row Qwen2.5-14B-Instruct batch-composition control |
| Statistical contract | Frozen analysis plan, expected claims, and standalone recomputation code |

### Repository map

- [`analysis/recompute.py`](analysis/recompute.py) — standalone verifier and
  claim recomputation;
- [`analysis_plan.json`](analysis_plan.json) — frozen analysis and uncertainty
  contract;
- [`paper_claims.json`](paper_claims.json) — machine-readable claims bound to
  arXiv v1;
- [`data/`](data/) — sanitized row-level evidence tables;
- [`release_manifest.json`](release_manifest.json) — environment,
  checkpoint-digest, numerical, decode, cache, population, and arXiv bindings;
- [`redaction_receipt.json`](redaction_receipt.json) — auditable record of the
  public transformation;
- [`SHA256SUMS`](SHA256SUMS) — file-level integrity manifest.

## Disclosure boundary

Rows use opaque identifiers `r0000` through `r0199` in the paper's frozen GPQA
Main order. Exact token sequences are represented by token counts and SHA-256
commitments. Source-row hashes commit to the corresponding private records;
they are not independently invertible or verifiable from this public package
alone.

| Included | Not included |
|---|---|
| Opaque row-level outcomes and integrity fields | Benchmark text, prompts, generated reasoning, or reversible token arrays |
| Sequence lengths and SHA-256 commitments | Real problem-ID mapping |
| Aggregate absolute and relative cache-drift summaries | Full cache tensors or logits |
| Redacted execution and checkpoint-digest contracts | Adapted model weights |
| Frozen analysis plan and complete statistical analyzer | Training data, lineage, code, or private generation runners |

The release therefore supports arithmetic and statistical verification plus
provenance commitments. It does **not** support content-level rescoring or
end-to-end regeneration. Exact reruns require digest-matching adapted
checkpoints and the private execution layer.

## Relationship to Section 3.9 of arXiv v1

Section 3.9 of arXiv v1 described a broader prospective release containing the
frozen problem-ID order, exact boundary-prefix and suffix token IDs, and
primary generation harnesses. This public release instead uses opaque
frozen-order row IDs, sequence commitments, row-level outcome labels,
numerical summaries, source-artifact digests, private-row audit commitments,
and the complete analyzer.

The narrower boundary avoids distributing benchmark-reconstructing token
arrays and checkpoint-coupled private implementation unrelated to the paper's
reported claims. The replacement manuscript corrects the release description
accordingly.

<details>
<summary><strong>Bridge cache-length field clarification</strong></summary>

In the private prospective-bridge ledger, one serialized cache-length field
was captured after suffix decoding had extended the mutable cache. The public
ledger names this value `post_decode_cache_sequence_len`. Its
`boundary_cache_sequence_len` is derived from the pre-decode comparison-tensor
metadata and equals the fixed-prefix length.

This transformation is recorded in
[`redaction_receipt.json`](redaction_receipt.json) and does not affect the
reported 12/12 tensor-identity result.

</details>

## Integrity and version binding

[`release_manifest.json`](release_manifest.json) records the exact SHA-256
hashes of the official arXiv-v1 PDF, source archive, and manuscript TeX,
together with every digest method. [`SHA256SUMS`](SHA256SUMS) binds the files
within this snapshot. For an immutable hosting-level citation, use the exact
repository commit or release tag together with [`CITATION.cff`](CITATION.cff).

## Citation

Please cite both the [paper](https://arxiv.org/abs/2607.28495v1) and this
artifact release. GitHub exposes the repository citation from
[`CITATION.cff`](CITATION.cff).

## License

Code under [`analysis/`](analysis/) is licensed under the MIT License. Derived
evidence tables and release documentation are licensed under
[CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). See
[`LICENSE`](LICENSE) for details.

No benchmark text, model weights, training data, or training lineage is
included.
