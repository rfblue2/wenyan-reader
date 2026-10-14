# Proposal: Model Routing

**Status:** proposed. Today one provider and model serve every LLM job ([Jobs and LLM](../architecture/jobs-and-llm.md#llm-clients)). Backlog: F5, F8.

Route each LLM job to a model suited to its role, so reviews are independent of drafts and cost scales with how much a call matters.

## Roles

| Role | Model class | Used for |
|---|---|---|
| **Primary** | Strongest available Claude Opus (target: Opus 4.8) | Paragraph discovery, segmentation, tokenization, gloss selection and new glosses, grammar notes, context notes, all reviews |
| **Long-context** | Gemini Pro-class | Only tasks that need large surrounding context: chapter summaries, source synthesis. Never a whole document in one paragraph or segment job. |
| **Cost fallback** | Cheaper model (e.g. MiniMax) | Non-authoritative drafting only. Never reviews or quality jobs. |

Reviews use a different model (or at least a different provider) from the draft they check, so errors are not correlated: a model that picks the wrong reading of 將 is likely to approve it too.

## Configuration

```yaml
models:
  profiles:
    dev:  {draft: minimax/MiniMax-M2.5-highspeed, review: minimax/MiniMax-M2.5-highspeed}
    prod: {draft: anthropic/claude-opus-4-8, review: anthropic/claude-opus-4-8, longContext: google/gemini-pro}
  profile: dev
```

Each job declares a role; `bootstrap` resolves role → client. The `LLMClient` port is unchanged, so providers stay swappable without touching job logic. `mock` remains the default and serves every role.

## Deterministic work stays in code

Never route these to a model:

- Normalization
- **UUID generation** — today the model mints paragraph, segment, token, note, and gloss ids (backlog G-C6)
- Source and input hashes
- **Token offset validation** (backlog G-C2)
- Schema and path validation
- Packaging
- Retry and cache bookkeeping

## Lexicons first

Look up deterministic dictionaries or curated lexicons before LLM gloss calls when that cuts cost without lowering quality. The model then handles only unresolved or context-sensitive senses.

## Call contract

Every call requests strict structured output for the fields it needs (spans, segments, tokens with offsets, gloss reuse or new glosses with pinyin, anchored notes with sources, review findings). Malformed output is rejected; the command exits non-zero so the editor can rerun. Enforcement design: [LLM output correctness](llm-output-correctness.md).
