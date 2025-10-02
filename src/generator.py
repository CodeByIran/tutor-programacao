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
            # parsed["alternativas"] = [f"{letters[i]}) {a}" for i, a in enumerate(
            #     parsed["alternativas"])]
            parsed["resposta_correta"] = parsed.get(
                "resposta_correta", "").strip().upper()
            return parsed
        raise ValueError(f"Resposta inválida no fallback: {txt}")

    raise RuntimeError(f"Resposta não compreendida: {body}")