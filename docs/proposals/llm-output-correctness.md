# Proposal: LLM Output Correctness

**Status:** proposed. Phase 0 (surface-filtered gloss candidates) is implemented; phases 1–4 are not.

Prevent LLM output from breaking the pipeline (malformed JSON, schema violations, broken cross-references) **at the call site**, instead of adding post-hoc normalization.

## Motivation

The gloss job asks the model to mint ids in `newGlosses[].id` and repeat them in `glossDecisions[].glossId`. Models sometimes emit `glossId: "new"` while `newGlosses` uses `new-001`, so status and assembly cannot resolve the gloss. The output parses and passes Pydantic validation; it is a **cross-field consistency violation** that the response shape makes possible. Id generation belongs to deterministic code.

The layers below stack. Each removes a failure class so the next fires rarely. Deterministic promote-time validation remains the final gate.

## Layer 1: Make invalid output unrepresentable

Give each job a dedicated **response schema** ("wire model"), separate from the artifact schema. The model returns only what it decides; code constructs the artifact.

Gloss job example:

```json
{
  "decisions": [
    { "tokenId": "…", "reuseGlossId": "existing-candidate-id" },
    { "tokenId": "…", "newGloss": { "pinyin": "jiàng", "gloss": "general; commander" } }
  ]
}
```

- `create-new` carries pinyin/gloss inline, so there is no id to mismatch. Code mints UUIDs, builds `newGlosses` / `newGlossIds`, dedupes via `normalize_gloss_reuse`, and assembles `GlossesArtifact`.
- Drop echo fields (`segmentId`, `inputHash`, `model`, `attempts`) from response schemas. `segment_runner.stamp_segment_metadata` already overwrites them.

Cost: one wire model per job alongside the artifact model.

## Layer 2: Enforce the schema at the API

- **Anthropic:** structured outputs (`output_config.format = {type: "json_schema", schema: …}`) guarantee schema-valid JSON. Requires `additionalProperties: false` and full `required` arrays; oversized schemas return 400.
- **MiniMax** (Anthropic-compatible endpoint): no `output_config.format`, but supports `tools` + `tool_choice`. Use **forced tool use** with one tool whose `input_schema` is the response schema.

Anthropic also supports forced tool use (`strict: true`), so forced tools can be the **single code path for both providers**, keeping the shared client implementation. `extract_json_text` fence-stripping becomes unnecessary on enforced paths.

Optional hardening: build `reuseGlossId` as an `enum` of the segment's candidate gloss ids per request. Depends on candidate filtering keeping the schema small.

## Layer 3: Validate-and-refeed retries

Some invariants exceed schema expressiveness (exactly one decision per token, tone-marked pinyin). Validate in code; on failure, continue the same conversation with the model's response as an assistant turn plus a user turn listing concrete violations, and ask it to re-emit. Bound at 2–3 attempts, then fail the job.

Today `AnthropicLLMClient` re-sends the identical prompt on `LLMParseError`; without feedback, those retries mostly burn tokens.

## Failure classes

| Failure class | Prevented by |
|---|---|
| Markdown fences, prose, truncated JSON | Layer 2 |
| Missing fields, wrong types | Layer 2 |
| Broken id cross-references | Layer 1 |
| Nonexistent candidate ids | Layer 2 enum (optional) |
| Semantic violations (coverage, pinyin) | Layer 3, then promote-time validation |

## Rollout

| Phase | Change | Status |
|---|---|---|
| 0 | Filter gloss prompt candidates to surfaces present in the segment | implemented |
| 1 | Gloss wire model + assembler; code mints ids | proposed |
| 2 | Forced tool use in both clients; remove JSON-extraction on enforced paths | proposed |
| 3 | Bounded feedback-retry loop; stop blind parse retries | proposed |
| 4 | Wire models for remaining LLM jobs; strip echo fields from prompts | proposed |

Risks: Anthropic schema size limits (slim wire models); MiniMax tool strictness is weaker (keep Layer 3 validators); on-disk artifact shapes are unchanged, so existing preprocess artifacts stay valid.
