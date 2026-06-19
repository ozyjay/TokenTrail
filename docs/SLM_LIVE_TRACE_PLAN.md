# SLM Live Trace Plan

**Project:** Token Trail  
**Status:** Pivoted to custom Hugging Face Transformers server  
**Last updated:** 2026-06-20

---

## Current decision

The preferred SLM live-trace path is now a **custom Hugging Face Transformers trace server**, not Ollama logprobs or vLLM.

Use this detailed plan:

```text
docs/HF_TRANSFORMERS_TRACE_SERVER_PLAN.md
```

---

## Backend roles

```text
Scripted trace mode: mandatory fallback and primary teaching mode
Ollama: simple local live text mode
HF Transformers trace server: preferred planned live token-trace path
vLLM: stretch/deferred desktop experiment
```

---

## Why this changed

Ollama live text remains useful, but local logprob probing did not return the token alternatives needed for a replayable live trace on the tested Qwen3 models.

vLLM has clearer logprob support, but it is heavier than needed for the local laptop workflow and public booth prototype.

A custom HF Transformers server gives Token Trail direct control over generated token IDs, per-step scores, top returned alternatives, trace conversion, and fallback behaviour.

---

## Open Day rule

```text
Scripted trace mode remains mandatory.
HF live trace mode is optional until proven reliable.
Ollama live text mode remains available.
```

Do not make the public demo depend on HF live trace unless it is proven on the final machine during rehearsal.
