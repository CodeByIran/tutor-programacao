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


# def generate_question(topic: str, fase: int = 2, categoria: str = None) -> Dict[str, Any]:
#     """
#     Gera uma questão de múltipla escolha estilo ONIA.
#     - categoria: macro área (ex.: Conceitual, Ética, Lógica, Aplicações)
#     - topic: subtema específico (ex.: Conhecimento de padrão, Teste de Turing, Deepfakes)
#     """

#     try:
#         fase = int(fase)
#     except Exception:
#         fase = 2
#     if fase not in (1, 2):
#         fase = 2

#     letters = ["A", "B", "C", "D", "E"]
#     num_alts = 4 if fase == 1 else 5

# # refatoração de categorias
#     _raw_categorias = {
#         "Lógica/Algoritmo": ["logica", "lógica", "raciocinio", "raciocínio"],
#         "Conceitual": ["conceitual", "teorica", "teórica", "teorico"],
#         "Ética e Sociedade": ["etica", "ética", "sociedade"],
#         "Aplicações e História": ["aplicacoes", "aplicações"],
#     }
#     CATEGORIAS = {k: cat for k, keys in _raw_categorias.items()
#                   for cat in keys}

#     cat_key = (categoria or "").strip().lower()
#     cat_desc = CATEGORIAS.get(cat_key, "Geral")

#     prompt = f"""
# Você é um gerador de questões da Olimpíada Nacional de Inteligência Artificial (ONIA).
# (Categoria: {cat_desc})
# Tópico específico: {topic}

# Gere UMA questão de múltipla escolha com {num_alts} alternativas, rotuladas com letras {', '.join(letters[:num_alts])}.

# As questões devem seguir 4 pilares obrigatórios:
# 1. Foco Interdisciplinar e Técnico: incluir conceitos fundamentais de IA (definições, história, algoritmos clássicos como DFS/BFS).
# 2. Complexidade Algorítmica: explorar raciocínio lógico, padrões, máquinas de estados, big data, vetores, comandos e sequências.
# 3. Relevância Ética e Social: abordar vieses, direitos autorais, neutralidade, limiares e implicações sociais da IA.
# 4. Fidelidade ao Formato ONIA: contextualizar o enunciado em cenários realistas, com alternativas consistentes e gabarito claro.

# Responda SOMENTE com um JSON válido no formato:
# {{
#   "categoria": string,
#   "topico": string,
#   "pergunta": string,
#   "alternativas": [string,...],
#   "resposta_correta": string (wuma letra como 'A'),
#   "explicacao": string (curta, do porquê a correta é correta)
#   "explicacoes_erradas": [string,...]  # explicação breve para cada alternativa incorreta
# }}
# Cada alternativa deve conter apenas o texto (sem prefixo de letra).
# """
#     result = call_huggingface_api(prompt, num_alts, letters)
# # Garante que o JSON tenha lista de explicações para alternativas erradas
#     if "explicacoes_erradas" not in result or not isinstance(result["explicacoes_erradas"], list):
#         # Cria lista de explicações vazias exceto para a correta
#         result["explicacoes_erradas"] = [
#             "" if letters[i] == result.get(
#                 "resposta_correta") else "Explicação breve do porquê está errada"
#             for i in range(num_alts)
#         ]

#     return result

def generate_question(topic: str, fase: int = 2, categoria: str = None) -> Dict[str, Any]:
    """
    Gera uma questão de múltipla escolha estilo ONIA 3ª fase (Categoria Regular),
    baseada em Python e raciocínio lógico.
    """

    try:
        fase = int(fase)
    except Exception:
        fase = 2
    if fase not in (1, 2):
        fase = 2

    letters = ["A", "B", "C", "D", "E"]
    num_alts = 4 if fase == 1 else 5

    # Refatoração de categorias
    _raw_categorias = {
        "Lógica/Algoritmo": ["logica", "lógica", "raciocinio", "raciocínio"],
        "Conceitual": ["conceitual", "teorica", "teórica", "teorico"],
        "Ética e Sociedade": ["etica", "ética", "sociedade"],
        "Aplicações e História": ["aplicacoes", "aplicações"],
    }
    CATEGORIAS = {k: cat for k, keys in _raw_categorias.items() for cat in keys}
    cat_key = (categoria or "").strip().lower()
    cat_desc = CATEGORIAS.get(cat_key, "Geral")

    # Novo prompt baseado no estilo da 3ª fase da ONIA
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

    result = call_huggingface_api(prompt, num_alts, letters)

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


def call_huggingface_api(prompt: str, num_alts: int = 5, letters=None) -> Dict[str, Any]:
    """
    Envia prompt para HuggingFace (InferenceClient ou requests) e retorna JSON da questão.
    """
    letters = letters or ["A", "B", "C", "D", "E"]

    # Tenta usar InferenceClient se disponível
    if InferenceClient and API_KEY:
        try:
            client = InferenceClient(token=API_KEY)
            r = client.chat_completion(
                model=MODEL,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=400,
            )
            text = r.get("choices", [{}])[0].get(
                "message", {}).get("content", "")
            parsed = _find_json(text)
            if parsed:
                return format_question(parsed, num_alts, letters)
            raise ValueError(f"Resposta inválida do modelo: {text}")
        except Exception as e:
            raise RuntimeError(f"Erro no InferenceClient: {e}")

    # Fallback usando requests
    url = ENDPOINT or f"https://api-inference.huggingface.co/models/{MODEL}"
    headers = {"Authorization": f"Bearer {API_KEY}"} if API_KEY else {}
    try:
        r = requests.post(url, headers=headers, json={
                          "inputs": prompt}, timeout=60)
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
