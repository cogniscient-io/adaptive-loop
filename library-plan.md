# Adaptive Loop Library Plan

## Goal

Transform the monolithic `AdaptiveLoopService` into a standalone, project-agnostic library that exposes adaptive, AI-assisted problem resolution as a reusable capability.

## Current Problems

- **Tight coupling to GCS Kernel** -- imports `MCPClient`, `PromptObject`, `AIOrchestratorService`
- **All concerns in one class** -- orchestration, prompting, parsing, transport, fallback logic
- **Raw string prompts** -- no template system, no localization, no versioning
- **Regex response parsing** -- fragile, no structured contract between prompt and parser
- **No caching** -- identical problems re-solved every time
- **No history** -- cannot audit what adaptations ran, succeeded, or fell back

## Separation of Concerns

| Current (mixed in one class) | Library Module |
|---|---|
| `_build_prompt()` with f-strings | `messages` -- structured prompt templates |
| `_parse_ai_response()` with regex | `parser` -- response extraction strategies |
| `AIOrchestratorService` call | `adapter` -- pluggable AI provider interface |
| Cache TODO | `cache` -- key/value store for successful adaptations |
| Logging/journaling TODO | `recorder` -- adaptation event history |
| `adapt_async()` orchestration | `core` -- composable orchestrator |

## Library Structure

```
adaptive_loop/
├── __init__.py            # Public API surface
├── core.py                # AdaptiveLoop orchestrator (async + sync adapt())
├── prompts/               # Built-in YAML prompt catalog (shipped with library)
│   ├── find_field.yaml
│   ├── extract_value.yaml
│   └── ...
├── messages/
│   ├── __init__.py
│   ├── template.py        # PromptTemplate class (inverted log-msg pattern)
│   └── registry.py        # PromptRegistry -- loads YAML from dirs, resolves by name
├── parser/
│   ├── __init__.py
│   ├── base.py            # BaseParser ABC + ParsedResult dataclass
│   ├── strategies.py      # KeyValParser, NumericParser, JSONParser
│   └── chain.py           # ParserChain -- primary strategy -> fallback sequence
├── adapter/
│   ├── __init__.py
│   └── litellm.py         # LiteLLMAdapter wraps litellm.async_completion
├── cache/
│   ├── __init__.py
│   └── base.py            # AdaptCache ABC + LRUCache + NullCache
├── recorder/
│   ├── __init__.py
│   └── base.py            # AdaptRecorder ABC + InMemoryRecorder + NullRecorder
└── exceptions.py          # AdaptiveLoopError, ParseError, AdapterError, TimeoutError
```

## Module Design

### 1. `messages/template.py` -- Structured Prompt Templates

Each product builds its own prompt library on top of the built-ins. The library provides the mechanism (template class, registry) and a few generic starting-point prompts. Engineers reference prompts by name, never hardcoding prompt strings in application code.

Inverted from log message libraries. Instead of `format(data) -> string`, the template defines:

- **name** -- identifier for lookup (e.g., `"find_field"`)
- **system** -- optional system-level instructions
- **user** -- user message template with named slots (`{context}`, `{problem}`)
- **parser_chain** -- ordered list of parser strategies (primary + fallbacks)

```yaml
# prompts/find_field.yaml
name: find_field
user: |
  Given this data: {{ context }}

  Find: {{ problem_description }}

  Respond with FIELD_NAME: VALUE or NOT_FOUND.
parser_chain:
  - key_value
  - numeric
```

### 1b. `messages/registry.py` -- Prompt Registry

Loads YAML files from one or more directories into a name-indexed registry. The consumer adds product-specific prompt directories at initialization; the orchestrator resolves templates by name against the registry, not by hardcoding paths.

```python
registry = PromptRegistry()
registry.load_directory("adaptive_loop/prompts")       # built-ins
registry.load_directory("/app/my-product/prompts")       # product-specific

template = registry.get("find_field")                   # by name
rendered = template.render(context=data, problem_description="max tokens")
```

Product-specific prompts can override built-ins by the same name (last-loaded wins).

Built-in templates live in `prompts/` as YAML files (e.g., `find_field.yaml`). The template loader reads YAML at startup -- multi-line text is clean, comments carry prompt iteration notes, and prompt changes don't require code deploys. Consumers add their own YAML files to extend the library.

### 2. `parser/` -- Response Extraction

The parser reads the AI's raw string response and returns a typed value.

- **KeyValParser** -- extracts `FIELD_NAME: VALUE` pattern (replaces current `_parse_ai_response`)
- **NumericParser** -- extracts first numeric value found
- **JSONParser** -- parses structured JSON output
- Template declares `parser_chain` (ordered list), not a single `output_schema`

**Confidence levels:**

- `"exact"` -- first parser in the chain matched (primary strategy)
- `"fallback"` -- a later parser in the chain matched
- `"none"` -- no parser succeeded, raw string returned

```python
chain = ParserChain(["key_value", "numeric"])
result = chain.parse(ai_response_string)
# ParsedResult(value=4096, confidence="exact")
# or if key_value fails and numeric succeeds:
# ParsedResult(value=4096, confidence="fallback")
# or if nothing matches:
# ParsedResult(raw="no value found", confidence="none")
```

### 3. `adapter/` -- AI Provider (LiteLLM)

Uses [LiteLLM](https://github.com/BerriAI/litellm) as the LLM transport layer. It already normalizes dozens of providers (OpenAI, Anthropic, Azure, Ollama, etc.) into a single `async_completion()` call — no need to re-invent that.

The `LiteLLMAdapter` wraps the template render output into a LiteLLM request and returns the raw text response.

```python
class LiteLLMAdapter:
    def __init__(self, model: str = "gpt-4o", **litellm_kwargs): ...
    async def send(self, request: AdaptRequest, timeout: float = 30.0) -> AdaptResponse: ...
```

The adapter is the only module with a concrete implementation shipped by the library. The host project configures the model and API keys — everything else is a default.

### 4. `cache/` -- Adaptation Result Cache

Prevents re-solving the same problem.

```python
class AdaptCache(ABC):
    @abstractmethod
    async def get(self, key: str) -> Optional[Any]: ...
    @abstractmethod
    async def set(self, key: str, value: Any, ttl: int = 3600): ...
```

Key = hash of (template name, context summary, problem description). Ships with an in-memory `LRUCache` and a no-op `NullCache`.

### 5. `recorder/` -- Adaptation Event Journal

Records every adaptation attempt for auditing and debugging.

```python
class AdaptRecorder(ABC):
    @abstractmethod
    async def record(self, event: AdaptEvent): ...
```

Event includes: timestamp, template used, problem description, outcome (success/fallback/error), parsed value, latency. Ships with `InMemoryRecorder` and `NullRecorder`.

### 6. `core.py` -- Orchestrator

Composes all modules into the public API. Provides both `async adapt()` and a sync `adapt()` wrapper using `asyncio.get_event_loop()` for consumers without an async context.

```python
loop = AdaptiveLoop(
    adapter=my_adapter,
    cache=my_cache,
    recorder=my_recorder,
    default_timeout=15.0,
)

# Async consumers
result = await loop.adapt(
    template="find_field",
    context=data,
    problem="Find the max context length",
    fallback=4096,
)

# Sync consumers
result = loop.adapt_sync(
    template="find_field",
    context=data,
    problem="Find the max context length",
    fallback=4096,
)
```

Flow:
1. Look up template by name
2. Render prompt with context data
3. Check cache -- if hit, return cached value
4. Send to adapter
5. Parse response with strategy from template
6. On success, cache the result and record event
7. On failure, return fallback and record event

## Migration Path (TDD)

Each module is driven by tests first -- write failing tests, then implementation.

1. **Scaffold the package** -- directory structure, empty modules, `pyproject.toml`, pytest config
2. **`messages/`** -- test PromptTemplate render, test PromptRegistry load/resolve/override, test YAML parsing
3. **`parser/`** -- test each parser strategy against raw AI output, test ParserChain fallback order and confidence
4. **`adapter/`** -- test timeout enforcement and error propagation via mock `litellm.async_completion`
5. **`cache/`** -- test hit/miss, test TTL expiry, test NullCache pass-through
6. **`recorder/`** -- test event capture, test InMemoryRecorder query, test NullRecorder no-op
7. **`core.py`** -- test full adapt flow (hit path), test fallback path, test timeout propagation, test sync wrapper
8. **Integration** -- wire a mock adapter through the full orchestrator, verify end-to-end behavior
9. **`__init__.py`** -- expose clean public API, verify imports
10. **Demonstrate** -- show the example usage from the host project working with the new library

## What the Host Project Provides

After migration, the host project's integration layer is thin:

```python
from adaptive_loop import AdaptiveLoop

loop = AdaptiveLoop(model="anthropic/claude-sonnet-4-6")

# Or with product-specific prompts:
loop = AdaptiveLoop(
    model="openai/gpt-4o",
    prompt_directories=["/app/my-product/prompts"],
)
```

The host project configures:
- **model** -- any LiteLLM-compatible model string
- **prompt directories** -- product-specific YAML prompts that override or extend built-ins
- **API keys** -- via environment variables or LiteLLM config

Everything else -- adapter transport, parsing, caching, recording -- is library internals.

## Repository Boundaries

**This repo** — builds and ships the `adaptive_loop` library. No GCS Kernel code, no GCS-specific imports.

**GCS Kernel repo** — consumes the library as its first product user. That work happens in the GCS repo, not here. Once the library is published, the GCS repo will:

1. Add `adaptive_loop` as a dependency
2. Create product-specific YAML prompts from the old `_build_prompt()` logic
3. Swap `adapt_async()` calls for `loop.adapt()`
4. Delete the GCS-specific `AdaptiveLoopService` class

`adaptive_loop_service.py` in this repo is a frozen reference artifact and will not be modified.
