# LLM extractor evaluation

## Gold schema (`GoldCausalAnnotationV1`)

`src/aionis/schema/gold_annotation.py` defines the frozen gold record for
E3 causal-edge evaluation. It reuses `CausalEdge` directly and does not store
ERL free text, market impact, future returns, or model predictions.

Each record has exactly one of two states:

- one `CausalEdge`, with `abstention_reason=null` and `adjudicated=true`;
- no edge, with a non-null `abstention_reason`.

`abstention_reason="adjudication_pending"` marks unresolved disagreement and
must set `adjudicated=false`. Pending records are not evaluable gold.

`annotator_ids` must be non-empty, sorted, and de-duplicated. `source_text_sha256`
must be a 64-character hex digest, and `source_span_end` must be strictly greater
than `source_span_start`.
