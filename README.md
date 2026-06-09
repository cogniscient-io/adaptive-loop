# adaptive-loop

AI-assisted adaptive problem resolution library. When a value cannot be determined from known fields, the adaptive loop asks an LLM to find it — with caching, parsing, and fallbacks built in.

## Installation

```bash
pip install adaptive-loop
```

## Quick Start

```python
from adaptive_loop import AdaptiveLoop

loop = AdaptiveLoop(model="anthropic/claude-3-haiku")

# The server returned "max_kv_context" instead of "max_context_length"
# The LLM figures out the right field to use
result = await loop.adapt(
    template="find_field",
    problem="Find the maximum context length",
    data={"max_kv_context": 131072, "max_tokens": 8192},
    fallback=4096,
)
# result == 131072  (from max_kv_context, not the fallback)
```

## How It Works

The orchestrator composes five layers:

1. **Prompt Templates** — YAML files in `adaptive_loop/prompts/` (or your own directory) define structured prompts by name. Engineers reference templates, not hardcoded strings.
2. **LiteLLM Adapter** — Renders the prompt and sends it to any LiteLLM-compatible provider (`openai/gpt-4o`, `anthropic/claude-3-haiku`, `ollama/llama3`).
3. **Parser Chain** — The template declares an ordered list of extraction strategies (`key_value`, `numeric`, `json`). The chain tries each parser until one succeeds, with confidence tracking.
4. **Cache** — On success, the result is cached. A subsequent call with the same template and problem returns the cached value without calling the LLM.
5. **Recorder** — Every adaptation attempt is logged with outcome (success/fallback/error), value, and latency.

## API

```python
result = await loop.adapt(
    template="find_field",       # required: prompt template name
    problem="Find max tokens",   # required: what you need
    data=model_response,         # optional: the data to analyze
    error="Unknown field",       # optional: error context for the AI
    fallback=4096,               # optional: value if AI can't find it
)
```

## Configuration

```python
from adaptive_loop import AdaptiveLoop
from adaptive_loop.cache.base import LRUCache
from adaptive_loop.recorder.base import InMemoryRecorder

loop = AdaptiveLoop(
    model="anthropic/claude-3-haiku",
    cache=LRUCache(max_size=256),
    recorder=InMemoryRecorder(),
    timeout=15.0,
)
```

## Built-in Templates

| Name | Description | Parser Chain |
|---|---|---|
| `find_field` | Find a field value in data | key_value → numeric |
| `extract_value` | Extract a numeric value as JSON | json → numeric |

## Product-Specific Prompts

Create YAML files in your product's prompt directory. They override built-in templates by name:

```yaml
# /app/my-product/prompts/find_field.yaml
name: find_field
system: You are a precise data field finder.
user: |
  Given this data: {data}
  An error occurred: {error}
  Find: {problem}
  Respond with FIELD_NAME: VALUE or NOT_FOUND.
parser_chain:
  - key_value
  - numeric
```

Then load them at init:

```python
from adaptive_loop.messages.registry import PromptRegistry

reg = PromptRegistry()
reg.load_directory("/app/my-product/prompts")
loop = AdaptiveLoop(model="gpt-4o", registry=reg)
```

## Development

```bash
pip install -e ".[dev]"
pytest tests/
```

## License

Concepts, ideas, and implementations in this repository are released under the [GNU General Public License v3.0](./LICENSE) and/or [Creative Commons Attribution 4.0 International (CC BY 4.0)](https://creativecommons.org/licenses/by/4.0/) for research and educational use.
Commercial licensing options are available. Please contact cogniscient.io@gmail.com for details.
