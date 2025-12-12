import ollama

response = ollama.generate(
    model="llama3",
    prompt="Say YES if you receive this message."
)

print(response["response"])