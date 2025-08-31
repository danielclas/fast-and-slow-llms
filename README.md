# Fast and Slow LLMs for Email-to-API Mapping

A lightweight framework for **routing business emails** to the right LLM agent and translating them into **structured API action plans**. The system uses a **router** and two **agents** that output Pydantic-validated JSON describing which API endpoints to call, with reasoning and confidence.


---

## Repo Structure

```
.
├── api_spec
│   ├── accounts-payable.openapi.yaml
│   ├── accounts-receivable.openapi.yaml
│   ├── general-ledger.openapi.yaml
│   └── open_api_spec.py
├── dataset
│   ├── dataset_inputs_150.jsonl
│   └── dataset_inputs_smoke_15.jsonl
├── index.html
├── io_utils.py
├── llm
│   ├── base
│   │   └── base_agent.py
│   ├── client.py
│   ├── controller
│   │   └── controller.py
│   ├── llm_router.py
│   ├── s1
│   │   └── s1_agent.py
│   ├── s2
│   │   └── s2_agent.py
│   └── tools
│       ├── __init__.py
│       └── openapi_loader.py
├── Paper
│   └── Fast and Slow LLMs for email to API mapping.pdf
├── Presentation materials
│   ├── Fast and slow LLMs.pdf
│   └── Fast and slow LLMs.pptx
├── README.md
├── requirements.txt
├── run.bash
├── runner.py
└── runs
    ├── baseline_s1_20250823_124721
    │   ├── merged.graded.jsonl
    │   └── merged.jsonl
    ├── baseline_s2_20250824_180009
    │   ├── merged.graded.jsonl
    │   └── merged.jsonl
    ├── intelligent_routing_0.3_confidence_20250824_213716
    │   ├── merged.graded.jsonl
    │   └── merged.jsonl
    ├── intelligent_routing_0.5_confidence_20250825_135053
    │   ├── merged.graded.jsonl
    │   └── merged.jsonl
    └── intelligent_routing_0.7_confidence_20250825_143605
        ├── merged.graded.jsonl
        └── merged.jsonl


```

---

## Installation

### 1) Python & deps
```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 2) Environment Variables
You need to set your OpenAI API key as an environment variable:

```bash
export OPENAI_API_KEY="your_api_key_here"
```

Or create a `.env` file in the project root:
```
OPENAI_API_KEY=your_api_key_here
```

---

## Usage

### Running the System
After installation, you can run the system using:

```bash
python runner.py
```

This will process emails from the dataset and save results to the `runs/` directory with timestamped folders.

### Visualizing Results
You can use the built-in web-based viewer to analyze and grade the results:

1. **Open the viewer**: Open `index.html` in your web browser
2. **Load results**: Click to select any `merged.jsonl` file from the `runs/` directory
3. **Analyze**: View statistics, filter results, and examine individual email processing details
4. **Grade results**: Mark responses as correct/incorrect and download graded files

The viewer provides:
- Run metadata and summary statistics
- Filtering by route, confidence, and text search
- Detailed view of each email's processing pipeline
- Manual grading interface with downloadable results

---

## How it Works

### Routing
`llm/llm_router.py` uses a system prompt and JSON-schema constrained decoding to produce a **RouteDecision**:

```jsonc
{
  "route": "S1" | "S2",
  "reasons": ["..."],
  "confidence": 0.0 <= x <= 1.0
}
```

The `Controller` (`llm/controller/controller.py`) is a thin facade that calls the router’s `decide()` method.

### Agents
Both `AgentS1` and `AgentS2` extend `BaseAgent` (`llm/base/base_agent.py`). They differ only in **prompting** and **intended use**:

- **S1**: fast / single-step, unambiguous requests.
- **S2**: slower / multi-step, ambiguous or interdependent actions.

Agents return an **AgentResponse** with an ordered **action_sequence** of **APIAction** items, plus `reasoning` and `confidence`.

**Schema (simplified):**
```jsonc
{
  "action_sequence": [
    {
      "endpoint": "accounts-receivable/customer",
      "method": "GET" | "POST" | "PUT" | "DELETE",
      "params": "...",   // query string or JSON-serialised dict
      "payload": "..."   // JSON-serialised dict or null
    }
  ],
  "reasoning": "...",
  "confidence": 0.0 <= x <= 1.0
}
```



### LLM client
`llm/client.py` wraps OpenAI’s API and enables **JSON schema–constrained** outputs. If the model returns invalid JSON, a **RuntimeError** is raised; the caller (e.g., the runner) records the error and continues.

---


## Citation

If you use this project in an academic work, please cite as:

```bibtex
@software{llm_agents_project,
  title = {Fast and Slow LLMs for Email-to-API Mapping},
  author = {Daniel Clas, Aida Rostami},
  year = {2025},
  url = {https://github.com/danielclas/fast-and-slow-llms}
}
```

