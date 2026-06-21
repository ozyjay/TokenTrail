# SLM Live Trace Plan

The supported live small-language-model path is the primary local Hugging Face Transformers trace server. It returns the same replayable structure as scripted traces, with real prompt tokens, generated tokens, top returned candidate alternatives, and probabilities.

## Behaviour

- HF trace mode accepts staff-entered prompts.
- Scripted mode is the mandatory fallback and secondary prepared mode. It never accepts staff-entered prompts; reset and runtime switching should restore the curated prompt view.
- Generated traces replay at the selected browser speed.
- The trace server trims to the first complete sentence after at least eight generated steps.
- Incomplete, slow, unavailable, or not-ready HF traces fail closed so Token Trail can show the scripted prepared fallback payload.
- Public wording should say the bars show top returned token alternatives from the local model, not private reasoning.

## Commands

```powershell
pwsh -NoProfile -File ./scripts/probe_hf_trace.ps1 --candidate-source forward-logits
pwsh -NoProfile -File ./scripts/serve_hf_trace.ps1 --candidate-source forward-logits
```
