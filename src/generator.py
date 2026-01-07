import os
import re
import json
from unittest import result
import requests
from typing import Any, Dict


API_KEY = (
    os.getenv("HF_TOKEN")
    or os.getenv("HF_API_KEY")
    or os.getenv("HUGGINGFACE_API_KEY")
)
MODEL = os.getenv(
    "HUGGINGFACE_MODEL"
) or "meta-llama/Llama-4-Scout-17B-16E-Instruct"
ENDPOINT = os.getenv("HUGGINGFACE_ENDPOINT")

try:
    from huggingface_hub import InferenceClient
except Exception:
    InferenceClient = None


def _find_json(s: str):
    """Extrai bloco JSON válido de uma string"""
    m = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", s, flags=re.DOTALL)
    if not m:
        i = s.find("{")
        j = s.rfind("}")
        if i == -1 or j == -1:
            return None
        candidate = s[i: j + 1]
    else:
        candidate = m.group(1)
    try:
        return json.loads(candidate)
    except Exception:
        return None
    
AVAILABLE_MODELS = {
    "llama": "meta-llama/Llama-4-Scout-17B-16E-Instruct",
    "depseeack": "deepseek-ai/DeepSeek-Coder-V2-Lite-Instruct",
    "starcoder": "bigcode/starcoder-2-7b",
    "gpt": "openai/gpt-oss-safeguard-20b",
}

def generate_question(topic: str, fase: int = 2, categoria: str = None, model: str = "llama") -> Dict[str, Any]:
    """
    Gera uma questão de múltipla escolha estilo ONIA 3ª fase (Categoria Regular),
    baseada em Python e raciocínio lógico.
    Permite escolher o modelo LLM da Hugging Face via parâmetro `model`.
    """

    if model not in AVAILABLE_MODELS:
        return {"error": f"Modelo '{model}' não disponível. Modelos válidos: {list(AVAILABLE_MODELS.keys())}"}

    model_name = AVAILABLE_MODELS[model]
    
    
    try:
        fase = int(fase)
    except Exception:
        fase = 2
    if fase not in (1, 2):
        fase = 2

    letters = ["A", "B", "C", "D", "E"]
    num_alts = 4 if fase == 1 else 5
    
    _raw_categorias = {
        "Lógica/Algoritmo": ["logica", "lógica", "raciocinio", "raciocínio"],
        "Conceitual": ["conceitual", "teorica", "teórica", "teorico"],
        "Ética e Sociedade": ["etica", "ética", "sociedade"],
        "Aplicações e História": ["aplicacoes", "aplicações"],
    }
    CATEGORIAS = {k: cat for k, keys in _raw_categorias.items() for cat in keys}
    cat_key = (categoria or "").strip().lower()
    cat_desc = CATEGORIAS.get(cat_key, "Geral")


    # 3. Inclua **o trecho de código Python dentro do enunciado** (não como campo separado).
    prompt = f"""
Você é um gerador de questões da Olimpíada Nacional de Inteligência Artificial (ONIA) - Categoria Regular.
(Categoria: {cat_desc})
Tópico específico: {topic}

Siga esta metodologia para gerar UMA questão de múltipla escolha com {num_alts} alternativas, rotuladas {', '.join(letters[:num_alts])}:

1. Introduza o conceito Python relevante (tipos, variáveis, strings, listas, funções, laços, condicionais).
2. Crie um cenário ou contexto realista aplicando o conceito.
3. Inclua um snippet de código que deve ser analisado ou completado.
4. Faça a pergunta de múltipla escolha (A–E).
5. Explique brevemente a resposta correta e forneça explicações curtas para cada alternativa incorreta.

Responda SOMENTE com um JSON válido no formato:
{{
  "categoria": string,
  "topico": string,
  "pergunta": string,
  "alternativas": [string,...],
  "resposta_correta": string (uma letra 'A'–'E'),
  "explicacao": string,
  "explicacoes_erradas": [string,...]
}}
"""
    #result = call_huggingface_api(prompt, num_alts, letters)
    raw=call_huggingface_api(prompt, num_alts, letters, model_name=model_name)
    if isinstance(raw, dict):
         result = raw
    else:
         result = _find_json(raw)    
    if result is None:
        return {"error": "Resposta inválida do modelo", "raw": raw}
    
    # Garante explicações para alternativas incorretas
    if "explicacoes_erradas" not in result or not isinstance(result["explicacoes_erradas"], list):
        result["explicacoes_erradas"] = [
            "" if letters[i] == result.get("resposta_correta") else "Explicação breve do porquê está errada"
            for i in range(num_alts)
        ]

    return result


def format_question(parsed: Dict[str, Any], num_alts: int, letters: list) -> Dict[str, Any]:
    """
    Formata as alternativas adicionando letras e ajusta a resposta correta.
    """
    alts = parsed.get("alternativas")
    if isinstance(alts, list) and len(alts) == num_alts:
        parsed["alternativas"] = [
            f"{letters[i]}) {a}" for i, a in enumerate(alts)]
        parsed["resposta_correta"] = parsed.get(
            "resposta_correta", "").strip().upper()
        return parsed
    raise ValueError("Formato de alternativas inválido no JSON retornado")


def call_huggingface_api(prompt: str, num_alts: int = 5, letters=None, model_name: str = None) -> Dict[str, Any]:
    """
    Envia prompt para HuggingFace (InferenceClient ou requests) e retorna JSON da questão.
    Permite escolher o modelo via parâmetro `model_name`.
    """
    letters = letters or ["A", "B", "C", "D", "E"]
    model_to_use = model_name or MODEL  # usa o modelo passado ou o default do ambiente

    # Tenta usar InferenceClient se disponível
    if InferenceClient and API_KEY:
        try:
            client = InferenceClient(token=API_KEY)
            r = client.chat_completion(
                model=model_to_use,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=400,
            )
            text = r.get("choices", [{}])[0].get("message", {}).get("content", "")
            parsed = _find_json(text)
            if parsed:
                return format_question(parsed, num_alts, letters)
            raise ValueError(f"Resposta inválida do modelo: {text}")
        except Exception as e:
            raise RuntimeError(f"Erro no InferenceClient: {e}")

    # Fallback usando requests
    url = ENDPOINT or f"https://api-inference.huggingface.co/models/{model_to_use}"
    headers = {"Authorization": f"Bearer {API_KEY}"} if API_KEY else {}
    try:
        r = requests.post(url, headers=headers, json={"inputs": prompt}, timeout=60)
        r.raise_for_status()
    except Exception as e:
        raise RuntimeError(f"Erro de conexão no requests: {e}")

    try:
        body = r.json()
    except Exception:
        body = r.text

    if isinstance(body, list) and body and isinstance(body[0], dict):
        txt = body[0].get("generated_text") or body[0].get("text", "")
        parsed = _find_json(txt or "")
        if parsed:
            return format_question(parsed, num_alts, letters)
        raise ValueError(f"Resposta inválida no fallback: {txt}")

    raise RuntimeError(f"Resposta não compreendida: {body}")


def generate_questions(topic: str, quantidade: int = 5, fase: int = 2, categoria: str = None, model: str = "llama") -> list:
    """Gera um lote de questões usando `generate_question`.

    Retorna lista de dicionários com as questões geradas (ou itens de erro quando ocorrer).
    """
    results = []
    for i in range(int(quantidade)):
        try:
            q = generate_question(topic, fase=fase, categoria=categoria, model=model)
            results.append(q)
        except Exception as e:
            results.append({"error": f"Erro ao gerar questão #{i+1}: {e}"})
    return results