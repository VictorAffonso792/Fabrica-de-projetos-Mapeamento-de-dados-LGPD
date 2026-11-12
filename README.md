# Privacidade 360 — Agente Inteligente de Mapeamento LGPD

> **O que mudou nesta versão:** veja [`CORRECOES_E_MELHORIAS.md`](CORRECOES_E_MELHORIAS.md).

Plataforma **local** de entrevistas assistidas por Gemini para organizar processos e registros das operações de tratamento de dados pessoais. Código em Python (biblioteca padrão), HTML, CSS e JavaScript; não necessita instalar dependências Python.

> Interface autoral inspirada no estilo corporativo e nas cores publicadas pela DPOnet. **Não é um produto oficial da DPOnet nem utiliza logotipos proprietários.**

## Executar no VS Code

1. Extraia este ZIP e abra a pasta extraída no VS Code (`Arquivo → Abrir Pasta`).
2. Instale **Python 3.10+** se ainda não estiver instalado.
3. Copie `.env.example` para um novo arquivo chamado `.env` **na pasta principal**, ao lado de `app.py` (não dentro de `tests/`).
4. Gere uma chave em <https://aistudio.google.com/apikey>. Edite o `.env`:

   ```ini
   GEMINI_API_KEY=SUA_CHAVE_AQUI
   GEMINI_MODELO=gemini-3.5-flash-lite
   GEMINI_FALLBACK=gemini-3.5-flash
   GEMINI_TIMEOUT=45
   PORTA=8000
   ```

5. No terminal do VS Code, execute:

   ```bash
   python app.py
   ```

6. Acesse o endereço exibido no terminal, normalmente <http://localhost:8000>. Use **Nova entrevista** para iniciar.

Para parar, `Ctrl+C`. Se a porta 8000 estiver ocupada, o programa tenta a próxima porta disponível.

**Segurança:** uma chave exposta anteriormente deve ser revogada no Google AI Studio e substituída. Não compartilhe `.env` nem o envie ao GitHub. O arquivo está no `.gitignore` e não é incluído no ZIP. A API Gemini recebe as mensagens enviadas pelo agente; avalie suas políticas de privacidade e de tratamento de dados antes de usar informações reais de clientes.

## Telas

- **Visão geral:** cinco indicadores reais, incluindo revisão jurídica separada do preenchimento, entrevistas recentes e evolução do registro.
- **Entrevistas:** histórico pesquisável, chat com Gemini e painel de mapeamento ao vivo. Entrada por voz em navegadores compatíveis.
- **Mapeamento:** campos organizados em seis grupos expansíveis, status, edição manual, renomeação/exclusão de processos e reconstrução após edições de mensagens.
- **Relatórios:** exportação em Markdown dos processos, pendências e transcrição.
- **Configurações:** orientações do ambiente e da chave Gemini; nenhuma credencial é exposta ao navegador.

## O que mudou na performance

| Antes | Agora |
|---|---|
| Até cinco etapas consecutivas de geração para ferramentas | **Uma geração estruturada por mensagem** no fluxo normal (e uma por reconstrução completa) |
| Nova entrevista fazia chamada de IA | **Abertura local imediata**, com pergunta inicial fixa |
| Transcrição inteira enviada a cada turno | **Resumo do estado estruturado + últimas 10 mensagens**; a transcrição integral continua no disco |
| Um bloqueio global no servidor | Travas por ID de entrevista; operações independentes podem prosseguir |
| Gravação direta de JSON | Substituição atômica dos arquivos para diminuir risco de arquivos parciais |
| Frontend bloqueava todos os botões durante requisições | Indicador de processamento e navegação mantida disponível |

**Observações:** uma geração pode provocar novas tentativas em erros temporários; o tempo total depende da rede, modelo, tamanho do contexto e limites da conta Google. O log informa duração e número de chamadas efetivas na API. Não foi executado benchmark com uma chave real neste ambiente; não há percentuais de aceleração alegados.

## Estrutura de arquivos (organizada por responsabilidade)

O projeto está dividido em arquivos menores, com nomes descritivos e comentários. A aplicação permanece em **Python + HTML + CSS + JavaScript**, sem dependências Python adicionais.

```text
privacidade360-v3-revisado/
├── app.py                     # Executa a aplicação
├── .env.example               # Configuração de exemplo (sem chave real)
├── .vscode/                   # Execução e extensões recomendadas
├── lgpd_agent/                # Regras e servidor Python
│   ├── config.py              # Configurações
│   ├── constants.py           # Campos do mapeamento LGPD
│   ├── prompts.py             # Instruções e schemas do Gemini
│   ├── gemini.py              # Comunicação com a API
│   ├── agent.py               # Extração estruturada das respostas
│   ├── interview_flow.py      # Roteiro, lacunas, encerramento e reabertura
│   ├── legal_suggestions.py  # Propostas jurídicas explícitas e revisão pendente
│   ├── mapping.py             # Registro das informações e processos
│   ├── service.py             # Ações da entrevista
│   ├── storage.py             # Persistência JSON e Markdown
│   ├── report.py              # Formatação do relatório
│   └── server.py              # Rotas e servidor local
├── static/
│   ├── index.html             # Elementos das páginas
│   ├── styles.css             # Importa os estilos abaixo
│   ├── app.js                 # Importa o código JavaScript abaixo
│   ├── css/
│   │   ├── base.css           # Cores, fontes, variáveis
│   │   ├── layout.css         # Estrutura e menu
│   │   ├── dashboard.css      # Painel inicial
│   │   ├── interviews.css     # Chat e histórico
│   │   ├── mapping.css        # Mapeamento de processos
│   │   ├── reports.css        # Relatórios e configurações
│   │   ├── feedback.css       # Avisos e mensagens
│   │   └── responsive.css     # Tablets e celulares
│   └── js/
│       ├── core.js            # Dados e utilitários compartilhados
│       ├── main.js            # Eventos e inicialização
│       ├── actions.js         # Envio, edição e exclusão
│       └── views/
│           ├── index.js       # Atualiza as telas
│           ├── dashboard.js   # Indicadores
│           ├── interviews.js  # Histórico, chat e resumo
│           ├── mapping.js     # Campos de cada processo
│           └── reports.js     # Exportação de relatórios
├── entrevistas/               # Dados locais (pasta vazia no ZIP)
├── tests/                     # Testes automatizados
└── docs/
    └── GUIA_DO_CODIGO.md      # Explica cada arquivo, as regras e onde editar
```

**Para entender tudo sem ter que ler código extenso**, abra primeiro [`docs/GUIA_DO_CODIGO.md`](docs/GUIA_DO_CODIGO.md). Ele contém um mapa do funcionamento, exemplos de alterações e explicações detalhadas sobre cada pasta e módulo.

## Dados de versões anteriores

Os arquivos `entrevistas/*.json` e `entrevistas/*.md` da versão antiga são compatíveis. Para migrá-los, **feche o aplicativo e faça backup**, então copie os arquivos da pasta antiga `entrevistas/` para a nova. Não substitua arquivos mais recentes sem verificar. Este ZIP inclui apenas a pasta vazia porque o arquivo enviado não continha seu histórico do computador.

## Testes

```bash
python -m unittest discover -s tests -v
```

Os testes simulam o Gemini, não precisam de chave e cobrem persistência, rotas, extração estruturada, preservação de edições manuais, erros e concorrência. Sintaxe do JavaScript também pode ser conferida com `node --check static/app.js` e os módulos em `static/js/`, caso o Node esteja instalado.

## Limitações atuais

- Servidor vinculado a `127.0.0.1`: **não publique na internet** sem autenticação, HTTPS, controles de acesso, criptografia e auditoria adequada.
- Histórico armazenado localmente, **sem criptografia**. Proteja o dispositivo e as cópias de segurança.
- Sugestão de base legal deve sempre ser revisada por um profissional de privacidade.
- Transcrições extensas são reconstruídas com a IA e podem aumentar o custo e o tempo de processamento.
- A interface é responsiva; reconhecimento por voz depende do navegador. Não há streaming de tokens: a resposta estruturada completa chega ao final de uma chamada.

## Referências

- [DPOnet — Plataforma](https://dponet.com.br/plataforma-dponet/)
- [Manual público de marca DPOnet](https://dponet.com.br/wp-content/uploads/2024/12/GuiadeAplicacao-MarcaDPOnet.pdf)
- [Modelos Gemini](https://ai.google.dev/gemini-api/docs/models)

## Atualização — roteiro de entrevista e eliminação de perguntas repetidas

Nesta versão, o **Python controla a próxima pergunta**, em vez de confiar no texto livre gerado pelo Gemini. O Gemini continua extraindo informações da última resposta, mas não decide unilateralmente quando a entrevista ou o mapeamento terminou.

- Perguntas são baseadas em **campos efetivamente ausentes**, para o processo correto. Uma resposta curta como "não" ou "WhatsApp" é contextualizada pela pergunta em aberto.
- Se o entrevistado não souber responder, a pergunta é **adiada** e não se repete indefinidamente. A pendência continua visível e pode ser preenchida no painel.
- Quando todos os campos operacionais estiverem preenchidos, o sistema pergunta uma única vez sobre outras atividades e **informa separadamente as pendências jurídicas**.
- A **base legal** exige avaliação fundamentada. O Gemini não pode inventar bases para processos sensíveis. Propostas explícitas do usuário podem ser **registradas como sugestões** sem ser aprovadas; há um status independente de revisão jurídica.
- O painel separa **campos documentados**, **pendências operacionais**, **sugestões jurídicas** e **aprovação jurídica**. Encerrar a entrevista não implica 100% de validação.
- A edição manual continua protegida contra sobrescrita pela IA; entrevistas antigas abrem normalmente mesmo sem o campo `controle_entrevista`.

**O caso 11/12:** se o único campo ausente for a **Base legal**, o sistema não inventa uma hipótese. O entrevistado pode registrar uma sugestão explícita e identificável, que aparecerá como **12/12 documentados**, mas com **revisão jurídica pendente**. Só o botão de validação jurídica, após conferência humana, altera a revisão para validada. Isso separa documento preenchido de documento juridicamente aprovado.

### Atualizar sem perder entrevistas

1. Feche o servidor anterior (`Ctrl+C`).
2. Faça cópia de segurança da sua pasta antiga `entrevistas/` e do `.env` (não compartilhe a chave).
3. Extraia esta nova versão em outra pasta e abra-a no VS Code.
4. Copie **seus próprios** arquivos `.json` e `.md` antigos para a pasta `entrevistas/` da versão nova. Não substitua arquivos homônimos sem conferência.
5. Crie o `.env` na pasta principal e configure uma chave válida do Gemini. Execute `python app.py`.
6. Abra sua entrevista anterior: o roteiro corrigido entra em ação a partir da **próxima mensagem**, sem necessidade de reiniciar o histórico.

Testes específicos de regressão estão em `tests/test_roteiro_entrevista.py`. Todos são executados sem chave real com:

```bash
python -m unittest discover -s tests -v
```

> Limitação: o comportamento de modelos reais pode variar. A lógica do servidor impede perguntas sobre campos preenchidos e declarações indevidas de conclusão, mas a extração semântica do Gemini deve ser conferida pelo usuário. Este projeto continua sendo um aplicativo local de demonstração e não substitui consultoria jurídica nem controles de segurança adequados para dados pessoais reais.

## Revisão de usabilidade e encerramento — versão 3

- **Um único botão principal para criar entrevista** no topo. As outras ações da página inicial apenas levam ao histórico, sem abrir um registro duplicado.
- **Encerrar entrevista**: salva a conversa imediatamente, mesmo com pendências; não chama o Gemini e não faz novas perguntas. O campo de resposta fica oculto, e o histórico recebe a situação **Encerrada**.
- **Reabrir entrevista**: restaura o campo de mensagem, e o roteiro pode continuar.
- **Bases legais sugeridas**: quando o entrevistado escrever propostas com o nome do processo e fundamento identificável, elas são salvas como **sugestão pendente de revisão jurídica**. O indicador conta o campo como documentado, não validado.
- **Recuperar bases sugeridas**: na tela Mapeamento, recupera propostas explícitas de entrevistas antigas sem chamar a IA. Útil para históricos em que o agente ignorou uma tabela de bases legais.
- **Registrar validação jurídica**: fica dentro do campo de base legal, requer confirmação e só deve ser acionado após revisão humana.
- **Dashboard**: inclui indicador independente de **Revisões jurídicas**.

Os demais recursos da plataforma continuam disponíveis. O sistema é local e não traz uma análise jurídica automatizada certificada.
