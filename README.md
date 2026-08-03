# Stage-replay arXiv-v1 claim-verification bundle

This archive is the claim-scoped evidence release for **Stage-Replay Divergence Follows the KV Cache: Fixed-Prefix Precision Controls and Bidirectional Cache Transplantation**,
[arXiv:2607.28495v1](https://arxiv.org/abs/2607.28495v1).

It supports independent recomputation of the central reported counts, Wilson
intervals, paired bootstrap intervals, McNemar tests, drift medians, bridge
counts, and bidirectional transplantation outcomes enumerated in
`paper_claims.json`.  It is not an end-to-end model reproduction package: the
two adapted checkpoints are identified by cryptographic digests but are not
distributed.

## Verify

Use Python 3.12 and the pinned NumPy version:

```bash
python3 -m venv ../stage-replay-release-venv
../stage-replay-release-venv/bin/pip install -r requirements.txt
../stage-replay-release-venv/bin/python analysis/recompute.py --check
```

Keep the virtual environment outside this directory: the verifier deliberately
rejects files that are not listed in `SHA256SUMS`.

The command fails closed on an unlisted file, checksum mismatch, schema drift,
missing row, failed integrity gate, changed row order, or disagreement with any
frozen arXiv-v1 claim in `paper_claims.json`.

## Included

- redacted environment, numerical, decode, cache, checkpoint-digest, and
  population contracts;
- 400 row-level retained-live/prefill observations (200 per precision);
- 400 row-level fixed-prefix observations with per-item aggregate cache-drift
  summaries;
- the 12-row prospective live/incremental bridge;
- a 200-row historical trajectory and numerical-fingerprint audit;
- six-arm, full-cache-only transplantation ledgers for the 32-row primary panel
  and 48-row outcome-blind later panel;
- the ten-row public-stock-model batch-composition diagnostic;
- a standalone analyzer and frozen expected claims.

Rows use opaque identifiers `r0000` through `r0199` in the paper's frozen
GPQA Main order.  Sequence contents are represented by their token counts and
SHA-256 commitments.  Source-row hashes record private audit commitments; they
can be checked against the private ledgers and sanitizer but are not
independently invertible or verifiable from this public package alone.

## Explicit correction to the v1 release description

Section 3.9 of arXiv v1 says that the frozen problem-ID order, exact
boundary-prefix and suffix token IDs, and primary generation harnesses would
be released.  The real problem-ID mapping, reversible token arrays, and
generation runners are intentionally not present here.  With the public
tokenizer, those token arrays reconstruct benchmark questions, formatting,
and complete generated reasoning.  The private generation runners also
contain checkpoint-coupled code unrelated to the claims in this paper.  This
bundle instead releases opaque frozen-order row IDs, sequence commitments,
row-level outcome labels, numerical summaries, source-artifact digests,
private-row audit commitments, and the complete statistical analyzer.  The
narrower boundary should be stated in the next arXiv version.

Consequently, this archive supports arithmetic and statistical verification
plus provenance commitments, not independent regeneration or content-level
rescoring.  Exact reruns require access to digest-matching adapted checkpoints
and the private execution layer.

## Important bridge-field clarification

In the private prospective-bridge ledger, one serialized cache-length field was
captured after suffix decoding had extended the mutable cache.  The public
ledger names that value `post_decode_cache_sequence_len`.  Its
`boundary_cache_sequence_len` is derived from the pre-decode comparison tensor
metadata and equals the fixed-prefix length.  This transformation is recorded
in `redaction_receipt.json`; it does not change the 12/12 tensor-identity result.

## Binding

`release_manifest.json` binds this package to the exact official arXiv-v1 PDF,
source archive, and manuscript TeX hashes and states each digest method.
`SHA256SUMS` binds every other file inside the archive.  The accompanying
external checksum and receipt bind the complete archive `stage-replay-arxiv-2607.28495v1-verification-v1.0.0.tar.gz`
itself.  A repository commit, immutable tag, and version DOI should be recorded
on the hosting release page rather than fabricated inside this pre-publication
archive.

## License

The analysis code is MIT-licensed.  The derived evidence tables and release
documentation are licensed under CC BY 4.0.  No benchmark text, model weights,
training data, or training lineage is included.
