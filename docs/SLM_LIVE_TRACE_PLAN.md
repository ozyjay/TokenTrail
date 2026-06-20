# SLM Live Trace Plan

The supported live small-language-model path is the local Hugging Face Transformers trace server. It returns the same replayable structure as scripted traces, with real prompt tokens, generated tokens, candidate alternatives, and probabilities.

## Behaviour

- HF trace mode accepts staff-entered prompts.
- Scripted mode never accepts staff-entered prompts; reset and runtime switching should restore the curated prompt view.
- Generated traces replay at the selected browser speed.
- The trace server trims to the first complete sentence after at least eight generated steps.
- Incomplete traces fail closed so Token Trail can show the scripted fallback payload.

## Commands

```powershell
pwsh -NoProfile -File ./scripts/probe_hf_trace.ps1 --candidate-source forward-logits
pwsh -NoProfile -File ./scripts/serve_hf_trace.ps1 --candidate-source forward-logits
```
