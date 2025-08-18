Here you go—drop this into a file like `FUNCTIONAL_SPEC.md` (or `DESIGN.md`) in your repo.

# LLM Email Router & Runner — Functional Description

> **Note**: This system is designed to be generic and can be used with different types of business emails and API systems, not limited to any specific domain.

## Purpose

Process a JSONL dataset of business emails with a **single controller** that routes each email to either a **fast agent (S1)** or a **deliberative agent (S2)**. The chosen agent analyzes the email and determines the appropriate API action sequence. The runner writes an **enriched copy** of the dataset with routing + agent output for later analysis.

---

## Scope (v1)

* **One controller** (LLM-based heuristic) → decides `S1` or `S2`.
* **Two agents** sharing the same base class; they differ only in **model** and **prompt**.
* **No in-place edits** to the source dataset. Output goes to `runs/<run_id>/merged.jsonl`.
* Minimal fields; **no timing/cost** metrics.

Non-goals (v1): retrieval, real API calls, multi-controller comparisons, fancy UI.

---

## Inputs & Outputs

### Input dataset (JSONL)

Each line is an object with at least:

```json
{
  "id": "train-000123-a1b2c3d4",
  "email_text": "...",
  "action_sequence": [...],
  "controller_label": "S2",
  "rationale_gt": "...",
  "metadata": {...}
}
```

> Only `id` and `email_text` are required by the runner. The rest are ground truth for later eval.

### Enriched output (JSONL)

For each input line, runner writes:

```json
{
  "... original fields ...": "...",
  "run": {
    "route_pred": "S1" | "S2",
    "agent": {
      "name": "AgentS1" | "AgentS2",
      "raw": "<agent model output string>"
    }
  }
}
```

> v1: agent output is raw text. Later we’ll add a typed `parsed` block.

---

## Components

### `client.py`

* Provides `complete(payload: dict) -> dict | str`.
* Payload includes `messages`, optional `response_format` with JSON Schema, and `temperature`.
* Returns the model’s **JSON** (dict or JSON string).

### `llm_router.py`

* Internal Pydantic model `RouteDecision`:

  * `route`: `"S1" | "S2"`
  * `reasons`: `List[str]`
  * `signals`: `Dict[str, Any]`
  * `confidence`: `float ∈ [0,1]`
* Builds a system/user prompt and **JSON Schema** for `RouteDecision`.
* Sends a structured-output request via `client.complete(payload)`.
* Validates response into `RouteDecision`. On failure:

  * **Strict mode**: raise, or
  * **Safe mode**: default to `"S2"` with low confidence.
* Public API:

  * `decide(email_text) -> "S1" | "S2"`
  * `decide_full(email_text) -> RouteDecision`

### `controller.py`

* Thin wrapper with a `route(email_text) -> "S1" | "S2"` that delegates to `LLMRouter`.

### `base_agent.py`

* Defines a stable `.run(email_text) -> Dict` API.
* Holds `system_prompt`, `user_template` (set by subclasses).
* v1: calls `client.complete({...})` and returns:

  ```python
  {"agent": self.__class__.__name__, "raw": "<model output>"}
  ```
* v2 (later): add internal Pydantic model (e.g., `ActionPlan`) and validate structured output.

### `agent_s1.py` / `agent_s2.py`

* Subclass `BaseAgent` with different prompts (and optionally different model configs).
* S1: concise/low-latency prompt.
* S2: careful/deliberative prompt (may surface missing fields/ambiguities first).

### `io_utils.py`

* `read_jsonl(path) -> Iterator[dict]`
* `append_jsonl(path, obj) -> None`
* `load_existing_ids(path) -> Set[str]` (for `--resume`)

### `runner.py`

* CLI:

  ```
  python runner.py \
    --dataset dataset/train.jsonl \
    --run-dir runs/first_pass \
    --resume \
    --max-n -1
  ```
* Flow:

  1. Stream input lines.
  2. Skip already-seen `id` if `--resume`.
  3. `route = controller.route(email_text)`.
  4. `agent = agents[route]` (fallback to S2/S1 if needed).
  5. `raw = agent.run(email_text)`.
  6. Write enriched line to `runs/<run_id>/merged.jsonl`.

---

## Execution Flow (single record)

1. Read `{id, email_text, ...}`.
2. Router builds JSON Schema for `RouteDecision` and calls `client.complete(payload)`.
3. Validate into `RouteDecision` → choose `"S1"` or `"S2"`.
4. Invoke agent (S1 or S2) with its system/user prompts; collect `raw`.
5. Append enriched output (original + `run`).

---

## Error Handling Policy (v1)

* **Router validation error**: either raise (strict) or default to `"S2"` with `confidence=0.3`.
* **Agent failures**: write `raw` as-is (or include a small `errors` field if you prefer). Runner never crashes on a single bad record; it appends and continues.

---

## Directory Layout (suggested)

```
project/
  client.py
  llm_router.py
  controller.py
  base_agent.py
  agent_s1.py
  agent_s2.py
  io_utils.py
  runner.py
  dataset/
    train.jsonl
  runs/
    first_pass/
      merged.jsonl
```

---

## Extensibility (planned)

* **Typed agent outputs**: introduce an internal `ActionPlan` Pydantic model and structured outputs in agents (mirrors router approach).
* **Evaluation**: compute routing accuracy vs `controller_label`, plus pass\@1 on `action_sequence`.
* **Caching**: hash `(model, prompts, input)` to avoid repeat calls when resuming.

## Domain Adaptability

This system can be adapted for different business domains by customizing:

* **Agent prompts**: Tailor S1/S2 prompts for specific business processes (AP, HR, Customer Service, etc.)
* **API schemas**: Configure for different API systems (Intacct, Salesforce, ServiceNow, etc.)
* **Routing logic**: Adjust controller to route based on domain-specific signals
* **Action sequences**: Define appropriate API call patterns for each domain

**Example domains**:
- **Accounts Payable**: Route invoice emails → API calls for payment processing
- **Customer Service**: Route support emails → API calls for ticket creation/routing  
- **HR**: Route employee emails → API calls for leave requests, benefits, etc.

---

## Acceptance (Definition of Done)

* [ ] `runner.py` processes the full dataset into `runs/<run>/merged.jsonl`.
* [ ] Router returns valid `RouteDecision` objects on ≥95% of inputs (fallback on the rest).
* [ ] Agents run without crashing; `raw` text present for every processed record.
* [ ] No modifications to source dataset; resume works idempotently via `--resume`.

Save this as `FUNCTIONAL_SPEC.md` and keep it in sync as you add typed agent outputs or evaluation.
