-- Estrutura esperada pelo projeto.
-- A tabela "paciente" já pode existir no seu banco; ajuste apenas se necessário.

CREATE TABLE IF NOT EXISTS paciente (
    id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    nome VARCHAR(100) NOT NULL,
    idade INTEGER
);

CREATE TABLE IF NOT EXISTS medicoes (
    id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    paciente_id INTEGER NOT NULL REFERENCES paciente(id) ON DELETE CASCADE,
    data DATE NOT NULL,
    glicemia NUMERIC(6,2),
    hba1c NUMERIC(4,2),
    peso NUMERIC(5,2)
);

CREATE TABLE IF NOT EXISTS medicamentos (
    id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    paciente_id INTEGER NOT NULL REFERENCES paciente(id) ON DELETE CASCADE,
    nome VARCHAR(100) NOT NULL,
    dose VARCHAR(50),
    data_inicio DATE,
    data_fim DATE
);

CREATE TABLE IF NOT EXISTS documentos (
    id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    paciente_id INTEGER NOT NULL REFERENCES paciente(id) ON DELETE CASCADE,
    nome_arquivo VARCHAR(255) NOT NULL,
    tipo_arquivo VARCHAR(100),
    caminho_arquivo TEXT NOT NULL,
    texto_extraido TEXT,
    data_upload TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
