# Copilot Global Instructions — Synapsera / AI Brain
**Use this file to guide GitHub Copilot behaviour for the entire repository.**
Goal: produce industry-grade, secure, tested, production-ready code for FastAPI + Celery + Redis + RAG systems — *while* allowing Copilot to innovate and propose alternatives with clear justification.

---

## 0. How to use these rules
1. Treat **"MANDATORY"** rules as non-negotiable constraints for generated code.  
2. Treat **"PREFERRED"** rules as strong recommendations. Copilot SHOULD follow them but may propose alternatives.  
3. If proposing alternatives to a MANDATORY rule, Copilot must include an **explicit DESIGN NOTE** explaining why the alternative is safer/better and list trade-offs.  
4. If a human asks Copilot to “override rules”, Copilot must output a short **RISK & MITIGATION** section and unit-test stubs for the change.

---

## 1. Mandatory (non-negotiable)
- **No secrets** in code. All keys/secrets must come from environment variables or a secret manager.  
- **Never** log PII (user full messages, emails, phone numbers, raw file contents). If logging is necessary, redact/hash.  
- **All long-running operations MUST be background tasks** (Celery, SQS, or approved queue). No blocking work in HTTP handlers.  
- **Redis MUST require AUTH + TLS in production**. Code must assert this when `ENV=production` and fail fast if insecure.  
- **File uploads**: validate magic bytes, MIME, max-size; store with UUID filenames in a temp dir; always delete temporary files after processing.  
- **Idempotency**: ingestion tasks must detect and skip duplicate documents (checksum or dedupe key).  
- **Task retry policy**: every Celery task must include sensible retry/backoff/jitter configuration or reference a shared retry helper.  
- **Sentry (or equivalent)** must be pluggable; only enabled in non-dev by env. Exceptions must be captured with context IDs.  
- **Tests required**: any generated feature must include at least unit tests for core logic and CI steps to run them.

---

## 2. Preferred (strong guidance)
- Use **async endpoints** (FastAPI) and Pydantic models for validation.  
- Use structured JSON logging (structlog or JSONFormatter) and include `correlation_id`/`task_id` in logs.  
- Use a clean module structure: `app/routes`, `app/tasks`, `app/services`, `app/utils`.  
- Batch embedding calls; prefer reuse of an `EmbeddingClient` wrapper with retry and rate-limit awareness.  
- Chunking should be semantic-first with fallback to fixed-size windows and overlap; store provenance metadata for each chunk.  
- Provide docstrings, type hints, simple examples in public functions.

---

## 3. Innovation & "Think Beyond" policy (explicit permission)
Copilot IS ALLOWED and ENCOURAGED to:
- Propose alternative architectures (e.g., SQS vs Redis vs Kafka, or RQ vs Celery) when it improves reliability, cost, or latency.  
- Suggest performance optimizations (quantization, ONNX, batching strategies, flashattention where relevant) with pragmatic trade-offs.  
- Propose richer ingestion alternatives (layout-aware extraction, table parsers, graph-RAG) and explain integration steps.  

When Copilot proposes any alternative it must output:
1. **DESIGN NOTE (short)** — what is the proposed change.  
2. **WHY (bullet points)** — concrete benefits vs current rules.  
3. **TRADE-OFFS (bullet points)** — cost, complexity, lock-in, operational burden.  
4. **SAFETY MITIGATION** — how to implement safely under current mandatory constraints (tests, feature flags, env gating).  
5. **MIGRATION PLAN (if applicable)** — stepwise plan to adopt the alternative with minimal risk.

---

## 4. Override flow (how humans instruct Copilot to deviate)
When a developer wants Copilot to intentionally deviate:
- Prefix the prompt with: `OVERRIDE_RULES: <short reason>`  
- Include required outputs: `RISK_ASSESSMENT`, `TESTS`, `ROLLBACK_PLAN`.  
- Example instruction to Copilot:  
