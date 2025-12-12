import ollama


def call_llm(prompt: str, model: str = "llama3") -> str:
    """
    Appelle le modèle local Ollama et renvoie le texte généré.
    """
    try:
        response = ollama.generate(model=model, prompt=prompt)
        return response["response"].strip()
    except Exception as e:
        print("[LLM ERROR]", e)
        # Réponse de secours
        return "ACTION: HOLD\nSIZE: 0\nREASON: Fallback due to error."
