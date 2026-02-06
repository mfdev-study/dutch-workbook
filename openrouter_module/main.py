import os
import sys
from dotenv import load_dotenv

load_dotenv()

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from openrouter_playground import OpenRouterClient, list_models

MODELS_FILE = "free_models.txt"
current_model = os.getenv("OPENROUTER_MODEL", "anthropic/claude-3-5-sonnet")


def main():
    client = OpenRouterClient()
    models, _ = list_models(0, 1, MODELS_FILE)
    model_count = len(load_all_models())

    print("OpenRouter Playground")
    print(f"Model: {current_model}")
    print(f"Loaded {model_count} models from {MODELS_FILE}")
    print("-" * 40)
    print("Commands:")
    print("  /ls [page]      - List free models (20 per page, * = current)")
    print("  /use <n>        - Switch model by index (auto-saves to .env)")
    print("  /use <id>       - Or use full model ID")
    print("  /info           - Show current model info")
    print("  /free           - Fetch fresh free models from API")
    print("  /quit           - Exit")
    print("-" * 40)

    while True:
        prompt = input(f"\n[{current_model.split('/')[-1]}] You: ").strip()
        if not prompt:
            continue

        if prompt.lower() in ["/quit", "/exit", "/q"]:
            break

        if prompt.lower().startswith("/ls"):
            parts = prompt.split()
            page = int(parts[1]) if len(parts) > 1 else 0
            model_slice, total = list_models(page, 20, MODELS_FILE)
            start = page * 20
            print(f"\nModels {start + 1}-{start + len(model_slice)} of {total}:")
            for i, m in enumerate(model_slice):
                marker = " *" if m["id"] == current_model else ""
                ctx = m["ctx"] if m["ctx"] else "?"
                print(f"  [{start + i:3}] {m['id']} (ctx: {ctx}){marker}")
            continue

        if prompt.lower().startswith("/use "):
            arg = prompt[5:].strip()
            if switch_model(arg, MODELS_FILE):
                print(f"Switched to: {current_model}")
            elif arg.isdigit():
                all_models = load_all_models()
                print(f"Invalid index: {arg} (0-{len(all_models) - 1})")
            else:
                print(f"Model not found: {arg}")
            continue

        if prompt.lower() == "/info":
            idx = get_model_index(current_model, MODELS_FILE)
            ctx = "?"
            if idx >= 0:
                models = load_all_models()
                ctx = models[idx].get("ctx", "?")
            print(f"\nCurrent model: {current_model}")
            print(f"Index: {idx}")
            print(f"Context: {ctx} tokens")
            continue

        if prompt.lower() == "/free":
            print("\nFetching fresh models from API...")
            try:
                client.fetch_and_save_free_models(MODELS_FILE)
                print(f"Saved models to {MODELS_FILE}")
            except Exception as e:
                print(f"Error: {e}")
            continue

        try:
            model, response = client.chat(prompt, current_model)
            print(f"\n[{model.split('/')[-1]}] Assistant: {response}")
        except Exception as e:
            print(f"\nError: {e}")


def load_all_models():
    try:
        with open(MODELS_FILE, "r") as f:
            lines = f.readlines()
    except FileNotFoundError:
        return []

    models = []
    for line in lines:
        line = line.strip()
        if line and not line.startswith("=") and not line.startswith("Free"):
            if "|" in line:
                parts = line.split("|")
                models.append({"id": parts[0].strip(), "ctx": parts[1].strip()})
            else:
                models.append({"id": line, "ctx": "?"})
    return models


def get_model_index(model_id, models_file):
    models = load_all_models()
    for i, m in enumerate(models):
        if m["id"] == model_id:
            return i
    return -1


def switch_model(arg, models_file):
    global current_model
    models = load_all_models()

    if arg.isdigit():
        idx = int(arg)
        if 0 <= idx < len(models):
            current_model = models[idx]["id"]
            save_model_to_env(current_model)
            return True
        return False
    else:
        for m in models:
            if m["id"] == arg:
                current_model = arg
                save_model_to_env(current_model)
                return True
        return False


def save_model_to_env(model_id):
    env_path = ".env"
    api_key = os.getenv("OPENROUTER_API_KEY", "")

    if os.path.exists(env_path):
        with open(env_path, "r") as f:
            lines = f.readlines()
    else:
        lines = []

    updated = False
    new_lines = []
    for line in lines:
        if line.startswith("OPENROUTER_MODEL="):
            new_lines.append(f"OPENROUTER_MODEL={model_id}\n")
            updated = True
        else:
            new_lines.append(line)

    if not updated:
        new_lines.append(f"OPENROUTER_MODEL={model_id}\n")

    with open(env_path, "w") as f:
        f.writelines(new_lines)


if __name__ == "__main__":
    main()
