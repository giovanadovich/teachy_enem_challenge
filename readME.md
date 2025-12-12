# Teachy ENEM RAG

Este projeto implementa uma API de Busca por Similaridade Semântica para questões do ENEM utilizando a arquitetura RAG (Retrieval-Augmented Generation).
A API combina embeddings semânticos gerados pelo Google Gemini, busca vetorial com Qdrant e persistência relacional com SQLite.

---

## Tecnologias Utilizadas

| Componente       | Tecnologia          | Função                         |
| ---------------- | ------------------- | ------------------------------ |
| API              | FastAPI             | Endpoints REST                 |
| Embeddings       | Google Gemini Flash | Vetorização semântica          |
| Banco Vetorial   | Qdrant (In-Memory)  | Busca por similaridade         |
| Banco Relacional | SQLite + SQLAlchemy | Armazenamento persistente      |
| Coleta de Dados  | requests            | Obtenção das questões iniciais |

---

## Arquitetura do Projeto

### 1. `collect_data.py`

* Coleta questões via API pública
* Limpa e organiza o dataset
* Salva em `data/initial_enem_data.json`

### 2. `db/sql_db.py`

* Configura o banco SQLite
* Gerencia sessões e engine

### 3. `core/question_service.py`

* Inicializa SQLite e Qdrant
* Gera embeddings com Gemini
* Indexa questões no Qdrant
* Implementa Context Stacking e Filtragem Estrutural

### 4. `api/main.py`

* Implementa os endpoints de busca e inserção

---

# Setup do Ambiente

## 1. Criar ambiente virtual

```bash
python -m venv new_env
```

## 2. Ativar o ambiente

Linux/macOS:

```bash
source new_env/bin/activate
```

Windows CMD:

```cmd
new_env\Scripts\activate
```

Windows PowerShell:

```powershell
new_env\Scripts\Activate.ps1
```

---

# Instalar Dependências

Antes de rodar qualquer parte do projeto, instale todas as dependências:

```bash
pip install -r requirements.txt
```

---

# Configurar a API Key do Google Gemini

PowerShell:

```powershell
$env:GEMINI_API_KEY = "SUA_CHAVE_AQUI"
```

Windows CMD:

```cmd
set GEMINI_API_KEY=SUA_CHAVE_AQUI
```

Linux/macOS:

```bash
export GEMINI_API_KEY="SUA_CHAVE_AQUI"
```

---

# Coletar os Dados Iniciais

```bash
python collect_data.py
```

---

# Inicializar Banco de Dados e Qdrant

Ao iniciar a API pela primeira vez:

* Tabelas SQLite são criadas automaticamente
* A coleção do Qdrant é criada
* O JSON com as questões é carregado
* Embeddings são gerados
* As questões são indexadas

Nenhuma etapa manual é necessária além das execuções anteriores.

---

# Rodar a API

```bash
uvicorn api.main:app --reload
```

API disponível em:

[http://127.0.0.1:8000]

Documentação (Swagger):

[http://127.0.0.1:8000/docs]

---

# Endpoints da API

## GET `/status/count`

Retorna o número total de questões indexadas.

Exemplo de resposta:

```json
{
  "count": 842
}
```

---

## GET `/questions?topic={texto}&amount={n}`

Executa uma busca semântica utilizando embeddings e filtragem estrutural.

Exemplo:

```
/questions?topic=leis de ohm&amount=5
```

Exemplo de resposta:

```json
[
  {
    "id": 15,
    "question": "Um circuito elétrico apresenta ...",
    "alternatives": ["A", "B", "C", "D"],
    "correct_answer": "C",
    "score": 0.89
  }
]
```

---

## POST `/questions`

Insere uma nova questão, gera embedding e indexa no Qdrant.

JSON esperado:

```json
{
  "question": "Qual é a unidade de resistência elétrica?",
  "alternatives": ["Volt", "Ohm", "Watt", "Ampere"],
  "correct_answer": "Ohm",
  "subject": "fisica"
}
```

Resposta:

```json
{
  "status": "success",
  "id": 440
}
```

---

# Exemplo Completo de Busca

Requisição:

```
GET /questions?topic=cinematica&amount=3
```

Resposta:

```json
[
  {
    "id": 55,
    "question": "Um corpo em MRU ...",
    "alternatives": ["A", "B", "C", "D"],
    "correct_answer": "B",
    "score": 0.92
  }
]
```

---

# Observações Importantes

* A primeira execução pode levar alguns segundos devido à geração dos embeddings iniciais.
* O Qdrant está configurado em modo in-memory, ideal para desenvolvimento.
* Qualquer nova questão inserida é automaticamente vetorizada e indexada.