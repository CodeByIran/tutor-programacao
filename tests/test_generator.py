import pytest
from src import generator


def test_generate_fase1_structure():
    q = generator.generate_question('sequencias', fase=1)
    assert isinstance(q, dict)
    assert 'pergunta' in q and isinstance(q['pergunta'], str)
    assert 'alternativas' in q and isinstance(q['alternativas'], list)
    assert len(q['alternativas']) == 4
    # alternativas devem começar com A) B) C) D)
    assert q['alternativas'][0].strip().startswith('A)')
    assert q['resposta_correta'] in ('A','B','C','D')


def test_generate_fase2_structure():
    q = generator.generate_question('ética em IA', fase=2)
    assert isinstance(q, dict)
    assert 'pergunta' in q and isinstance(q['pergunta'], str)
    assert 'alternativas' in q and isinstance(q['alternativas'], list)
    assert len(q['alternativas']) == 5
    # alternativas devem começar com A) ... E)
    assert q['alternativas'][4].strip().startswith('E)')
    assert q['resposta_correta'] in ('A','B','C','D','E')
