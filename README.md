# CrewAI Agent Eval Quickstart with Promptfoo

A minimal, runnable example that shows how to **evaluate a CrewAI agent's output quality using promptfoo** — and catch regressions when you change the prompt.

> **TL;DR**: Clone, add your OpenAI key, run `promptfoo eval`. That's it.

## What This Covers

| Question | This repo answers it? |
|---|---|
| How do I check that my CrewAI agent returns valid JSON? | Yes — `is-json` assertions |
| How do I verify all required fields are present? | Yes — JavaScript assertion on parsed output |
| How do I assert that the agent categorizes tickets correctly? | Yes — category-specific assertions |
| How do I evaluate the quality of the agent's reasoning? | Yes — `llm-rubric` assertion |
| How do I verify the agent used the right tool? | Yes — tool-usage assertions on `tools_used` |
| How do I catch regressions after changing my agent prompt? | Yes — re-run `promptfoo eval` and compare |
| How do I inspect and share eval results? | Yes — `promptfoo view` opens a local web viewer |

## When to Use `crewai test` vs Promptfoo

| | `crewai test` | promptfoo |
|---|---|---|
| Purpose | Built-in performance scoring across N iterations | Fine-grained assertions on specific inputs |
| Test cases | Reuses the crew's own task | Define your own test suite with expected outputs |
| Assertions | Automatic quality scoring | Custom: JSON validity, field presence, rubric, LLM-grader |
| Regression | No built-in regression detection | Re-run and compare; results are stored per run |
| Viewer | CLI summary only | Web viewer + export |
| Best for | "Is my crew generally working?" | "Did my prompt change break specific cases?" |

**Use both.** `crewai test` for overall health; promptfoo for structured output contracts and regression guarding.

## Setup

### Prerequisites

- Python 3.10+
- Node.js 18+ (for promptfoo)
- An API key for your chosen CrewAI LLM provider. This quickstart defaults to OpenAI; TogetherAI is included as an optional alternative.

On Debian/Ubuntu, install the venv package first if `python -m venv .venv` fails:

```bash
sudo apt install python3-venv
```

### Install

```bash
# Clone this repo
git clone https://github.com/<your-username>/crewai-promptfoo-eval-quickstart.git
cd crewai-promptfoo-eval-quickstart

# Python dependencies
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Or, with uv
uv venv
uv pip install -r requirements.txt

# promptfoo CLI
npm install
```

### Configure API Key

```bash
cp .env.example .env
# Edit .env and add either TOGETHERAI_API_KEY or OPENAI_API_KEY
```

This repo supports these common setups:

```bash
# TogetherAI
TOGETHERAI_API_KEY=replace-me
TOGETHER_API_KEY=replace-me              # Same value — needed for llm-rubric grading
TOGETHER_MODEL_CHAT=zai-org/GLM-5.1

# OpenAI
OPENAI_API_KEY=replace-me
CREWAI_MODEL=openai/gpt-4o-mini
```

If `TOGETHER_MODEL_CHAT` is set without a provider prefix, `agent.py` will pass it to CrewAI as `together_ai/<model>`.

If you installed CrewAI with `uv`, make sure promptfoo uses the same Python environment:

```bash
PROMPTFOO_PYTHON=.venv/bin/python
```

You can put `PROMPTFOO_PYTHON` in `.env`; `npm run eval` loads `.env` automatically.

The `npm run eval` script also points `HOME`, `XDG_DATA_HOME`, and `PROMPTFOO_CONFIG_DIR` at ignored repo directories so promptfoo and CrewAI do not need to write run state into your real home directory. `.env.example` sets `CREWAI_TRACING_ENABLED=false` to avoid CrewAI Cloud credential prompts during this local quickstart.

## Run the Eval

```bash
npm run eval
```

You can also run the promptfoo CLI directly:

```bash
npx promptfoo@latest eval --env-file .env
```

This will:

1. Load the CrewAI triage agent from `agent.py`
2. Run each test case from `promptfooconfig.yaml`
3. Assert valid JSON, required fields (including `tools_used`), correct category, appropriate priority, and tool usage
4. Print a summary table

### View Results

```bash
npm run view
```

Opens a local web viewer where you can inspect each test case's output, see which assertions passed/failed, and compare across runs.

## How It Works

### The Agent (`agent.py`)

A single-agent CrewAI crew that triages support tickets into structured JSON. The agent uses a `search_knowledge_base` tool before triaging and reports which tools it used:

```json
{
  "category": "billing | technical | account | feature_request | security",
  "priority": "critical | high | medium | low",
  "rationale": "One-sentence explanation",
  "next_action": "One-sentence next step",
  "tools_used": ["search_knowledge_base"]
}
```

The `call_api()` function is the promptfoo Python provider entry point. promptfoo calls it for each test case with the ticket text as `prompt`.

### The Eval Config (`promptfooconfig.yaml`)

Defines:

- **Provider**: `python:agent.py:call_api` — points to our CrewAI agent
- **Prompts**: `{{ticket}}` — each test case sends its ticket text to the Python provider
- **Test cases**: 10 tickets covering all 5 categories with various assertion patterns including `llm-rubric` and tool-usage checks

### Assertions Used

| Assertion Type | What It Checks |
|---|---|
| `is-json` | Output is parseable JSON |
| JavaScript | Custom logic: field presence, category correctness, priority validity, tool usage |
| `llm-rubric` | LLM-graded quality of the triage reasoning (e.g. rationale relevance, next-action appropriateness) |

## Add a Regression Case

1. Add a new test case to `promptfooconfig.yaml`:

```yaml
- vars:
    ticket: "Your new ticket description here."
  assert:
    - type: is-json
    - type: javascript
      value: |
        const d = JSON.parse(output);
        const required = ['category','priority','rationale','next_action','tools_used'];
        const missing = required.filter(k => !(k in d));
        return missing.length === 0;
      label: "all 5 fields present"
    - type: javascript
      value: |
        const d = JSON.parse(output);
        return d.category === 'billing';
      label: "category=billing"
```

2. Run `promptfoo eval` — if the agent's output changes (e.g., after a prompt edit), you'll see which cases break.

### Test Cases from CSV

Additional test cases live in `tests/support_cases.csv`. The CSV format is:

```csv
ticket,expected_category,expected_priority
"I want to request a dark mode option.",feature_request,low
```

You can load these into your `promptfooconfig.yaml` by referencing them directly, or add them as inline test cases for full assertion control.

## Inspect and Share Results

```bash
# Open the web viewer
npm run view

# Export results as JSON
npx promptfoo@latest eval -o results.json

# Export as YAML
npx promptfoo@latest eval -o results.yaml
```

Share screenshots from the viewer, or share exported results files, so teammates can see exactly what changed.

## Extend to Tool-Usage Checks

The triage agent includes a `search_knowledge_base` tool and reports which tools it used in the `tools_used` field of its output. You can assert on this in two ways:

### 1. Verify a specific tool was called

```yaml
- type: javascript
  value: |
    const d = JSON.parse(output);
    return Array.isArray(d.tools_used) && d.tools_used.includes('search_knowledge_base');
  label: "used knowledge base tool"
```

### 2. Verify the tools_used field is present and is an array

```yaml
- type: javascript
  value: |
    const d = JSON.parse(output);
    return Array.isArray(d.tools_used);
  label: "tools_used is an array"
```

To add your own tools, define them in `agent.py` using the `@tool` decorator, add them to the agent's `tools` list, and update the task description to instruct the agent to report tool usage in `tools_used`.

### LLM-Rubric Assertions

For cases where exact matching is too brittle (e.g., edge-case tickets), use `llm-rubric` to have an LLM grade the quality of the output:

```yaml
- type: llm-rubric
  value: |
    The triage should identify this as a security issue with critical or high priority.
    The rationale should reference unauthorized access, data exposure, or vulnerability handling.
    The next_action should involve alerting the security team or taking immediate protective measures.
  label: "rubric: security triage quality"
```

The `llm-rubric` assertion uses OpenAI by default (requires `OPENAI_API_KEY`). The example in this repo already overrides the default with `provider: togetherai:zai-org/GLM-5.1`; remove the `provider:` line if you'd rather use OpenAI's default grader. To use a different TogetherAI model:

```yaml
- type: llm-rubric
  provider: togetherai:meta-llama/Llama-3-70b-chat-hf
  value: "Your rubric criteria here."
```

## Known Limits

- **Flaky assertions**: Category assertions depend on LLM judgment. For edge-case tickets, use `llm-rubric` assertions instead of exact matches.
- **Tool-usage flakiness**: The agent self-reports `tools_used` based on its own judgment. If it occasionally omits a tool, consider loosening the assertion to check for field existence only (e.g., `Array.isArray(d.tools_used)`) rather than requiring a specific tool name.
- **Provider support**: promptfoo's Python provider runs the agent synchronously. For large crews, consider timeout settings in `promptfooconfig.yaml`.
- **Rubric cost**: `llm-rubric` assertions make an additional LLM call per test case for grading. Budget accordingly.
- **Cost**: Each test case makes one LLM call (plus one per rubric assertion). 10 cases × gpt-4o-mini ≈ $0.01 per eval run without rubric; slightly more with rubric.
- **`crewai test` vs promptfoo**: These are complementary, not competing. Use `crewai test` for overall crew health; use promptfoo for specific output contracts and regression detection.

## Public Repo Checklist

Before publishing this repo:

- Confirm `.env` is not committed. Only `.env.example` should be public.
- Run `python -m py_compile agent.py`.
- Run `npm run eval` with a real `TOGETHERAI_API_KEY` or `OPENAI_API_KEY`.
- Open `npm run view` and verify the latest run is inspectable.
- Replace `git clone https://github.com/<your-username>/crewai-promptfoo-eval-quickstart.git` above after the GitHub repo exists.
- Add a short GitHub description, for example: `CrewAI support-ticket eval quickstart using promptfoo`.
- Keep result exports out of git unless you intentionally want to publish a sample report.

## File Structure

```
.
├── README.md                 # This file
├── agent.py                  # CrewAI agent + promptfoo provider
├── promptfooconfig.yaml      # Eval config: providers, prompts, tests, assertions
├── .env.example              # API key template
├── .gitignore                # Local secrets, caches, and generated result files
├── LICENSE                   # MIT license
├── package-lock.json         # Locked promptfoo CLI dependency graph
├── package.json              # promptfoo CLI scripts
├── requirements.txt          # Python dependencies
└── tests/
    └── support_cases.csv     # Additional test cases
```

## Origin

This quickstart was created in response to the [CrewAI community thread on agent eval tools](https://community.crewai.com/t/agent-eval-tools/7453). The thread asks: *how do you evaluate complex CrewAI agents for output quality, tool usage, regressions, and shareable results?*

This repo maps each question to a concrete promptfoo pattern:

| Community question | promptfoo pattern | Demonstrated? |
|---|---|---|
| Output quality | Assertions + `llm-rubric` checks | Yes — `llm-rubric` on security case |
| Tool usage improvement | `tools_used` field + tool-call assertions | Yes — `search_knowledge_base` dummy tool |
| Regressions after changes | Saved test cases + repeated `promptfoo eval` | Yes — inline regression suite |
| Comparing runs | `promptfoo view` + result exports | Yes — viewer + JSON/YAML export |
| Sharing results | Viewer screenshots or exported reports | Yes — `-o results.json` |

## License

MIT
