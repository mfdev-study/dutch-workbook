# OpenRouter Playground

Simple app for testing and exploring OpenRouter API.

## Setup

1. Install dependencies:
   ```bash
   uv sync
   ```

2. Copy `.env.example` to `.env` and add your API key:
   ```bash
   cp .env.example .env
   ```

3. Edit `.env` and set your OpenRouter API key:
   ```
   OPENROUTER_API_KEY=your_api_key_here
   ```

4. Optional: Set a default model:
   ```
   OPENROUTER_MODEL=anthropic/claude-3-5-sonnet
   ```

## Quick Start

Run the interactive chat:
```bash
uv run python main.py
```

Then type your prompts and press Enter. Type `/quit` to exit.

## Interactive Mode Commands

| Command | Description |
|---------|-------------|
| `/ls [page]` | List free models (20 per page, e.g., `/ls 1` for page 2) |
| `/use <n>` | Switch to model by index (e.g., `/use 42`) |
| `/use <id>` | Switch to model by full ID (e.g., `/use deepseek/deepseek-r1`) |
| `/info` | Show current model info |
| `/free` | Refresh models list from OpenRouter API |
| `/quit` or `/exit` | Exit the program |

## Step-by-Step Example

```bash
# 1. Start the chat
uv run python main.py

# 2. List available models
/ls

# 3. Switch to a different model (use index number from /ls)
/use 42

# 4. Chat with the model
Hello! How are you?

# 5. Check your current model
/info

# 6. Exit
/quit
```

## Using as a Python Module

Import the module in your own projects:

```python
from openrouter_playground import chat, list_models, OpenRouterClient, list_free_models
```

### Quick Chat

```python
from openrouter_playground import chat

# Uses default model from OPENROUTER_MODEL env var
response = chat("Hello, world!")
print(response)

# Use a specific model
response = chat("Explain quantum physics", model="qwen/qwen3-4b")
print(response)

# With custom API key
response = chat("Hello!", api_key="your-openrouter-api-key")
```

### List Models

```python
from openrouter_playground import list_models

# Get first 20 models
models, total = list_models(page=0, per_page=20)
print(f"Total models: {total}")
for m in models:
    print(f"  {m['id']} (ctx: {m['ctx']})")

# Get next page
models, total = list_models(page=1, per_page=20)
```

### Use the Client Class

```python
from openrouter_playground import OpenRouterClient

# Initialize with API key from env
client = OpenRouterClient()

# Or provide API key directly
client = OpenRouterClient(api_key="your-openrouter-api-key")

# Chat with default model
response = client.chat("Hello!")
print(response)

# Chat with specific model
response = client.chat("Write a poem", model="meta-llama/llama-3.3-70b-instruct")
print(response)

# List models
models, total = client.list_models(page=0, per_page=10)
for m in models:
    print(f"  {m['id']} (ctx: {m['ctx']})")

# Fetch and save fresh free models from API
free_models = client.fetch_and_save_free_models("my_models.txt")
print(f"Saved {len(free_models)} models")
```

### Fetch Free Models from API

```python
from openrouter_playground import list_free_models

# Fetch and save free models to file
free_models = list_free_models(api_key="your-key")

# Print model IDs
for m in free_models:
    print(f"  {m['id']} (ctx: {m['context_length']})")
```

## Available Models

Check https://openrouter.ai/collections/free-models for current free models.

## File Structure

```
openrouter-playground/
├── src/openrouter_playground/
│   ├── __init__.py      # Package exports
│   └── client.py        # OpenRouterClient class + functions
├── main.py              # CLI entry point
├── pyproject.toml       # Package config
├── .env.example         # Environment template
├── .env                 # Your API key (create from .env.example)
├── free_models.txt      # Cached list of free models
└── README.md            # This file
```

## Install as Dependency in Other Projects

Add to your `pyproject.toml`:

```toml
[project]
dependencies = [
    "openrouter-playground @ git+https://github.com/yourusername/openrouter-playground.git",
]
```

Or install locally:

```bash
cd /path/to/openrouter-playground
pip install -e .
```
