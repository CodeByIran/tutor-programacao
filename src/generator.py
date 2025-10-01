import os
import re
import json
import requests
from typing import Any, Dict

API_KEY = (
    os.getenv("HF_TOKEN")
    or os.getenv("HF_API_KEY")
    or os.getenv("HUGGINGFACE_API_KEY")
)
MODEL = os.getenv(
    "HUGGINGFACE_MODEL") or "meta-llama/Llama-4-Scout-17B-16E-Instruct"
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
        candidate = s[i:j+1]
    else:
        candidate = m.group(1)
    try:
        return json.loads(candidate)
    except Exception:
        return None


def generate_question(topic: str, fase: int = 2, categoria: str = None) -> Dict[str, Any]:
    """
    Gera uma questão de múltipla escolha estilo ONIA usando somente o Llama.
    Retorna sempre dict com pergunta, alternativas e resposta_correta.
    """

    # normaliza fase
    try:
        fase = int(fase)
    except Exception:
        fase = 2
    if fase not in (1, 2):
        fase = 2

    letters = ["A", "B", "C", "D", "E"]
    num_alts = 4 if fase == 1 else 5

    # # categoria → intro
    # cat = (categoria or "").strip().lower()
    # if cat in ("logica", "lógica", "raciocinio", "raciocínio"):
    #     intro = "(Lógica/Algoritmo) Questão que exige raciocínio, padrão, sequência, comandos ou travessias de grafos."
    # elif cat in ("conceitual", "teorica", "teórica", "teorico"):
    #     intro = "(Conceitual) Questão sobre definições, história, tipos de IA ou princípios teóricos."
    # elif cat in ("etica", "ética", "sociedade"):
    #     intro = "(Ética) Questão sobre vieses, riscos sociais, deepfakes, privacidade e implicações éticas."
    # else:
    #     intro = "(Geral) Questão alinhada ao estilo ONIA: conceitual, lógica, ética ou aplicação prática."

    # categorias → intro
    CATEGORIAS = {
        "logica": "(Lógica/Algoritmo) Questão que exige raciocínio, padrão, sequência, comandos ou travessias de grafos.",
        "lógica": "(Lógica/Algoritmo) Questão que exige raciocínio, padrão, sequência, comandos ou travessias de grafos.",
        "raciocinio": "(Lógica/Algoritmo) Questão que exige raciocínio, padrão, sequência, comandos ou travessias de grafos.",
        "raciocínio": "(Lógica/Algoritmo) Questão que exige raciocínio, padrão, sequência, comandos ou travessias de grafos.",
        "conceitual": "(Conceitual) Questão sobre definições, história, tipos de IA ou princípios teóricos.",
        "teorica": "(Conceitual) Questão sobre definições, história, tipos de IA ou princípios teóricos.",
        "teórica": "(Conceitual) Questão sobre definições, história, tipos de IA ou princípios teóricos.",
        "teorico": "(Conceitual) Questão sobre definições, história, tipos de IA ou princípios teóricos.",
        "etica": "(Ética) Questão sobre vieses, riscos sociais, deepfakes, privacidade e implicações éticas.",
        "ética": "(Ética) Questão sobre vieses, riscos sociais, deepfakes, privacidade e implicações éticas.",
        "sociedade": "(Ética) Questão sobre vieses, riscos sociais, deepfakes, privacidade e implicações éticas.",
    }

    cat = (categoria or "").strip().lower()
    intro = CATEGORIAS.get(
        cat,
        "(Geral) Questão alinhada ao estilo ONIA: conceitual, lógica, ética ou aplicação prática."
    )
    # instrução rígida
    prompt = (
        f"Você é um gerador de questões da Olimpíada Nacional de Inteligência Artificial (ONIA). "
        f"{intro} Gere UMA questão de múltipla escolha sobre: {topic}. "
        f"Use exatamente {num_alts} alternativas e rotule-as com letras {', '.join(letters[:num_alts])}. "

        # Ideologia ONIA
        "As questões devem seguir 4 pilares obrigatórios: \n"
        "1. Foco Interdisciplinar e Técnico: incluir conceitos fundamentais de IA (definições, história, tipos de aprendizado, algoritmos clássicos como DFS/BFS). \n"
        "2. Complexidade Algorítmica: explorar raciocínio lógico, padrões, máquinas de estados, big data, vetores, comandos e análise de sequências. \n"
        "3. Relevância Ética e Social: abordar vieses, direitos autorais, neutralidade, limiares e implicações sociais da IA. \n"
        "4. Fidelidade ao Formato ONIA: contextualizar o enunciado em cenários realistas e fornecer alternativas consistentes, com gabarito claro. \n"

        # Estrutura rígida de saída
        "Responda EXCLUSIVAMENTE com um JSON válido com os campos: \n"
        "{\n"
        "  \"pergunta\": string,\n"
        "  \"alternativas\": [string,...],\n"
        "  \"resposta_correta\": string (uma letra como 'A'),\n"
        "  \"explicacao\": string (opcional, curta)\n"
        "}\n"
        "Cada alternativa deve ser apenas o texto (sem prefixo de letra). "
        "Responda SOMENTE com JSON válido, sem comentários, sem markdown e sem nada fora da estrutura definida."
    )

    # 1 - Tentar com InferenceClient
    if InferenceClient and API_KEY:
        try:
            client = InferenceClient(token=API_KEY)
            r = client.chat_completion(
                model=MODEL,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=400,
            )
            text = (
                r.get("choices", [])[0]
                .get("message", {})
                .get("content", "")
            )
            parsed = _find_json(text)
            if parsed and isinstance(parsed, dict):
                alts = parsed.get("alternativas")
                if isinstance(alts, list) and len(alts) == num_alts:
                    parsed["alternativas"] = [
                        f"{letters[i]}) {a}" for i, a in enumerate(alts)
                    ]
                    parsed["resposta_correta"] = (
                        parsed.get("resposta_correta", "").strip().upper()
                    )
                    return parsed
            raise ValueError(f"Resposta inválida do modelo: {text}")
        except Exception as e:
            raise RuntimeError(f"Erro no InferenceClient: {e}")

    # 2 - fallback HTTP cru (requests)
    url = ENDPOINT or f"https://api-inference.huggingface.co/models/{MODEL}"
    headers = {"Authorization": f"Bearer {API_KEY}"} if API_KEY else {}
    try:
        r = requests.post(url, headers=headers, json={
                          "inputs": prompt}, timeout=60)
    except Exception as e:
        raise RuntimeError(f"Erro de conexão no requests: {e}")

    if r.status_code != 200:
        raise RuntimeError(f"Erro HTTP {r.status_code}: {r.text}")

    try:
        body = r.json()
    except Exception:
        body = r.text

    if isinstance(body, list) and body and isinstance(body[0], dict):
        txt = body[0].get("generated_text") or body[0].get("text")
        parsed = _find_json(txt or "")
        if parsed and isinstance(parsed.get("alternativas"), list) and len(parsed["alternativas"]) == num_alts:
            parsed["alternativas"] = [f"{letters[i]}) {a}" for i, a in enumerate(
                parsed["alternativas"])]
            parsed["resposta_correta"] = parsed.get(
                "resposta_correta", "").strip().upper()
            return parsed
        raise ValueError(f"Resposta inválida no fallback: {txt}")

    raise RuntimeError(f"Resposta não compreendida: {body}")


# import os
# import re
# import json
# import requests
# from typing import Any, Dict, List

# API_KEY = os.getenv("HF_TOKEN") or os.getenv("HF_API_KEY") or os.getenv("HUGGINGFACE_API_KEY")
# MODEL = os.getenv("HUGGINGFACE_MODEL") or "meta-llama/Llama-4-Scout-17B-16E-Instruct"
# ENDPOINT = os.getenv("HUGGINGFACE_ENDPOINT")

# try:
#     from huggingface_hub import InferenceClient
# except Exception:
#     InferenceClient = None


# def _fallback(topic: str, fase: int = 2) -> Dict[str, Any]:
#     # gera um fallback simples consistente com a fase: fase 1 -> 4 alternativas (A-D), fase 2 -> 5 alternativas (A-E)
#     letters = ["A", "B", "C", "D", "E"]
#     if fase == 1:
#         raw = ["alternativa A", "alternativa B", "alternativa C", "alternativa D"]
#     else:
#         raw = ["alternativa A", "alternativa B", "alternativa C", "alternativa D", "alternativa E"]
#     alts = [f"{letters[i]}) {txt}" for i, txt in enumerate(raw)]
#     correct = "A"
#     return {"pergunta": f"(Fallback) Sobre {topic}", "alternativas": alts, "resposta_correta": correct}


# def _find_json(s: str):
#     # pega bloco JSON entre ``` ou o primeiro { ... }
#     m = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", s, flags=re.DOTALL)
#     if not m:
#         i = s.find("{")
#         j = s.rfind("}")
#         if i == -1 or j == -1:
#             return None
#         candidate = s[i:j+1]
#     else:
#         candidate = m.group(1)
#     try:
#         return json.loads(candidate)
#     except Exception:
#         return None


# def generate_question(topic: str, fase: int = 2, categoria: str = None) -> Any:
#     """
#     Gera uma questão de múltipla escolha sobre `topic` seguindo o formato ONIA.

#     Args:
#         topic: tópico da questão (ex: 'raciocínio lógico', 'história da IA').
#         fase: 1 -> 4 alternativas (A-D). 2 -> 5 alternativas (A-E). Default 2.

#     Retorna:
#         dict com chaves: pergunta (str), alternativas (list[str]), resposta_correta (str letra).
#     """
#     # normaliza fase
#     try:
#         fase = int(fase)
#     except Exception:
#         fase = 2
#     if fase not in (1, 2):
#         fase = 2

#     letters = ["A", "B", "C", "D", "E"]
#     num_alts = 4 if fase == 1 else 5

#     # mapeamento simples de templates por categoria
#     cat = (categoria or "").strip().lower() if categoria else ""
#     if cat in ("logica", "lógica", "raciocinio", "raciocínio"):
#         intro = "(Lógica/Algoritmo) Questão que exige raciocínio, padrão, sequência, comandos ou travessias de grafos."
#     elif cat in ("conceitual", "teorica", "teórica", "teorico"):
#         intro = "(Conceitual) Questão sobre definições, história, tipos de IA ou princípios teóricos."
#     elif cat in ("etica", "ética", "sociedade"):
#         intro = "(Ética) Questão sobre vieses, riscos sociais, deepfakes, privacidade e implicações éticas."
#     else:
#         intro = "(Geral) Questão alinhada ao estilo ONIA: conceitual, lógica, ética ou aplicação prática."

#     # instrução rígida para o LLM: produzir apenas JSON válido e seguir o esquema ONIA
#     prompt = (
#         f"Você é um gerador de questões estilo Olimpíada Nacional de Inteligência Artificial (ONIA). "
#         f"{intro} Gere UMA questão de múltipla escolha sobre: {topic}. "
#         f"Use exatamente {num_alts} alternativas e rotule-as com letras {', '.join(letters[:num_alts])}. "
#         "Responda EXCLUSIVAMENTE com um JSON válido com os campos: \n"
#         "{\n  \"pergunta\": string,\n  \"alternativas\": [string,...],\n  \"resposta_correta\": string (uma letra como 'A'),\n  \"explicacao\": string (opcional, curta)\n}\n"
#         "Cada elemento em 'alternativas' deve ser apenas o texto da alternativa (sem prefixo de letra). "
#         "Responda SOMENTE com JSON válido, sem comentários, sem markdown, sem explicação fora do JSON. Se você incluir qualquer coisa fora do JSON, será considerado erro"
#         # "Não inclua explicações nem texto adicional fora do campo 'explicacao'. Não coloque código ou markdown, apenas o JSON."
#     )

#     if InferenceClient and API_KEY:
#         try:
#             client = InferenceClient(token=API_KEY)
#             try:
#                 res = client.text_generation(prompt, model=MODEL, max_new_tokens=200)
#                 text = res if isinstance(res, str) else (res.get("generated_text") if isinstance(res, dict) else str(res))
#             except Exception:
#                 # tentar chat simples
#                 try:
#                     r = client.chat_completion(model=MODEL, messages=[{"role":"user","content":prompt}])
#                     text = r.get("choices", [])[0].get("message", {}).get("content") if isinstance(r, dict) else str(r)
#                 except Exception:
#                     text = None

#             if text:
#                 parsed = _find_json(text)
#                 if parsed and isinstance(parsed, dict):
#                     # garante número de alternativas correto
#                     alts = parsed.get("alternativas")
#                     if isinstance(alts, list) and len(alts) == num_alts:
#                         # prefixa alternativas com letras antes de retornar e mantém explicacao se houver
#                         prefixed = [f"{letters[i]}) {a}" for i, a in enumerate(alts)]
#                         parsed["alternativas"] = prefixed
#                         if parsed.get("resposta_correta") and isinstance(parsed.get("resposta_correta"), str):
#                             parsed["resposta_correta"] = parsed["resposta_correta"].strip().upper()
#                         return parsed
#                 # se parse falhar ou formato incorreto, tenta continuar para o próximo fallback
#                 # (mantemos text para debug quando nada mais funcionar)
#         except Exception:
#             pass

#     # 2 - fallback HTTP
#     url = ENDPOINT or f"https://api-inference.huggingface.co/models/{MODEL}"
#     headers = {"Authorization": f"Bearer {API_KEY}"} if API_KEY else {}
#     try:
#         r = requests.post(url, headers=headers, json={"inputs": prompt}, timeout=60)
#     except Exception:
#         return _fallback(topic, fase=fase)

#     if r.status_code != 200:
#         return _fallback(topic, fase=fase)

#     try:
#         body = r.json()
#     except Exception:
#         body = r.text

#     if isinstance(body, str):
#         parsed = _find_json(body)
#         if parsed and isinstance(parsed, dict):
#             if isinstance(parsed.get("alternativas"), list) and len(parsed.get("alternativas")) == num_alts:
#                 # prefixa
#                 alts = parsed.get("alternativas")
#                 parsed["alternativas"] = [f"{letters[i]}) {a}" for i, a in enumerate(alts)]
#                 if parsed.get("resposta_correta"):
#                     parsed["resposta_correta"] = parsed["resposta_correta"].strip().upper()
#                 return parsed
#         return parsed or body

#     # handle typical HF list response
#     if isinstance(body, list) and body and isinstance(body[0], dict):
#         txt = body[0].get("generated_text") or body[0].get("text")
#         parsed = _find_json(txt or "")
#         if parsed and isinstance(parsed, dict):
#             if isinstance(parsed.get("alternativas"), list) and len(parsed.get("alternativas")) == num_alts:
#                 alts = parsed.get("alternativas")
#                 parsed["alternativas"] = [f"{letters[i]}) {a}" for i, a in enumerate(alts)]
#                 if parsed.get("resposta_correta"):
#                     parsed["resposta_correta"] = parsed["resposta_correta"].strip().upper()
#                 return parsed
#         return parsed or (txt or body[0])

#     # se nada funcionou, tente extrair JSON do texto bruto
#     parsed = None
#     try:
#         text = r.text
#         parsed = _find_json(text)
#         if parsed and isinstance(parsed, dict) and isinstance(parsed.get("alternativas"), list) and len(parsed.get("alternativas")) == num_alts:
#             alts = parsed.get("alternativas")
#             parsed["alternativas"] = [f"{letters[i]}) {a}" for i, a in enumerate(alts)]
#             if parsed.get("resposta_correta"):
#                 parsed["resposta_correta"] = parsed["resposta_correta"].strip().upper()
#             return parsed
#     except Exception:
#         pass

#     # último recurso: fallback que respeita a fase
#     return _fallback(topic, fase=fase)
