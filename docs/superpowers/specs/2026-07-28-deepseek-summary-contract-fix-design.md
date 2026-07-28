# DeepSeek Summary Contract Fix

## Problem

The real Stage 4B acceptance run completed Brave search and fetched five public
sources, but failed during model generation. A minimal request to
`deepseek-v4-flash` returned HTTP 200, so the credential, balance, endpoint,
model, and JSON Output feature are valid. The remaining failure boundary is the
model response contract or its validation.

## Considered approaches

1. **Prompt-only contract (selected).** Give the model an exact JSON shape,
   field types, limits, and example; keep Pydantic as the final trust-boundary
   validator. This is the smallest provider-compatible change.
2. Add provider-specific response parsing and coercion. This could hide invalid
   model output and makes the OpenAI-compatible adapter less portable.
3. Replace JSON Output with tool/function calling. This adds schema machinery
   and provider-specific behavior that Stage 4B does not need.

## Design

- Keep the existing OpenAI-compatible `/chat/completions` adapter.
- Replace the loose field-name instruction with one explicit JSON example:
  `overview` is a string and every other requested content field is an array of
  strings. The model must not return `sources`; trusted source metadata remains
  attached by CareerPilot.
- Send `thinking: {"type": "disabled"}` for DeepSeek V4 models only. Other
  OpenAI-compatible models receive no provider-specific parameter.
- Classify failures locally as `model_http`, `model_empty`, `model_json`, or
  `model_schema`. Store only the category in the Job's safe error message; do
  not store upstream response bodies, prompts, source text, or credentials.
- Preserve the current checkpoint and resume behavior. Retrying the failed Job
  reuses the five fetched sources and does not repeat Brave calls.

## Verification

- Unit test the exact request payload for DeepSeek and a generic compatible
  model.
- Test empty, malformed JSON, and wrong-shaped output categories without
  persisting sensitive response data.
- Run all backend tests and Ruff.
- Resume the existing failed ArcSoft Job and verify one Summary version plus
  its Markdown file.

## Non-goals

- No provider SDK or new dependency.
- No automatic bulk Summary generation.
- No retry loop beyond the existing explicit Job resume.
- No storage of model reasoning content.
