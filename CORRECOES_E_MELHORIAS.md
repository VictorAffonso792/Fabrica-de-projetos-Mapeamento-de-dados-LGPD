# Versão 2 — correções + melhorias

Inclui **todas as correções da Versão 1** (veja `CORRECOES.md`) e mais as melhorias abaixo.

## Checklist

- [x] **Correções 1 a 6** — iguais à Versão 1.
- [x] **7. Agente menos robótico** — o Gemini formula a pergunta; o Python continua decidindo o assunto.
- [x] **8. Entrevista mais curta** — perguntas agrupadas: 6 por processo em vez de 11.
- [x] **9. Relatório sem duplicidade** — a base legal sai da lista de "Lacunas".
- [x] **10. Configuração tolerante** — valores inválidos no `.env` não travam o app.
- [x] **11. Código mais limpo** — uma só regra de lacunas, código morto removido, import no topo.
- [x] **Testes** — novo `tests/test_melhorias.py`. Total: 58 testes, todos passando.

## 7. Pergunta natural (`agent.py`, `prompts.py`, `config.py`)

**Antes:** a resposta do Gemini era descartada, e o chat mostrava sempre o texto fixo:
> Qual é a finalidade principal da atividade 'Recrutamento'?

**Depois:** o roteiro em Python escolhe **o que** perguntar, e o Gemini escolhe **como** perguntar, reconhecendo o que o líder acabou de dizer:
> Ótimo, anotei que vocês cuidam do recrutamento! Para que ele serve e por que precisam desses dados?

```python
texto = definir_proxima_resposta(ent, ultima, len(registros))
if controle(ent).get("pergunta_atual"):          # há pergunta nova do roteiro
    texto = formular_pergunta(ent, ultima, texto)  # Gemini reescreve; se falhar, usa o texto fixo
```

Segurança da mudança: se a chamada falhar, vier em JSON, vazia, longa demais ou sem pergunta, o sistema usa a pergunta fixa. A entrevista nunca trava por causa disso.

Custo: são **2 chamadas por mensagem** em vez de 1. Para voltar ao comportamento antigo (mais rápido), use `PERGUNTAS_NATURAIS=0` no `.env`.

## 8. Perguntas agrupadas (`interview_flow.py`)

**Antes:** um campo por pergunta, 11 perguntas por processo.

**Depois:** os mesmos 6 grupos da tela de Mapeamento.

| Grupo | Campos |
|---|---|
| 1 | finalidade + justificativa |
| 2 | titulares + dados pessoais + dados sensíveis |
| 3 | coleta |
| 4 | armazenamento + retenção |
| 5 | compartilhamento + transferência internacional |
| 6 | segurança |

```python
campos = [x for x in grupo_de(proximo["campo"]) if x in mesmo_processo]
c["pergunta_atual"] = {"processo": ..., "campo": campos[0], "campos": campos}
return prefixo + montar_pergunta(proximo["processo"], campos)
```

Regras para não perder informação:
- Se o líder responder **parte** do grupo, o que faltou é perguntado sozinho logo em seguida.
- Se responder "não sei" para o grupo inteiro, o grupo é **adiado** (mesmo comportamento de antes).
- O sistema termina um grupo antes de passar ao próximo.

## 9. Relatório (`report.py`)

**Antes:** a base legal aparecia em "Revisão jurídica necessária" **e** em "Lacunas".

**Depois:** "Lacunas" mostra só as pendências operacionais.

## 10. Configuração (`config.py`)

**Antes:**
```python
PORTA = int(configurar("PORTA", "8000"))   # PORTA=abc -> app não abre
```

**Depois:**
```python
PORTA = _inteiro("PORTA", 8000, 1, 65535)  # avisa no terminal e usa 8000
```

## 11. Limpeza

- `mapping.lacunas()` agora usa `interview_flow.lacunas_detalhadas()`, então existe uma só regra.
- A ferramenta antiga `consultar_lacunas`, que ninguém chamava, foi removida.
- O import de `resumo_pendencias` em `service.py` foi para o topo do arquivo.

## Como testar

```bash
python -m unittest discover -s tests -v
python app.py
```
