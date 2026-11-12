# Versão 1 — somente correções

Base: `privacidade360-v3-entrevistas-revisadas.zip`. Nada do que já funcionava foi alterado; o roteiro, as telas e as regras jurídicas continuam iguais.

## Checklist

- [x] **1. Tools da IA de verdade** — o turno agora usa *function calling* do Gemini.
- [x] **2. Erros 503 e 429** — passam a usar o modelo reserva em vez de travar a conversa.
- [x] **3. Microfone** — o ditado para ao enviar a mensagem.
- [x] **4. Índices negativos** — a API rejeita índices negativos, texto e posições inexistentes.
- [x] **5. Acentos** — "Admissão" e "Admissao" são o mesmo processo.
- [x] **6. Mensagens de erro** — o usuário vê textos amigáveis, não erros internos do Python.
- [x] **Testes** — novo `tests/test_correcoes.py`. Total: 48 testes, todos passando.

## 1. Tools da IA (`lgpd_agent/prompts.py`, `lgpd_agent/agent.py`)

**Antes:** o Gemini só devolvia um JSON (saída estruturada).
```python
"generationConfig": {"responseMimeType": "application/json", "responseSchema": SCHEMA_TURNO},
...
dados = json.loads(texto_de(partes))
```

**Depois:** o Gemini **chama a ferramenta** `registrar_mapeamento`, com os mesmos campos de antes. Continua sendo uma chamada por turno.
```python
"tools": TOOLS_TURNO,            # declara a função registrar_mapeamento
"toolConfig": TOOL_CONFIG_TURNO, # mode ANY: o modelo deve chamá-la
...
dados = _dados_do_turno(partes)  # lê os argumentos da functionCall (aceita JSON em texto por compatibilidade)
```

## 2. Troca de modelo em 503/429 (`lgpd_agent/gemini.py`)

**Antes:** o modelo reserva só era usado em 404. Com 503, o app tentava 2 vezes e desistia; com 429, desistia na hora.
```python
if e.code == 429:
    raise RuntimeError("Limite de uso do Gemini atingido (429)...")
if e.code == 404:
    break
```

**Depois:** 404 e 429 vão direto para o reserva; 5xx repete e depois vai para o reserva. A mensagem final diz qual foi o problema.
```python
if e.code in (404, 429):
    break                          # tenta o modelo reserva
if e.code in (500, 502, 503, 504):
    if tentativa + 1 < TENTATIVAS:
        time.sleep(.6 * (tentativa + 1)); continue
    break                          # sobrecarga persistente: modelo reserva
```

## 3. Microfone (`static/js/actions.js`)

**Antes:** `enviar()` não parava o reconhecimento de voz, e a próxima fala reescrevia a caixa com o texto já enviado.

**Depois:**
```js
function pararMicrofone() {
  if (!recognition || !recording) return;
  recognition.onresult = null;   // descarta resultados atrasados
  recognition.stop();
}
// em enviar():
pararMicrofone();
```

## 4 e 6. Índices e mensagens (`lgpd_agent/service.py`, `lgpd_agent/server.py`)

**Antes:** `{"acao": "remover", "indice": -1}` removia o último processo, e erros mostravam textos como `pop from empty list`.
```python
ent["processos"].pop(int(corpo["indice"]))
```

**Depois:** todo índice passa por `_item()`, e o servidor só mostra ao usuário mensagens escritas pelo sistema.
```python
ent["processos"].pop(_item(ent["processos"], corpo.get("indice")))
# -> "Processo não encontrado. Atualize a página e tente novamente."
```

## 5. Acentos (`lgpd_agent/mapping.py`)

**Antes:**
```python
if p["nome"].strip().lower() == nome.strip().lower():
```

**Depois:**
```python
alvo = normalizar(nome).strip()
if normalizar(p["nome"]).strip() == alvo:
```

## Como testar

```bash
python -m unittest discover -s tests -v
python app.py
```
