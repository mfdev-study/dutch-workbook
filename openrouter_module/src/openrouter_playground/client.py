import os

from dotenv import load_dotenv

load_dotenv()

from openai import OpenAI


def load_models_from_file(models_file: str = "free_models.txt"):
    try:
        with open(models_file) as f:
            lines = f.readlines()
    except FileNotFoundError:
        return [], 0

    models = []
    for line in lines:
        line = line.strip()
        if line and not line.startswith("=") and not line.startswith("Free"):
            if "|" in line:
                parts = line.split("|")
                models.append({"id": parts[0].strip(), "ctx": parts[1].strip()})
            else:
                models.append({"id": line, "ctx": "?"})

    return models, len(models)


class OpenRouterClient:
    def __init__(self, api_key: str = None, base_url: str = "https://openrouter.ai/api/v1"):
        self.api_key = api_key or os.getenv("OPENROUTER_API_KEY")
        self.base_url = base_url
        self.client = OpenAI(api_key=self.api_key, base_url=self.base_url)

    def chat(self, prompt: str, model: str = None) -> tuple[str, str]:
        model = model or os.getenv("OPENROUTER_MODEL", "anthropic/claude-3-5-sonnet")
        response = self.client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
        )
        content = response.choices[0].message.content
        return model, content

    def list_models(self, page: int = 0, per_page: int = 20, models_file: str = "free_models.txt"):
        models, total = load_models_from_file(models_file)
        start = page * per_page
        end = start + per_page
        return models[start:end], total

    def fetch_and_save_free_models(self, models_file: str = "free_models.txt"):
        response = self.client.models.list()
        free_models = []

        for model in response.data:
            pricing = getattr(model, "pricing", None) or {}
            input_price = pricing.get("input", "0")
            output_price = pricing.get("output", "0")

            if input_price == "0" and output_price == "0":
                free_models.append(
                    {
                        "id": model.id,
                        "name": getattr(model, "name", model.id),
                        "context_length": getattr(model, "context_length", None),
                    }
                )

        free_models = sorted(free_models, key=lambda x: x["name"])

        with open(models_file, "w") as f:
            f.write(f"Free Models ({len(free_models)} total)\n")
            f.write("=" * 60 + "\n\n")
            for m in free_models:
                ctx = m.get("context_length") or "?"
                f.write(f"{m['id']} | {ctx}\n")

        return free_models


def chat(prompt: str, model: str = None, api_key: str = None) -> tuple[str, str]:
    client = OpenRouterClient(api_key=api_key)
    return client.chat(prompt, model)


def list_models(page: int = 0, per_page: int = 20, models_file: str = "free_models.txt"):
    return load_models_from_file(models_file)


def list_free_models(api_key: str = None) -> list:
    client = OpenRouterClient(api_key=api_key)
    return client.fetch_and_save_free_models()
