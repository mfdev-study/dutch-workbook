from openrouter_playground import chat

model, response = chat(
    "write md intuction how to compile and run c code on linux provide in this md file which commands i must run"
)
print(f"Model: {model}")
print(response)
