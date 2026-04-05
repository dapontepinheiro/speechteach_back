# SpeechTeach — Backend

Backend da aplicação SpeechTeach, plataforma de prática de pronúncia em inglês 
com avaliação em tempo real por IA, utilizando frases de séries famosas como 
conteúdo de estudo.

> Frontend disponível em [speechteach_front](link do repo)

## Funcionalidades

| Módulo | Descrição |
|---|---|
| Avaliação de pronúncia | análise de áudio via Microsoft Azure Speech SDK com feedback de precisão, ritmo, clareza e emoção |
| Text-to-Speech | reprodução do modelo de pronúncia correto para cada frase |
| Frases por nível | banco de frases separadas por dificuldade (Iniciante, Intermediário, Avançado) e por série |
| Cadastro e autenticação | criação e gerenciamento de contas de usuário |
| Estatísticas | streak, precisão média, estrelas conquistadas e frases finalizadas |

## Estrutura
├── main.py           # entrada da aplicação e rotas principais
├── cadastro.py       # autenticação e gerenciamento de usuários
├── frases.py         # banco de frases e lógica de níveis/séries
├── ms_speech.py      # integração com Microsoft Azure Speech SDK
├── voice_chat.py     # processamento do áudio enviado pelo usuário
├── stats.py          # cálculo de streak, estrelas e estatísticas
└── requirements.txt
## Tecnologias

| Ferramenta | Uso |
|---|---|
| Python | linguagem principal do backend |
| Microsoft Azure Speech SDK | avaliação de pronúncia e text-to-speech |
| FastAPI | servidor e rotas da API |

## Como Executar

1. Instale as dependências
```bash
pip install -r requirements.txt
```

2. Crie um arquivo `.env` na raiz do projeto
AZURE_SPEECH_KEY=sua_chave_aqui
AZURE_REGION=sua_regiao_aqui

4. Execute a aplicação
```bash
uvicorn main:app --port 8000
```

## Prévia

![Home](assets/home-preview.png)
![Dashboard](assets/dashboard-preview.png)
![Treino](assets/treino-preview.png)
