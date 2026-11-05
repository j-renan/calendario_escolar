-- Esquema do banco de dados do Calendario Escolar.
-- Banco: PostgreSQL
-- O script pode ser executado mais de uma vez sem recriar tabelas existentes.

CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    name VARCHAR(120) NOT NULL,
    email VARCHAR(180) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(50) DEFAULT 'coordenador',
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS course_categories (
    id SERIAL PRIMARY KEY,
    code VARCHAR(140) UNIQUE NOT NULL,
    name VARCHAR(120) NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS app_settings (
    key VARCHAR(120) PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_course_categories_name
    ON course_categories (LOWER(name));

CREATE TABLE IF NOT EXISTS calendars (
    id SERIAL PRIMARY KEY,
    title VARCHAR(200) NOT NULL DEFAULT 'CALENDÁRIO ESCOLAR',
    unit_code VARCHAR(50) NOT NULL DEFAULT 'CFP 5.10',
    semester_year VARCHAR(50) NOT NULL DEFAULT '2º / 2026',
    status VARCHAR(30) NOT NULL DEFAULT 'rascunho',
    version VARCHAR(50) NOT NULL DEFAULT 'Versão 01 - 06/10/2026',
    director_name VARCHAR(150) NOT NULL DEFAULT 'Tiago Roberto Ferreira',
    director_signature_status VARCHAR(50) DEFAULT 'Pendente',
    signature_date TIMESTAMP NULL,
    workload_note TEXT DEFAULT '* Ampliação da Jornada de trabalho',
    data_json JSONB NOT NULL,
    created_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_calendars_semester_year
    ON calendars (semester_year);

CREATE TABLE IF NOT EXISTS calendar_history (
    id SERIAL PRIMARY KEY,
    calendar_id INTEGER REFERENCES calendars(id) ON DELETE CASCADE,
    action VARCHAR(100) NOT NULL,
    snapshot_json JSONB NOT NULL,
    user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
