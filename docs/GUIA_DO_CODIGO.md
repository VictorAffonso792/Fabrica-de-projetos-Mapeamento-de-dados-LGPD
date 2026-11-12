# Guia do código — Privacidade 360

Este guia explica **o que cada parte faz**, como elas se comunicam e **onde você deve editar** no VS Code. Foi escrito para facilitar a manutenção por quem está começando a trabalhar no projeto.

## 1. Como o sistema funciona (visão simples)

1. Você abre `app.py` no VS Code e executa `python app.py`.
2. `lgpd_agent/server.py` inicia um servidor local e disponibiliza a interface web.
3. O navegador carrega `static/index.html`, os estilos de `static/css/` e o JavaScript de `static/js/`.
4. Ao criar ou abrir uma entrevista, o navegador chama rotas `/api/entrevistas` do servidor.
5. As ações chegam a `lgpd_agent/service.py`, que organiza cada alteração.
6. Ao enviar uma resposta, `lgpd_agent/agent.py` conversa com o Gemini por meio de `lgpd_agent/gemini.py`.
7. O resultado estruturado preenche os campos em `lgpd_agent/mapping.py`. O roteiro em `lgpd_agent/interview_flow.py` escolhe a próxima pergunta e confere pendências.
8. `lgpd_agent/storage.py` salva o estado da entrevista em JSON e gera o relatório Markdown com `lgpd_agent/report.py`.
9. O navegador recebe a entrevista atualizada e redesenha os componentes da tela.

### Fluxo resumido

```text
Você escreve no chat
       ↓
static/js/actions.js (envia para a API)
       ↓
lgpd_agent/server.py (recebe a requisição)
       ↓
lgpd_agent/service.py (carrega a entrevista)
       ↓
lgpd_agent/agent.py → lgpd_agent/gemini.py (IA)
       ↓
lgpd_agent/mapping.py + lgpd_agent/interview_flow.py
       ↓
lgpd_agent/storage.py (salva a entrevista)
       ↓
static/js/views/interviews.js (atualiza o chat)
```

## 2. Explicação dos arquivos Python

| Arquivo | O que faz | Quando editar |
|---|---|---|
| `app.py` | Porta de entrada. Inicia o aplicativo. | Quase nunca; mantenha-o simples. |
| `lgpd_agent/config.py` | Lê `.env`, porta, pastas, nome do modelo e timeout. | Ao mudar configurações do servidor ou do Gemini. |
| `lgpd_agent/constants.py` | Define os **12 campos LGPD** usados na aplicação. | Quando os campos do mapeamento precisarem evoluir. |
| `lgpd_agent/prompts.py` | Instruções para o Gemini e formato JSON esperado. | Para melhorar a extração de respostas, sem mudar o controle do roteiro. |
| `lgpd_agent/gemini.py` | Executa requisições à API Gemini e trata erros temporários. | Para configurar chamadas, limites, retries e erros da IA. |
| `lgpd_agent/agent.py` | Monta o contexto, recebe a resposta estruturada da IA e registra informações. | Para melhorar a compreensão das respostas e validar extrações. |
| `lgpd_agent/interview_flow.py` | Escolhe **qual pergunta fazer**, controla perguntas adiadas e evita declarar conclusão antecipada. | Para corrigir repetição de perguntas ou regras de encerramento. |
| `lgpd_agent/mapping.py` | Cria processos, preenche campos, identifica lacunas e respeita edições manuais. | Para alterar regras de atualização do registro LGPD. |
| `lgpd_agent/service.py` | Cria entrevistas e executa ações: enviar, editar, renomear, excluir, reconstruir. | Ao acrescentar funcionalidades de negócio. |
| `lgpd_agent/storage.py` | Salva/carrega JSON e lista entrevistas, com escrita atômica. | Para modificar armazenamento ou exportação persistida. |
| `lgpd_agent/report.py` | Formata o relatório Markdown. | Para mudar a aparência/conteúdo do `.md`. |
| `lgpd_agent/server.py` | Disponibiliza páginas, CSS, JS e rotas HTTP. | Para adicionar endpoints ou alterar comportamento do servidor. |

**Importante:** as decisões de encerramento do mapeamento não dependem apenas da resposta textual do Gemini. Elas ficam no `interview_flow.py`, onde podem ser testadas de forma previsível.

## 3. Explicação dos arquivos do frontend

O frontend foi separado em três camadas para evitar milhares de linhas misturadas em um mesmo arquivo.

### HTML — estrutura da tela

- `static/index.html`: contém as áreas visuais do aplicativo, o menu, os elementos dos formulários e os ícones SVG. **Não deve conter a lógica do Gemini.**

### CSS — aparência

`static/styles.css` é apenas a **lista de importações**. O CSS real está dividido em:

| Arquivo CSS | Responsabilidade |
|---|---|
| `css/base.css` | **Paleta de cores**, tipografia, estilos globais e foco acessível. |
| `css/layout.css` | Menu lateral, cabeçalho, botões e estrutura da página. |
| `css/dashboard.css` | Cards, estatísticas, lista de recentes e indicador circular. |
| `css/interviews.css` | Histórico, balões do chat, editor e ações da entrevista. |
| `css/mapping.css` | Cards de processos, grupos de campos e indicadores de pendências. |
| `css/reports.css` | Tela de relatórios e configurações. |
| `css/feedback.css` | Avisos, mensagens de status, alertas e componentes compartilhados. |
| `css/responsive.css` | Ajustes para tablet e celular. |

**Para mudar a cor principal**, abra `static/css/base.css` e altere `--navy` (menu) ou `--blue` (ações). **Não altere as mesmas cores manualmente em dezenas de arquivos.**

### JavaScript — comportamento

`static/app.js` é apenas uma **entrada**. Ele importa `js/main.js`, que conecta os controles da página.

| Arquivo JavaScript | Responsabilidade |
|---|---|
| `js/core.js` | Guarda o estado da interface, faz chamadas HTTP e cria elementos comuns. |
| `js/main.js` | Faz a inicialização; vincula eventos aos botões e carrega os dados iniciais. |
| `js/actions.js` | Executa ações do usuário: criar entrevista, enviar mensagem, editar, renomear, exportar e usar microfone. |
| `js/views/index.js` | Reúne as funções que atualizam as telas. |
| `js/views/dashboard.js` | Desenha os indicadores e entrevistas recentes. |
| `js/views/interviews.js` | Desenha histórico, conversa e resumo do mapeamento durante a entrevista. |
| `js/views/mapping.js` | Desenha detalhes dos processos e campos para edição. |
| `js/views/reports.js` | Atualiza opções de relatório. |

**Regra para não desorganizar novamente:** quando uma mudança for somente visual, comece por `static/css/`. Quando mudar uma ação do usuário, veja `static/js/actions.js`. Quando mudar **o conteúdo de uma pergunta da IA**, veja `lgpd_agent/interview_flow.py` e `lgpd_agent/prompts.py`.

## 4. Exemplos práticos: onde editar?

| O que você quer mudar | Onde começar |
|---|---|
| Cor do menu lateral | `static/css/base.css` |
| Tamanho dos cards do dashboard | `static/css/dashboard.css` |
| Organização da conversa | `static/js/views/interviews.js` e `static/css/interviews.css` |
| Texto de botões e estrutura das páginas | `static/index.html` |
| Como a IA entende o que o usuário disse | `lgpd_agent/prompts.py` + `lgpd_agent/agent.py` |
| Fazer menos perguntas repetidas | `lgpd_agent/interview_flow.py` |
| Evitar encerramento com 11/12 campos | `lgpd_agent/interview_flow.py` + `tests/test_roteiro_entrevista.py` |
| Acrescentar um campo LGPD | `lgpd_agent/constants.py` + regras de entrevista + testes + agrupamento em `static/js/core.js` |
| Alterar o texto do relatório | `lgpd_agent/report.py` |
| Alterar o nome do modelo Gemini | `.env` (`GEMINI_MODELO`) |
| Adicionar um botão novo | `static/index.html` + `static/js/main.js` + `static/js/actions.js` |

## 5. Como são guardadas as entrevistas

Os arquivos ficam em `entrevistas/`:

- `<id>.json`: estado completo da entrevista, mensagens, processos e campos.
- `<id>.md`: relatório legível, atualizado ao salvar.

A cada mudança, o sistema salva uma nova versão dos dados locais. **Não edite arquivos JSON enquanto a aplicação estiver em execução**; faça primeiro uma cópia de segurança. O ZIP distribuído não inclui suas entrevistas particulares nem o `.env`.

## 6. Como o controle de conclusão funciona

Existem **12 campos por processo**. O sistema pergunta sobre dados operacionais ausentes e considera a base legal uma pendência especial, que pode exigir revisão jurídica. Por isso:

- **11/12 campos não significa conclusão.** O último campo é explicitado ao usuário.
- Se faltarem respostas operacionais, o roteiro procura outras lacunas e não repete indiscriminadamente a mesma pergunta.
- Se faltar apenas base legal, o sistema indica que o levantamento operacional está completo, **mas o registro ainda exige avaliação jurídica**.
- O usuário pode editar os campos manualmente; o agente não sobrescreve esses valores.

Arquivos principais dessa regra: `interview_flow.py`, `mapping.py`, `agent.py` e `tests/test_roteiro_entrevista.py`.

## 7. Rodar e testar no VS Code

No terminal aberto **na pasta onde está `app.py`**:

```bash
python app.py
```

Abra o endereço indicado (geralmente `http://localhost:8000`). Para interromper, pressione `Ctrl+C`.

Para rodar os testes:

```bash
python -m unittest discover -s tests -v
```

Para verificar a sintaxe dos módulos JavaScript **caso tenha Node.js instalado**:

```bash
node --check static/app.js
node --check static/js/main.js
```

> Os testes automatizados simulam a API Gemini: não garantem que uma chave real esteja ativa ou que o serviço externo esteja disponível. O aplicativo é local e não deve ser colocado na internet sem medidas adicionais de segurança.

## 8. Cuidados para continuar evoluindo

1. Faça **backup** de `entrevistas/` antes de atualizar o projeto.
2. Nunca coloque a chave de API no código-fonte. Use `.env` na raiz e mantenha-o privado.
3. Mude um módulo de cada vez e rode os testes após a mudança.
4. Se criar um novo módulo JS ou CSS, importe-o a partir dos arquivos de entrada.
5. Mantenha a validação de dados e a lógica LGPD no Python. O JavaScript é uma interface, não a autoridade que determina se o processo está completo.
6. As sugestões da IA sobre bases legais exigem revisão jurídica, especialmente em contextos com dados sensíveis.


## Atualização v3 — início e encerramento da entrevista

- `lgpd_agent/interview_flow.py` — controla a pergunta pendente, evita repetição, reconhece pedido de encerramento e calcula separadamente pendências operacionais e jurídicas.
- `lgpd_agent/legal_suggestions.py` — identifica propostas de base legal escritas explicitamente pelo entrevistado para processos já cadastrados; mantém o status `validacao_juridica: pendente`. Não produz parecer nem cria hipótese jurídica.
- `lgpd_agent/service.py` — oferece `encerrar`, `reabrir`, `recuperar_bases` e `validar_base`. O encerramento e a recuperação das bases **não fazem chamada à IA**.
- `static/js/views/interviews.js` — exibe Em andamento / Encerrada e controla a visibilidade do campo de envio.
- `static/js/views/mapping.js` — exibe o status da sugestão de base legal e a ação para registrar validação jurídica humana.
- `static/js/views/dashboard.js` — contabiliza revisões jurídicas separadamente dos campos documentados.

### Preenchimento versus validação

Um campo de base legal escrito mas não aprovado conta como **documentado** no total 12/12. Isso **não** significa que a escolha é correta ou foi validada. O painel mantém o aviso de revisão jurídica até o responsável registrar explicitamente a confirmação.

### Atualizar um histórico antigo

Abra a entrevista, entre em **Mapeamento** e clique em **Recuperar bases sugeridas**. Isso relê apenas as mensagens do entrevistado que tenham propostas vinculadas a processos existentes; não consulta o Gemini.

### Onde ficam os testes novos?

`tests/test_encerramento_revisao.py` cobre os pedidos de encerramento, ausência de chamadas à IA nessa operação, reabertura, recuperação de propostas anteriores, proteção contra aprovação automática e preservação do status.
