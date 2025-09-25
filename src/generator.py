import os
from dotenv import load_dotenv
from openai import OpenAI
import openai as openai_module
import logging

# Carregar variáveis de ambiente
load_dotenv()


def _get_api_key():
    """Retorna a chave da API a partir de variáveis de ambiente.

    Procura em OPENAI_API_KEY primeiro, depois em DEEPSEEK_API_KEY.
    """
    return os.getenv("OPENAI_API_KEY") or os.getenv("DEEPSEEK_API_KEY")


def _get_client():
    """Cria e retorna um cliente OpenAI usando a chave disponível.

    Evita criar o cliente na importação do módulo para não travar a
    aplicação quando a chave não estiver definida (útil para desenvolvimento).
    """
    api_key = _get_api_key()
    if not api_key:
        return None
    return OpenAI(api_key=api_key, base_url="https://api.deepseek.com")


def generate_question(topic: str):
    client = _get_client()
    if client is None:
        # Retornar fallback local em vez de lançar, garantindo que a rota sempre responda.
        return _local_fallback_question(topic, "OPENAI_API_KEY (ou DEEPSEEK_API_KEY) não definida")

    prompt = (
        f"Crie uma questão de múltipla escolha sobre {topic}. "
        "Inclua 4 alternativas (A, B, C, D), a resposta correta e uma explicação breve."
    )

    try:
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": "Você é um gerador de questões didáticas."},
                {"role": "user", "content": prompt},
            ],
            stream=False,
        )
        # Retornar texto bruto dentro de um dicionário para consistência com o fallback.
        resp_text = response.choices[0].message.content
        return {"raw": resp_text}
    except Exception as e:
        # Log the error and provide a local fallback so the API doesn't return 500.
        logging.warning("OpenAI request failed: %s", e)
        err_text = str(e)
        return _local_fallback_question(topic, err_text)


def _local_fallback_question(topic: str, reason: str = ""):
    """Gera uma questão simples localmente quando o serviço externo falha.

    Retorna um dicionário com campos estruturados para facilitar consumo pelo front-end.
    """
    alternatives = [
        "Alternativa 1",
        "Alternativa 2",
        "Alternativa 3",
        "Alternativa 4",
    ]
    question = {
        "enunciado": f"(Fallback) Sobre {topic}: Qual é a alternativa correta?",
        "alternativas": alternatives,
        "correta": "A",
        "feedback": f"Questão gerada localmente porque o gerador externo falhou: {reason}",
    }
    return question
