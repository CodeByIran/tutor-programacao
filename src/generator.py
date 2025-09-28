import os
import re
import requests
from typing import Any, Dict

# config
API_KEY = os.getenv("HF_TOKEN") or os.getenv("HF_API_KEY") or os.getenv("HUGGINGFACE_API_KEY")
MODEL = os.getenv("HUGGINGFACE_MODEL") or "meta-llama/Llama-4-Scout-17B-16E-Instruct"
ENDPOINT = os.getenv("HUGGINGFACE_ENDPOINT")

try:
    from huggingface_hub import InferenceClient
except Exception:
    InferenceClient = None


def _local_fallback(topic: str) -> Dict[str, Any]:
    return {"pergunta": f"(Fallback) Sobre {topic}", "alternativas": ["A","B","C","D"], "resposta_correta": "A"}


def _extract_json_from_text(text: str) -> Any:
    # prefer ```json {...}``` or ```{...}``` blocks
    m = re.search(r"```json\s*(\{.*?\})\s*```", text, flags=re.DOTALL)
    if not m:
        m = re.search(r"```\s*(\{.*?\})\s*```", text, flags=re.DOTALL)
    if not m:
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and end > start:
            candidate = text[start:end+1]
        else:
            return None
    else:
        candidate = m.group(1)

    try:
        import json
        return json.loads(candidate)
    except Exception:
        return None


def generate_question(topic: str) -> Any:
    prompt = f"Crie uma questão de múltipla escolha sobre {topic}. Retorne um JSON com pergunta, alternativas e resposta_correta."

    # 1) prefer HF client
    if InferenceClient and API_KEY:
        client_error = None
        try:
            client = InferenceClient(token=API_KEY, timeout=60)
            try:
                out = client.text_generation(prompt, model=MODEL, max_new_tokens=256)
            except Exception as e_text:
                # try conversational/chat completion if text_generation unsupported
                try:
                    if hasattr(client, 'chat_completion'):
                        out = client.chat_completion(model=MODEL, messages=[{"role": "user", "content": prompt}])
                    else:
                        out = client.chat(model=MODEL, messages=[{"role": "user", "content": prompt}])
                except Exception as e_chat:
                    client_error = f"text_error: {e_text}; chat_error: {e_chat}"
                    out = None

            if out is not None:
                # parse output
                if isinstance(out, str):
                    parsed = _extract_json_from_text(out)
                    return parsed if parsed is not None else out
                if isinstance(out, dict):
                    if "generated_text" in out:
                        parsed = _extract_json_from_text(out["generated_text"])
                        return parsed if parsed is not None else out["generated_text"]
                    if "choices" in out and len(out["choices"])>0:
                        content = out["choices"][0].get("message", {}).get("content") or out["choices"][0].get("text")
                        if content:
                            parsed = _extract_json_from_text(content)
                            return parsed if parsed is not None else content
                    return out
        except Exception as e:
            client_error = str(e)

    # 2) HTTP fallback
    url = ENDPOINT if ENDPOINT else f"https://api-inference.huggingface.co/models/{MODEL}"
    headers = {"Authorization": f"Bearer {API_KEY}"} if API_KEY else {}
    try:
        resp = requests.post(url, headers=headers, json={"inputs": prompt}, timeout=30)
    except Exception as e:
        return {"error": "http_request_failed", "details": str(e), "client_error": client_error if 'client_error' in locals() else None, "fallback": _local_fallback(topic)}

    if resp.status_code != 200:
        # include client_error if available for diagnostics
        return {"error": "http_status", "status": resp.status_code, "body": resp.text, "client_error": client_error if 'client_error' in locals() else None, "fallback": _local_fallback(topic)}

    # parse response
    try:
        body = resp.json()
    except Exception:
        body = resp.text

    if isinstance(body, str):
        parsed = _extract_json_from_text(body)
        return parsed if parsed is not None else body

    if isinstance(body, list) and len(body)>0 and isinstance(body[0], dict) and "generated_text" in body[0]:
        parsed = _extract_json_from_text(body[0]["generated_text"])
        return parsed if parsed is not None else body[0]["generated_text"]

    return body if body else {"error": "empty_response", "fallback": _local_fallback(topic)}
