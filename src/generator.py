import os
import requests
import logging
from typing import Optional


# Support both HF_API_KEY and HUGGINGFACE_API_KEY for compatibility
def _get_hf_api_key() -> Optional[str]:
    return os.getenv("HF_API_KEY") or os.getenv("HUGGINGFACE_API_KEY")


def _local_fallback_question(topic: str, reason: str = ""):
    alternatives = [
        "Alternativa 1",
        "Alternativa 2",
        "Alternativa 3",
        "Alternativa 4",
    ]
    return {
        "enunciado": f"(Fallback) Sobre {topic}: Qual é a alternativa correta?",
        "alternativas": alternatives,
        "correta": "A",
        "feedback": f"Questão gerada localmente porque o gerador externo falhou: {reason}",
    }


def generate_question(topic: str):
    api_key = _get_hf_api_key()
    model = os.getenv("HUGGINGFACE_MODEL") or os.getenv("HF_MODEL") or "gpt2"

    prompt = f"Crie uma questão de múltipla escolha sobre {topic}. Inclua 4 alternativas (A, B, C, D), indique a resposta correta e uma explicação breve."

    if not api_key:
        logging.info("No Hugging Face API key found in environment.")
        return _local_fallback_question(topic, "Hugging Face API key não definida")

    url = f"https://api-inference.huggingface.co/models/{model}"
    headers = {"Authorization": f"Bearer {api_key}", "Accept": "application/json"}
    payload = {"inputs": prompt, "parameters": {"max_new_tokens": 256}}

    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=30)
    except Exception as e:
        logging.warning("Request to Hugging Face failed: %s", e)
        return _local_fallback_question(topic, f"Request error: {e}")

    if resp.status_code != 200:
        # Try to get any useful message from the response; handle non-JSON bodies
        body = None
        try:
            body = resp.json()
        except Exception:
            body = resp.text or f"HTTP {resp.status_code}"
        logging.warning("Hugging Face inference returned status %s: %s", resp.status_code, body)
        return _local_fallback_question(topic, f"Hugging Face error: {body}")

    # Successful response: try parse JSON and extract text
    try:
        data = resp.json()
    except Exception as e:
        logging.warning("Failed to parse JSON from Hugging Face response: %s", e)
        text = resp.text.strip()
        if text:
            return {"raw": text}
        return _local_fallback_question(topic, "Resposta HF vazia ou inválida")

    # HF may return list or dict; extract generated text
    generated = None
    if isinstance(data, list) and len(data) > 0:
        first = data[0]
        if isinstance(first, dict):
            generated = first.get("generated_text") or first.get("text")
        elif isinstance(first, str):
            generated = first
    elif isinstance(data, dict):
        generated = data.get("generated_text") or data.get("text")

    if generated:
        return {"raw": generated}

    # Nothing usable returned
    logging.warning("Hugging Face returned no generated text: %s", data)
    return _local_fallback_question(topic, "Hugging Face não retornou texto gerado")
