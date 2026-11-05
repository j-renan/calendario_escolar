# Antigravity - Gestão de Calendário Escolar SENAI-SP

Aplicação web completa desenvolvida com **Flask**, **PostgreSQL** e arquitetura **MVP (Model-View-Presenter)** aplicando os princípios **SOLID** e **Programação Orientada a Objetos (POO)**.

---

## 🏛️ Arquitetura MVP & SOLID

A aplicação foi estruturada seguindo rigorosamente a separação de responsabilidades em camadas:

```
calendario_escolar/
├── app.py                      # Application Factory e inicialização
├── config.py                   # Configurações de ambiente (12-Factor App)
├── core/                       # Serviços transversais do sistema
│   ├── database.py             # Gerenciamento de conexões PostgreSQL (Pool)
│   ├── security.py             # JWT Token Provider e Hashing de senhas
│   └── exceptions.py           # Exceções customizadas da aplicação
├── models/                     # Camada de Domínio e Modelos (M de MVP)
│   ├── user.py                 # Entidade de Usuário
│   ├── calendar.py             # Entidades de Calendário, Meses, Dias e Regras de Negócio
│   └── repositories/           # Inversão de Dependência (DIP) e Interfaces (ISP)
│       ├── base.py             # Contratos/Interfaces abstratas (IUserRepository, ICalendarRepository)
│       ├── user_repository.py  # Implementação concreta PostgreSQL
│       ├── calendar_repository.py # Persistência de Calendário e Snapshots JSONB
│       └── category_repository.py # Persistência PostgreSQL das categorias
├── presenters/                 # Camada de Apresentação (P de MVP)
│   ├── auth_presenter.py       # Orquestração de autenticação e validações
│   ├── category_presenter.py   # Regras de cadastro e validação de categorias
│   └── calendar_presenter.py   # Cálculos de dias letivos, fluxo de aprovação, exportação PDF
├── views/                      # Camada de Visualização (V de MVP)
│   ├── auth_view.py            # Endpoints REST para autenticação (/api/auth)
│   ├── category_view.py        # Endpoints autenticados para categorias (/api/categories)
│   ├── user_view.py            # Administração de usuários (/api/users)
│   ├── calendar_view.py        # Endpoints REST para manipulação do calendário (/api/calendars)
│   └── export_view.py          # Endpoints de exportação PDF e JSON (/api/export)
├── static/                     # Recursos visuais e frontend
│   ├── css/
│   │   ├── style.css           # Estilo visual moderno e responsivo SaaS
│   │   └── print.css           # Estilos para impressão em folha A4 paisagem
│   ├── js/
│   │   ├── api.js              # Cliente de API e gerenciador de Token JWT
│   │   └── app.js              # Controlador interativo de interface, modais e eventos
│   └── img/
│       └── logo_senai.png      # Logo oficial SENAI São Paulo
├── templates/
│   └── index.html              # Interface do usuário (SPA)
└── test_suite.py               # Suíte completa de testes automatizados
```

### Princípios SOLID Aplicados:
- **S (Single Responsibility Principle):** Cada classe possui uma única responsabilidade (ex: `TokenProvider` cuida apenas de tokens; `CalendarPresenter` cuida apenas da lógica de negócio e estados do calendário; `PostgresCalendarRepository` cuida apenas da persistência em banco).
- **O (Open/Closed Principle):** As classes são abertas para extensão e fechadas para modificação via interfaces e extensões de repositórios.
- **L (Liskov Substitution Principle):** Qualquer implementação de repositório (`IUserRepository`, `ICalendarRepository`) pode ser substituída sem afetar os presenters.
- **I (Interface Segregation Principle):** Interfaces de repositório focadas e enxutas em `models/repositories/base.py`.
- **D (Dependency Inversion Principle):** Os Presenters dependem de abstrações/interfaces de repositório, não de instâncias concretas do banco.

---

## 🎨 Interface e Layout (UI)

- **Barra Lateral Esquerda:** Escura e elegante (`#0F172A`), com logo e marca **"Antigravity"**, navegação e perfil de usuário com logout.
- **Acesso:** Tela de login com sessão JWT. O login automático por credenciais padrão foi removido.
- **Perfis de acesso:** Diretor tem acesso total e pode assinar calendários; Coordenador e OPP têm acesso total, exceto assinatura; Colaborador pode visualizar calendários.
- **Gestão de usuários:** Página própria para cadastrar, listar, editar e excluir usuários. Não é permitido excluir a própria conta ou a última conta ativa de Diretor.
- **Gestão de categorias:** Página própria para cadastrar, listar, editar e excluir categorias. Calendários existentes preservam as categorias já registradas.
- **Calendários:** Seleção e criação por ano e semestre. A geração base marca dias de segunda a sexta como letivos e fins de semana como não letivos; feriados, recessos e eventos devem ser revistos manualmente.
- **Marcos de curso:** Ao classificar um dia como início/término das aulas, escolha o marco e as categorias afetadas. As datas selecionadas atualizam os cards e a lista de eventos daquele mês é sincronizada com as alterações do dia.
- **Exclusão de calendário:** Diretor, Coordenador e OPP podem excluir o calendário selecionado após confirmação; o histórico relacionado é removido junto.
- **Painel Central de Trabalho:**
  - **Cabeçalho:** Logo clássico do **SENAI SÃO PAULO** no canto superior esquerdo, título centralizado **"CALENDÁRIO ESCOLAR"**, e caixas informativas para **"CFP 5.10"** e **"SEM/ANO: 2º / 2026"** no canto superior direito.
  - **Barra de Ferramentas de Edição:**
    - **Salvar como Rascunho**: Salva o estado atual no PostgreSQL.
    - **Publicar**: Publica a versão oficial com atualização de versão.
    - **Exportar**: Menu dropdown com opções de download em **PDF** (gerado com ReportLab), **Imprimir A4**, e **Exportar JSON**.
    - **Filtros**: Filtragem dinâmica por cursos.
    - **Desfazer / Histórico**: Janela modal com histórico de snapshots e restauração com 1 clique (Undo/Redo).
  - **1. Cards de Resumo (Topo):** um bloco por categoria de curso:
    - *Aprendizagem Industrial*
    - *Curso Técnico*
    - *Formação Continuada*
    - *Graduação / Especialização*
    (Com contagem mensal dos seis meses do semestre e total de dias letivos).
  - **2. Grade de Meses (Corpo Principal):** Os seis meses selecionados são exibidos em duas colunas:
    - **Coluna da Esquerda:** os três primeiros meses do semestre.
    - **Coluna da Direita:** os três últimos meses do semestre.
    - Cada mês contém:
      - Grade de domingo a sábado (D, 2ª, 3ª, 4ª, 5ª, 6ª, S) com cores semânticas:
        - 🔴 **Vermelho:** Feriados
        - 🟢 **Verde:** Início e término das aulas
        - 🟡 **Amarelo:** Dias não letivos / Férias / Recesso / Planejamento
        - 🔵 **Azul:** Dias de compensação / Sábado Letivo
        - ⚪ **Branco:** Dias letivos normais
      - **Edição Interativa:** Clique em qualquer dia para abrir o modal de alteração de status/descrição; o sistema recalcula os dias letivos do mês e do card de resumo instantaneamente!
      - Coluna lateral **"EVENTOS"** com textos coloridos em azul, vermelho e verde.
      - Notas de rodapé mensais (ex: *"Felicidade na escola"*, *"Agosto lilás..."*, *"Setembro amarelo..."*, etc.).
      - Linhas inferiores com contagem de **"Dias Letivos para cada categoria de curso"**.
  - **3. Rodapé e Seções de Apoio (Base):**
    - **Canto inferior esquerdo:** Tabela *"Dias a compensar / Dias de compensação"* (10/jul, 18/jul, 07/dez, 26/set) e carimbo de versão (*"Versão 01 - 06/10/2026"*).
    - **Centro / Direita:** Quadro de **"APROVAÇÃO"** da Direção para o Diretor **Tiago Roberto Ferreira**, nota de rodapé `* Ampliação da Jornada de trabalho`, e botão interativo para **Assinatura Digital** com código hash criptográfico SHA-256 e data/hora.

---

## 🔒 Segurança & Autenticação JWT

- Login com e-mail e senha.
- Criptografia de senhas com PBKDF2/SHA-256 (`werkzeug.security`).
- Autenticação e autorização por perfil via **JSON Web Tokens (JWT)** nos endpoints administrativos.
- Cadastro de usuário autenticado, com senha mínima de 8 caracteres; usuários podem ser desativados sem apagar o histórico.
- No primeiro início, a aplicação cria um usuário coordenador se ainda não houver usuários:
  - **E-mail:** `coordenador@senai.br`
  - **Senha:** `senai2026`
- Altere as credenciais iniciais e configure segredos fortes no ambiente antes de disponibilizar a aplicação.

### API de gestão

- `GET/POST /api/calendars`: lista calendários ou cria um período a partir de `year`, `semester` e `category_ids`.
- `GET/POST /api/categories`, `PUT /api/categories/<id>` e `DELETE /api/categories/<id>`: consulta, cadastra, edita, ativa/inativa e exclui categorias.
- `GET/POST /api/users`, `PUT /api/users/<id>` e `DELETE /api/users/<id>`: consulta, cadastra, edita e exclui usuários.
- A criação e edição de calendários, usuários e categorias exigem token de Diretor, Coordenador ou OPP. Colaboradores têm acesso somente de leitura aos calendários.
- A assinatura digital exige perfil de Diretor. Perfis antigos de administrador são migrados para Diretor.
- Se ainda não houver Diretor ativo, Coordenador ou OPP pode cadastrar o primeiro; depois, somente um Diretor pode conceder esse perfil.
- Contas de Diretor só podem ser editadas por outro Diretor, preservando a restrição de assinatura.

---

## 🚀 Como Executar

### 1. Pré-requisitos:
- Python 3.10+
- PostgreSQL 12+ em execução (banco `calendario_escolar` configurado)

### 2. Ativação do ambiente e execução:
No PowerShell:
```powershell
.\.venv\Scripts\Activate.ps1
python app.py
```

Acesse no navegador:
```
http://127.0.0.1:5000
```

### 3. Execução dos testes:
```powershell
python test_suite.py
```
