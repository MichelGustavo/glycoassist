# GlycoAssist

Protótipo acadêmico de assistente com LLM para consulta de dados de pacientes com diabetes. O sistema integra:

- **PostgreSQL** para pacientes, medições, medicamentos e metadados/texto de documentos;
- **upload de PDF**, salvo em disco e vinculado ao paciente no banco;
- **LLM via Groq**, que recebe o histórico do paciente recuperado do PostgreSQL e o texto dos PDFs;
- interface web em Flask para selecionar um paciente e conversar sobre os dados registrados.

> O projeto é educacional. Ele não faz diagnóstico e não deve prescrever, suspender ou alterar tratamento.

## Estrutura

```text
tribunal-ia/
├── app.py                 # servidor Flask e APIs
├── assistente.py          # prompt, LLM e extração de PDF
├── database.py            # acesso parametrizado ao PostgreSQL
├── config.py              # limites e configurações gerais
├── main.py                # versão opcional de terminal
├── schema.sql             # estrutura esperada das tabelas
├── templates/index.html   # interface web
├── static/style.css
├── static/script.js
├── uploads/               # PDFs salvos por paciente
├── requirements.txt
└── .env.example
```

## Banco de dados esperado

O código usa estas tabelas:

- `paciente(id, nome, idade)`
- `medicoes(id, paciente_id, data, glicemia, hba1c, peso)`
- `medicamentos(id, paciente_id, nome, dose, data_inicio, data_fim)`
- `documentos(id, paciente_id, nome_arquivo, tipo_arquivo, caminho_arquivo, texto_extraido, data_upload)`

O arquivo `schema.sql` contém os comandos de criação. Como você já possui a tabela `paciente`, não precisa recriá-la se a estrutura for compatível.

## Configuração

1. Crie/ative um ambiente virtual.
2. Instale as dependências:

```bash
pip install -r requirements.txt
```

3. Copie `.env.example` para `.env`:

```bash
cp .env.example .env
```

4. Preencha a chave da Groq e os dados do PostgreSQL:

```env
GROQ_API_KEY=sua_chave
LOGIN_EMAIL=seu_email
LOGIN_PASSWORD=sua_senha_de_acesso
FLASK_SECRET_KEY=uma_chave_longa_e_aleatoria
DB_HOST=localhost
DB_PORT=5432
DB_NAME=seu_banco
DB_USER=postgres
DB_PASSWORD=sua_senha
```

Também é possível usar `DATABASE_URL`; se ela estiver definida, terá prioridade.

## Executar

```bash
python app.py
```

Abra `http://127.0.0.1:5000`.

Se as variáveis de login não forem definidas, o protótipo usa
`admin@glycoassist.local` / `admin`. Defina credenciais próprias no `.env` antes
de disponibilizar a aplicação para outras pessoas.

## Como o banco entra na LLM

A LLM **não recebe permissão para executar SQL arbitrário**. A aplicação faz consultas parametrizadas em `database.py`, reúne os dados do paciente e os envia como contexto para o modelo. Isso evita que uma resposta da LLM seja transformada diretamente em SQL destrutivo.

A cada nova pergunta, o servidor relê do PostgreSQL:

1. cadastro do paciente;
2. medições recentes;
3. medicamentos;
4. documentos enviados e o texto extraído dos PDFs.

Assim, uma pergunta como “Como minha HbA1c evoluiu?” usa os valores da tabela `medicoes`; uma pergunta como “O que aparece no meu último exame?” também usa o texto armazenado em `documentos`.

## Upload de PDF

Quando um PDF é enviado:

1. o arquivo físico vai para `uploads/<paciente_id>/`;
2. `pypdf` extrai o texto;
3. o PostgreSQL recebe `nome_arquivo`, `tipo_arquivo`, `caminho_arquivo`, `texto_extraido`, `paciente_id` e `data_upload`;
4. nas próximas perguntas, esse texto passa a fazer parte do contexto da LLM.

PDFs escaneados como imagem, sem camada de texto, precisam passar por OCR antes do envio.
