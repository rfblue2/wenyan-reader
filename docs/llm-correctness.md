# LLM Output Correctness

How to prevent LLM output from breaking the pipeline (malformed JSON, schema violations, broken cross-references) **at the call site**, instead of adding post-hoc normalization steps. Motivated by the gloss decision ↔ entry linking bug in [code-audit.md](code-audit.md): the model emits `glossDecisions[].glossId: "new"` while `newGlosses` uses different ids, so status and assembly cannot resolve the gloss.

That bug is not a formatting error — the output parses and passes Pydantic validation. It is a **cross-field consistency violation**, possible only because the response shape asks the model to mint UUIDs in one array and repeat them exactly in two others. [Model strategy](../architecture/preprocessing/model-strategy.md) already assigns UUID generation to deterministic code; the current `segment-gloss.md` prompt contradicts that.

The layers below stack. Each one removes a failure class so the next fires rarely; the existing deterministic promote-time validation ([architecture-audit.md](architecture-audit.md) §2.1–2.2) remains the final gate but becomes a near-never-firing assertion.

## 1. Make invalid output unrepresentable (highest leverage, no API features)

Give each job a dedicated **response schema**, separate from the artifact schema. The model returns only what it decides; deterministic code constructs the artifact.

For the gloss job:

```json
{
  "decisions": [
    { "tokenId": "…", "reuseGlossId": "existing-candidate-id" },
    { "tokenId": "…", "newGloss": { "pinyin": "jiàng", "gloss": "general; commander" } }
  ]
}
```

- `create-new` carries pinyin/gloss **inline** — there is no id to mismatch. Code mints UUIDs, builds `newGlosses` / `newGlossIds`, dedupes via `normalize_gloss_reuse`, and assembles `GlossesArtifact`.
- Drop echo fields (`segmentId`, `inputHash`, `model`, `attempts`) from response schemas. `segment_runner.stamp_segment_metadata` already overwrites them; asking the model to echo them only adds failure modes (architecture audit §3.3) and schema bulk.

Apply the same pattern to every LLM-calling job. Trade-off: one extra "wire model" per job alongside the artifact model — consistent with existing [coding style](../architecture/coding-style.md) layering.

## 2. Enforce the schema at the API level

The API analog of a CLI that rejects wrongly formatted output. Providers differ:

- **Anthropic (production):** GA **structured outputs** — pass `output_config.format = {type: "json_schema", schema: …}` on `/v1/messages`. Constrained decoding *guarantees* the response is valid JSON matching the schema: no fences, no prose, no missing fields. `extract_json_text` stripping and the "respond with a single JSON object only" system-prompt plumbing become unnecessary on this path. Requirements: `additionalProperties: false` and full `required` arrays on every object (thin wrapper over `model_json_schema()`), and schemas must stay small — oversized schemas fail with a 400 ("compiled grammar too large"), another reason to strip echo fields.
- **MiniMax (dev, Anthropic-compatible endpoint):** does **not** support `output_config.format`, but fully supports `tools` + `tool_choice`. Use **forced tool use**: define one tool (e.g. `emit_gloss_response`) whose `input_schema` is the response schema, set `tool_choice: {"type": "tool", "name": "…"}`, read the `tool_use` block. Tool arguments are far more reliably schema-shaped than free text, though on MiniMax this is a strong constraint rather than a hard guarantee.

Since Anthropic also supports forced tool use (with `strict: true` for a hard guarantee), the forced-tool shape can be the **single code path for both providers**, preserving the current shared `AnthropicLLMClient` / `MiniMaxLLMClient` implementation.

Optional hardening: schemas are built per request, so `reuseGlossId` can be an **`enum` of the segment's actual candidate gloss ids** — under constrained decoding the model cannot reference a nonexistent gloss. Interacts with schema-size limits, so best after candidate filtering (architecture audit §3.2) shrinks the list.

## 3. Validate-and-refeed retries for semantic invariants

Some invariants remain outside schema expressiveness: exactly one decision per token id, tone-marked pinyin. Pattern: parse and validate in code; on failure, continue the **same conversation** — append the model's response as an assistant turn plus a user turn listing the concrete violations ("token t-7 has no decision") — and ask it to re-emit. Bound at 2–3 attempts, then fail the job (resumable as usual).

Note: the current retry loop in `AnthropicLLMClient` re-sends the identical prompt on `LLMParseError`. Without the error fed back, the model has no reason to answer differently, so those retries mostly burn tokens. With layers 1–2 in place this loop should fire rarely.

## Summary of failure classes and owners

| Failure class | Prevented by |
|---|---|
| Markdown fences, prose, truncated JSON | Constrained decoding / forced tool use (2) |
| Missing fields, wrong types | Constrained decoding / forced tool use (2) |
| Broken id cross-references (gloss linking bug) | Response schema restructuring (1) |
| Referencing nonexistent candidate ids | Per-request `enum` constraint (2, optional) |
| Semantic violations (coverage, pinyin quality) | Feedback retry loop (3), then promote-time validation |

## Implementation order

1. Restructure the gloss response schema (pilot); code mints ids and assembles the artifact. Closes the code-audit "High" item without a normalizer.
2. Switch clients to forced tool use (both providers) or `output_config.format` (Anthropic); delete JSON-extraction regex handling on enforced paths.
3. Add the bounded feedback-retry loop to the client.
4. Roll the response-schema split out to the remaining jobs; strip echo fields from prompts and templates.
