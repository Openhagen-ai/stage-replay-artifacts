# Data dictionary

All CSV files are UTF-8 with one header row. Booleans are the lowercase strings
`true` and `false`; an empty divergence index means no observed divergence.
Every `*_sha256` value is lowercase hexadecimal.

## Sequence commitments

Private token sequences are hashed as canonical JSON: UTF-8 encoding,
`ensure_ascii=True`, sorted object keys, and separators `(',', ':')`. Token
arrays are never included. Matching commitments therefore support equality
checks without disclosing the sequence.

## Matrix ledgers

`matched_live_prefill.csv` records retained-live versus one-shot-prefill rows.
`fixed_prefix_2x2.csv` records token-by-token incremental versus one-shot
prefill rows on the same 200 fixed prefixes at BF16 and FP32. Replica columns
refer to independent, storage-isolated copies. `answer_equal` is exact equality
of extracted answer blocks; correctness columns are deterministic scorer labels.

## Cache-drift fields

`fixed_prefix_2x2.csv` contains the per-item boundary-cache maximum absolute,
mean absolute, delta-L2, source-L2, and relative-L2 summaries needed for the
reported aggregate comparisons. Relative L2 is delta L2 divided by the larger
of the two source norms. Raw cache tensors and logits are not included.

## Bridge ledgers

`live_teacher_bridge.csv` compares ordinary retained live cache with
token-by-token reconstruction on twelve newly reached shared prefixes.
`historical_bridge_audit.csv` records per-item equality results from joining the
private historical and reconstructed ledgers. The 1,158/14 common-leaf counts
are provenance-bound audit results; the compact public rows do not reproduce
all private leaves individually.

## Transplant ledgers

The two `kv_transplant_*.csv` files contain only the six registered full-cache
arms: two incremental replicas, two prefill replicas, and one full K/V swap in
each direction. `incremental_cache_into_prefill` means the recipient was the
prefill state and all 48 K/V layer pairs came from the incremental donor. The
ledgers contain exactly these six claim-scoped arms.

## Stock-model diagnostic

`stock_qwen_control.csv` reports singleton-versus-pair and pair-replica token
and selected-token-log-probability equality for ten inputs. It changes batch
composition, not cache construction, and is not a stock-model stage-replay
replication.
