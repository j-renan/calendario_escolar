/**
 * Antigravity - Gestão de Calendário Escolar SENAI-SP
 * Frontend Application Controller
 */

document.addEventListener("DOMContentLoaded", () => {
    const app = new CalendarApp();
    app.init();
});

class CalendarApp {
    constructor() {
        this.calendar = null;
        this.currentUser = null;
        this.selectedDayContext = null;
        this.filterCategory = "all";
        this.editingUserId = null;
        this.users = [];
        this.editingCategoryId = null;
        this.categories = [];
    }

    async init() {
        this.setupEventListeners();
        if (await this.checkAuthStatus()) {
            await this.loadCalendars();
        }
    }

    async checkAuthStatus() {
        const user = window.apiService.getCurrentUser();
        const token = window.apiService.getToken();
        if (token && user) {
            try {
                this.currentUser = await window.apiService.getProfile();
                this.updateUserUI();
                document.getElementById("authScreen").style.display = "none";
                return true;
            } catch (error) {
                window.apiService.clearAuth();
            }
        }
        this.currentUser = null;
        this.updateUserUI();
        document.getElementById("authScreen").style.display = "flex";
        return false;
    }

    updateUserUI() {
        const nameEl = document.getElementById("userName");
        const roleEl = document.getElementById("userRole");
        const avatarEl = document.getElementById("userAvatar");
        const btnAuth = document.getElementById("btnAuthToggle");
        const role = this.currentUser?.role?.toLowerCase();
        const canEdit = ["diretor", "coordenador", "opp"].includes(role);

        if (this.currentUser) {
            nameEl.textContent = this.currentUser.name || "Coordenador";
            roleEl.textContent = {
                diretor: "DIRETOR",
                coordenador: "COORDENADOR",
                opp: "OPP",
                colaborador: "COLABORADOR"
            }[role] || "USUÁRIO";
            avatarEl.textContent = (this.currentUser.name || "C").charAt(0).toUpperCase();
            btnAuth.innerHTML = `<i class="fa-solid fa-right-from-bracket"></i> Sair`;
            btnAuth.onclick = () => this.handleLogout();
        } else {
            nameEl.textContent = "Não autenticado";
            roleEl.textContent = "Visitante";
            avatarEl.textContent = "?";
            btnAuth.innerHTML = `<i class="fa-solid fa-right-to-bracket"></i> Entrar`;
            btnAuth.onclick = () => {
                document.getElementById("authScreen").style.display = "flex";
            };
        }

        document.querySelectorAll('.sidebar-nav .nav-item[data-tab="usuarios"], .sidebar-nav .nav-item[data-tab="categorias"]')
            .forEach(item => { item.hidden = !canEdit; });
        for (const id of ["btnCreateCalendar", "btnSaveDraft", "btnPublish", "btnDeleteCalendar"]) {
            const button = document.getElementById(id);
            if (button) button.hidden = !canEdit;
        }
        const signButton = document.getElementById("btnDigitalSign");
        if (signButton) signButton.hidden = role !== "diretor";
    }

    handleLogout() {
        window.apiService.clearAuth();
        this.currentUser = null;
        this.updateUserUI();
        document.getElementById("authScreen").style.display = "flex";
        this.showToast("Sessão encerrada com sucesso.", "info");
    }

    setupEventListeners() {
        // Toolbar buttons
        document.getElementById("btnSaveDraft")?.addEventListener("click", () => this.saveDraft());
        document.getElementById("btnPublish")?.addEventListener("click", () => this.publishCalendar());
        document.getElementById("btnUndo")?.addEventListener("click", () => this.openHistoryModal());
        document.getElementById("btnFilter")?.addEventListener("click", () => this.toggleFilterModal());
        document.getElementById("btnDeleteCalendar")?.addEventListener("click", () => this.deleteCalendar());
        document.getElementById("btnToggleSidebar")?.addEventListener("click", (event) => {
            const button = event.currentTarget;
            const isExpanded = button.getAttribute("aria-expanded") === "true";
            document.querySelector(".app-container")?.classList.toggle("sidebar-collapsed", isExpanded);
            button.setAttribute("aria-expanded", String(!isExpanded));
            const label = isExpanded ? "Expandir menu lateral" : "Recolher menu lateral";
            button.setAttribute("aria-label", label);
            button.title = label;
            button.querySelector("i").className = isExpanded
                ? "fa-solid fa-angles-right"
                : "fa-solid fa-angles-left";
        });
        document.getElementById("btnExportDropdown")?.addEventListener("click", (e) => {
            e.stopPropagation();
            document.getElementById("exportMenu")?.classList.toggle("active");
        });

        // Close export menu on outside click
        document.addEventListener("click", () => {
            document.getElementById("exportMenu")?.classList.remove("active");
        });

        // Export options
        document.getElementById("exportPdf")?.addEventListener("click", (e) => {
            e.preventDefault();
            this.exportPdf();
        });
        document.getElementById("exportPrint")?.addEventListener("click", (e) => {
            e.preventDefault();
            window.print();
        });
        document.getElementById("exportJson")?.addEventListener("click", (e) => {
            e.preventDefault();
            this.exportJson();
        });

        // Modals close buttons
        document.querySelectorAll(".btn-close-modal, .btn-modal-cancel").forEach(btn => {
            btn.addEventListener("click", (e) => {
                const modal = e.target.closest(".modal-overlay");
                if (modal) modal.classList.remove("active");
            });
        });

        // Day edit form submit
        document.getElementById("formEditDay")?.addEventListener("submit", (e) => {
            e.preventDefault();
            this.submitDayEdit();
        });
        document.getElementById("editDayType")?.addEventListener("change", () => this.toggleMilestoneFields());
        document.getElementById("editDayMilestone")?.addEventListener("change", () => this.updateMilestoneCategorySelection());

        // Auth form submit
        document.getElementById("formLogin")?.addEventListener("submit", (e) => {
            e.preventDefault();
            this.submitLoginScreen();
        });
        document.getElementById("btnCreateCalendar")?.addEventListener("click", () => this.openCalendarCreate());
        document.getElementById("formCalendarCreate")?.addEventListener("submit", (e) => {
            e.preventDefault();
            this.submitCalendarCreate();
        });
        document.getElementById("calendarSelector")?.addEventListener("change", async (e) => {
            if (!e.target.value) return;
            try {
                this.calendar = await window.apiService.getCalendar(e.target.value);
                this.renderCalendar();
            } catch (error) {
                this.showToast("Falha ao abrir calendário: " + error.message, "error");
            }
        });
        document.getElementById("formUserCreate")?.addEventListener("submit", (e) => {
            e.preventDefault();
            this.submitUserCreate();
        });
        document.getElementById("btnCancelUserEdit")?.addEventListener("click", () => this.resetUserForm());
        document.getElementById("formCategoryCreate")?.addEventListener("submit", (e) => {
            e.preventDefault();
            this.submitCategoryCreate();
        });
        document.getElementById("btnCancelCategoryEdit")?.addEventListener("click", () => this.resetCategoryForm());
        document.getElementById("usersList")?.addEventListener("click", (e) => this.handleUserListClick(e));
        document.getElementById("categoriesList")?.addEventListener("click", (e) => this.handleCategoryListClick(e));

        // Director digital signature button
        document.getElementById("btnDigitalSign")?.addEventListener("click", () => {
            this.signApproval();
        });

        // Navigation tabs
        document.querySelectorAll(".sidebar-nav .nav-item").forEach(item => {
            item.addEventListener("click", (e) => {
                e.preventDefault();
                const tab = item.getAttribute("data-tab");
                document.querySelectorAll(".sidebar-nav .nav-item").forEach(navItem => {
                    navItem.classList.toggle("active", navItem === item);
                });
                if (tab === "historico") {
                    this.openHistoryModal();
                } else if (tab === "calendarios") {
                    this.showCalendarPage();
                } else if (tab === "usuarios") {
                    this.showUsersPage();
                } else if (tab === "categorias") {
                    this.showCategoriesPage();
                }
            });
        });
    }

    async submitLoginScreen() {
        const email = document.getElementById("loginEmail").value;
        const password = document.getElementById("loginPassword").value;
        const errorBox = document.getElementById("loginError");
        errorBox.textContent = "";
        try {
            const res = await window.apiService.login(email, password);
            this.currentUser = res.user;
            this.updateUserUI();
            this.showCalendarPage();
            document.getElementById("authScreen").style.display = "none";
            await this.loadCalendars();
        } catch (error) {
            errorBox.textContent = error.message;
        }
    }

    async loadCalendars(preferredCalendarId = this.calendar?.id) {
        try {
            const calendars = await window.apiService.getCalendars();
            const selector = document.getElementById("calendarSelector");
            selector.innerHTML = calendars.map(item =>
                `<option value="${item.id}">${this.escapeHtml(item.semester_year)} - ${this.escapeHtml(item.status)}</option>`
            ).join("");
            const selected = calendars.find(item => item.id === preferredCalendarId) || calendars[0];
            if (!selected) {
                this.calendar = null;
                selector.innerHTML = '<option value="">Nenhum calendário</option>';
                this.renderEmptyCalendar();
                return;
            }
            selector.value = String(selected.id);
            this.calendar = await window.apiService.getCalendar(selected.id);
            this.renderCalendar();
        } catch (error) {
            this.showToast("Falha ao listar calendários: " + error.message, "error");
        }
    }

    async deleteCalendar() {
        if (!this.calendar) return;
        const calendarId = this.calendar.id;
        const period = this.calendar.semester_year;
        if (!confirm(`Excluir permanentemente o calendário ${period} e todo o seu histórico? Esta ação não pode ser desfeita.`)) {
            return;
        }
        try {
            await window.apiService.deleteCalendar(calendarId);
            this.calendar = null;
            await this.loadCalendars();
            this.showToast(`Calendário ${period} excluído.`, "success");
        } catch (error) {
            this.showToast("Falha ao excluir calendário: " + error.message, "error");
        }
    }

    renderEmptyCalendar() {
        document.getElementById("emptyCalendarState").hidden = false;
        document.querySelector(".sheet-container").hidden = true;
        document.getElementById("calStatusBadge").hidden = true;
        for (const id of ["btnDeleteCalendar", "btnSaveDraft", "btnPublish", "btnUndo", "btnFilter", "btnExportDropdown"]) {
            document.getElementById(id).disabled = true;
        }
    }

    async openCalendarCreate() {
        try {
            const categories = await window.apiService.getCategories(true);
            const choices = document.getElementById("calendarCategoryChoices");
            choices.innerHTML = categories.map(category => `
                <label class="management-row">
                    <input type="checkbox" value="${category.id}" checked>
                    <span>${this.escapeHtml(category.name)}</span>
                </label>
            `).join("") || "<p>Nenhuma categoria ativa disponível.</p>";
            document.getElementById("calendarYear").value = new Date().getFullYear();
            document.getElementById("modalCalendarCreate").classList.add("active");
        } catch (error) {
            this.showToast("Falha ao carregar categorias: " + error.message, "error");
        }
    }

    async submitCalendarCreate() {
        const year = Number(document.getElementById("calendarYear").value);
        const semester = Number(document.getElementById("calendarSemester").value);
        const categoryIds = [...document.querySelectorAll("#calendarCategoryChoices input:checked")]
            .map(input => Number(input.value));
        try {
            const result = await window.apiService.createCalendar(year, semester, categoryIds);
            this.calendar = result.calendar;
            document.getElementById("modalCalendarCreate").classList.remove("active");
            await this.loadCalendars();
            this.renderCalendar();
            this.showToast("Calendário criado com sucesso.", "success");
        } catch (error) {
            this.showToast("Não foi possível criar o calendário: " + error.message, "error");
        }
    }

    async showCategoriesPage() {
        if (!this.currentUser || !["diretor", "coordenador", "opp"].includes(this.currentUser.role.toLowerCase())) {
            this.showToast("Você não tem permissão para acessar esta área.", "error");
            return;
        }
        document.getElementById("toolbarHeader").hidden = true;
        document.getElementById("calendarPage").hidden = true;
        document.getElementById("usersPage").hidden = true;
        document.getElementById("categoriesPage").hidden = false;
        await this.loadCategories();
    }

    async showUsersPage() {
        if (!this.currentUser || !["diretor", "coordenador", "opp"].includes(this.currentUser.role.toLowerCase())) {
            this.showToast("Você não tem permissão para acessar esta área.", "error");
            return;
        }
        document.getElementById("toolbarHeader").hidden = true;
        document.getElementById("calendarPage").hidden = true;
        document.getElementById("usersPage").hidden = false;
        await this.loadUsers();
    }

    showCalendarPage() {
        document.getElementById("toolbarHeader").hidden = false;
        document.getElementById("calendarPage").hidden = false;
        document.getElementById("usersPage").hidden = true;
        document.getElementById("categoriesPage").hidden = true;
    }

    async loadUsers() {
        try {
            this.users = await window.apiService.getUsers();
            const hasActiveDirector = this.users.some(user => user.role === "diretor" && user.is_active);
            const directorOption = document.querySelector('#newUserRole option[value="diretor"]');
            if (directorOption) {
                directorOption.hidden = this.currentUser.role !== "diretor" && hasActiveDirector;
            }
            const roleLabels = {
                diretor: "Diretor",
                coordenador: "Coordenador",
                opp: "OPP",
                colaborador: "Colaborador"
            };
            const usersList = document.getElementById("usersList");
            usersList.innerHTML = this.users.map(user => {
                const protectedDirector = this.currentUser.role !== "diretor" && user.role === "diretor";
                return `
                    <tr data-user-id="${user.id}">
                        <td data-label="Nome">${this.escapeHtml(user.name)}</td>
                        <td data-label="E-mail">${this.escapeHtml(user.email)}</td>
                        <td data-label="Perfil">${roleLabels[user.role] || this.escapeHtml(user.role)}</td>
                        <td data-label="Status">
                            <span class="user-status ${user.is_active ? "user-status-active" : "user-status-inactive"}">
                                ${user.is_active ? "Ativo" : "Inativo"}
                            </span>
                        </td>
                        <td data-label="Ações" class="user-actions">
                            <button class="btn-toolbar user-edit" type="button" ${protectedDirector ? "disabled" : ""}>
                                <i class="fa-solid fa-pen"></i> Editar
                            </button>
                            <button class="btn-toolbar btn-danger user-delete" type="button" ${user.id === this.currentUser.id || protectedDirector ? "disabled" : ""}>
                                <i class="fa-solid fa-trash"></i> Excluir
                            </button>
                        </td>
                    </tr>
                `;
            }).join("") || `<tr><td class="users-empty" colspan="5">Nenhum usuário cadastrado.</td></tr>`;
        } catch (error) {
            this.showToast("Falha ao carregar usuários: " + error.message, "error");
        }
    }

    async submitUserCreate() {
        const password = document.getElementById("newUserPassword").value;
        const payload = {
            name: document.getElementById("newUserName").value,
            email: document.getElementById("newUserEmail").value,
            role: document.getElementById("newUserRole").value
        };
        if (this.editingUserId) {
            payload.is_active = document.getElementById("newUserStatus").value === "true";
            if (password) payload.password = password;
        } else {
            payload.password = password;
        }
        try {
            if (this.editingUserId) {
                await window.apiService.updateUser(this.editingUserId, payload);
                this.showToast("Usuário atualizado.", "success");
            } else {
                await window.apiService.createUser(payload);
                this.showToast("Usuário cadastrado.", "success");
            }
            this.resetUserForm();
            await this.loadUsers();
        } catch (error) {
            this.showToast("Falha ao salvar usuário: " + error.message, "error");
        }
    }

    async handleUserListClick(event) {
        const button = event.target.closest("button");
        const row = button?.closest("[data-user-id]");
        if (!row) return;
        const userId = Number(row.dataset.userId);
        const user = this.users.find(item => item.id === userId);
        if (!user || !button) return;
        if (button.classList.contains("user-edit")) {
            this.editingUserId = userId;
            document.getElementById("userFormTitle").textContent = "Editar usuário";
            document.getElementById("newUserName").value = user.name;
            document.getElementById("newUserEmail").value = user.email;
            document.getElementById("newUserPassword").value = "";
            document.getElementById("newUserPassword").required = false;
            document.getElementById("newUserPasswordLabel").textContent = "Nova senha (opcional)";
            document.getElementById("newUserRole").value = user.role;
            document.getElementById("newUserRole").disabled = this.currentUser.role !== "diretor" && user.role === "diretor";
            document.getElementById("newUserStatus").value = String(user.is_active);
            document.getElementById("newUserStatusGroup").hidden = false;
            document.getElementById("btnSaveUser").innerHTML = '<i class="fa-solid fa-floppy-disk"></i> Salvar alterações';
            document.getElementById("btnCancelUserEdit").hidden = false;
            document.getElementById("newUserName").focus();
            return;
        }
        if (button.classList.contains("user-delete")) {
            if (!confirm(`Excluir o usuário "${user.name}"? Esta ação não pode ser desfeita.`)) return;
            try {
                await window.apiService.deleteUser(userId);
                await this.loadUsers();
                this.showToast("Usuário excluído.", "success");
            } catch (error) {
                this.showToast("Falha ao excluir usuário: " + error.message, "error");
            }
        }
    }

    resetUserForm() {
        this.editingUserId = null;
        document.getElementById("formUserCreate").reset();
        document.getElementById("userFormTitle").textContent = "Cadastrar usuário";
        document.getElementById("newUserPassword").required = true;
        document.getElementById("newUserPasswordLabel").textContent = "Senha (mín. 8 caracteres)";
        document.getElementById("newUserRole").disabled = false;
        document.getElementById("newUserStatusGroup").hidden = true;
        document.getElementById("btnSaveUser").innerHTML = '<i class="fa-solid fa-user-plus"></i> Cadastrar usuário';
        document.getElementById("btnCancelUserEdit").hidden = true;
        if (this.currentUser && this.currentUser.role !== "diretor") {
            document.getElementById("newUserRole").value = "coordenador";
        }
    }

    async loadCategories() {
        try {
            this.categories = await window.apiService.getCategories();
            document.getElementById("categoriesList").innerHTML = this.categories.map(category => `
                <tr data-category-id="${category.id}">
                    <td data-label="Categoria">${this.escapeHtml(category.name)}</td>
                    <td data-label="Status">
                        <span class="user-status ${category.is_active ? "user-status-active" : "user-status-inactive"}">
                            ${category.is_active ? "Ativa" : "Inativa"}
                        </span>
                    </td>
                    <td data-label="Ações" class="user-actions">
                        <button class="btn-toolbar category-edit" type="button">
                            <i class="fa-solid fa-pen"></i> Editar
                        </button>
                        <button class="btn-toolbar btn-danger category-delete" type="button">
                            <i class="fa-solid fa-trash"></i> Excluir
                        </button>
                    </td>
                </tr>
            `).join("") || `<tr><td class="users-empty" colspan="3">Nenhuma categoria cadastrada.</td></tr>`;
        } catch (error) {
            this.showToast("Falha ao carregar categorias: " + error.message, "error");
        }
    }

    async submitCategoryCreate() {
        try {
            const name = document.getElementById("newCategoryName").value;
            if (this.editingCategoryId) {
                await window.apiService.updateCategory(
                    this.editingCategoryId,
                    name,
                    document.getElementById("categoryStatus").value === "true"
                );
                this.showToast("Categoria atualizada.", "success");
            } else {
                await window.apiService.createCategory(name);
                this.showToast("Categoria cadastrada.", "success");
            }
            this.resetCategoryForm();
            await this.loadCategories();
        } catch (error) {
            this.showToast("Falha ao salvar categoria: " + error.message, "error");
        }
    }

    async handleCategoryListClick(event) {
        const button = event.target.closest("button");
        const row = button?.closest("[data-category-id]");
        if (!row) return;
        const categoryId = Number(row.dataset.categoryId);
        const category = this.categories.find(item => item.id === categoryId);
        if (!category || !button) return;
        if (button.classList.contains("category-edit")) {
            this.editingCategoryId = categoryId;
            document.getElementById("categoryFormTitle").textContent = "Editar categoria";
            document.getElementById("newCategoryName").value = category.name;
            document.getElementById("categoryStatus").value = String(category.is_active);
            document.getElementById("categoryStatusGroup").hidden = false;
            document.getElementById("btnSaveCategory").innerHTML = '<i class="fa-solid fa-floppy-disk"></i> Salvar alterações';
            document.getElementById("btnCancelCategoryEdit").hidden = false;
            document.getElementById("newCategoryName").focus();
            return;
        }
        if (button.classList.contains("category-delete")) {
            if (!confirm(`Excluir a categoria "${category.name}"? Ela deixará de aparecer nas opções para novos calendários. Calendários existentes manterão seus dados.`)) return;
            try {
                await window.apiService.deleteCategory(categoryId);
                await this.loadCategories();
                this.showToast("Categoria excluída.", "success");
            } catch (error) {
                this.showToast("Falha ao excluir categoria: " + error.message, "error");
            }
        }
    }

    resetCategoryForm() {
        this.editingCategoryId = null;
        document.getElementById("formCategoryCreate").reset();
        document.getElementById("categoryFormTitle").textContent = "Cadastrar categoria";
        document.getElementById("categoryStatusGroup").hidden = true;
        document.getElementById("btnSaveCategory").innerHTML = '<i class="fa-solid fa-plus"></i> Cadastrar categoria';
        document.getElementById("btnCancelCategoryEdit").hidden = true;
    }

    escapeHtml(value) {
        const element = document.createElement("span");
        element.textContent = value ?? "";
        return element.innerHTML;
    }

    renderCalendar() {
        if (!this.calendar) return;
        document.getElementById("emptyCalendarState").hidden = true;
        document.querySelector(".sheet-container").hidden = false;
        document.getElementById("calStatusBadge").hidden = false;
        for (const id of ["btnDeleteCalendar", "btnSaveDraft", "btnPublish", "btnUndo", "btnFilter", "btnExportDropdown"]) {
            document.getElementById(id).disabled = false;
        }
        const selector = document.getElementById("calendarSelector");
        if (selector) selector.value = String(this.calendar.id);

        // 1. Header Information
        document.getElementById("calTitle").textContent = this.calendar.title || "CALENDÁRIO ESCOLAR";
        document.getElementById("calUnitCode").textContent = this.calendar.unit_code || "CFP 5.10";
        document.getElementById("calSemesterYear").textContent = this.calendar.semester_year || "2º / 2026";
        
        const badgeStatus = document.getElementById("calStatusBadge");
        if (badgeStatus) {
            badgeStatus.textContent = this.calendar.status === "publicado" ? "Publicado" : "Rascunho";
            badgeStatus.className = `badge-status badge-${this.calendar.status || 'rascunho'}`;
        }

        // 2. Summary Cards (Top 4 Courses)
        this.renderSummaryCards();

        // 3. Month Grid (Left: Jul, Ago, Set | Right: Out, Nov, Dez)
        this.renderMonthsGrid();

        // 4. Compensations Table & Version
        this.renderCompensations();

        // 5. Director Approval Box
        this.renderApprovalBox();
    }

    renderSummaryCards() {
        const container = document.getElementById("summaryCardsGrid");
        if (!container) return;
        container.innerHTML = "";

        const categories = this.calendar.categories || [];
        const monthAbbrs = {
            1: "JAN", 2: "FEV", 3: "MAR", 4: "ABR", 5: "MAI", 6: "JUN",
            7: "JUL", 8: "AGO", 9: "SET", 10: "OUT", 11: "NOV", 12: "DEZ"
        };
        categories.forEach(cat => {
            if (this.filterCategory !== "all" && String(cat.id) !== this.filterCategory) {
                return;
            }

            const m = cat.monthly_days || {};
            const monthCells = (this.calendar.months || []).map(month => {
                const abbreviation = month.month_abbr || monthAbbrs[month.month_index];
                return `<div class="monthly-cell"><span class="m-name">${abbreviation}</span><span class="m-val">${m[abbreviation] ?? 0}</span></div>`;
            }).join("");
            const card = document.createElement("div");
            card.className = "summary-card";
            card.innerHTML = `
                <div>
                    <div class="card-course-title">${this.escapeHtml(cat.title)}</div>
                    <div class="card-dates">
                        <span>Início: <b>${this.escapeHtml(cat.start_date)}</b></span>
                        <span>Término: <b>${this.escapeHtml(cat.end_date)}</b></span>
                    </div>
                    <div class="card-monthly-table">${monthCells}</div>
                </div>
                <div class="card-total-box">
                    <span class="total-label">Dias Letivos</span>
                    <span class="total-value">TOTAL: ${cat.total_days}</span>
                </div>
            `;
            container.appendChild(card);
        });
    }

    renderMonthsGrid() {
        const leftCol = document.getElementById("monthsColLeft");
        const rightCol = document.getElementById("monthsColRight");
        if (!leftCol || !rightCol) return;

        leftCol.innerHTML = "";
        rightCol.innerHTML = "";

        const months = this.calendar.months || [];
        months.forEach(m => {
            const card = this.createMonthCard(m);
            if (m.column === "left") {
                leftCol.appendChild(card);
            } else {
                rightCol.appendChild(card);
            }
        });
    }

    createMonthCard(month) {
        const card = document.createElement("div");
        card.className = "month-card";

        // Header
        const header = document.createElement("div");
        header.className = "month-header";
        header.innerHTML = `
            <h3>${month.month_name}</h3>
            <span class="month-year">${month.year}</span>
        `;
        card.appendChild(header);

        // Body: Calendar Grid + Events Column
        const body = document.createElement("div");
        body.className = "month-body";

        // 1. Calendar Days Table
        const calWrap = document.createElement("div");
        calWrap.className = "calendar-grid-wrap";
        
        let tableHtml = `
            <table class="calendar-table">
                <thead>
                    <tr>
                        <th>D</th>
                        <th>2ª</th>
                        <th>3ª</th>
                        <th>4ª</th>
                        <th>5ª</th>
                        <th>6ª</th>
                        <th>S</th>
                    </tr>
                </thead>
                <tbody>
        `;

        const weeks = month.calendar_weeks || [];
        weeks.forEach(week => {
            tableHtml += `<tr>`;
            week.forEach(cell => {
                if (!cell || cell.day === null || cell.type === "empty") {
                    tableHtml += `<td class="day-empty"></td>`;
                } else {
                    const typeClass = `day-${cell.type || 'letivo'}`;
                    const tooltip = cell.title ? this.escapeHtml(cell.title).replace(/"/g, "&quot;") : `Dia ${cell.day}`;
                    tableHtml += `
                        <td class="${typeClass}" title="${tooltip}" data-month="${month.month_index}" data-day="${cell.day}" data-type="${this.escapeHtml(cell.type || "letivo")}" data-title="${this.escapeHtml(cell.title || '').replace(/"/g, "&quot;")}">
                            ${cell.day}
                        </td>
                    `;
                }
            });
            tableHtml += `</tr>`;
        });

        tableHtml += `</tbody></table>`;
        calWrap.innerHTML = tableHtml;

        // Attach click listener to day cells for editing
        if (["diretor", "coordenador", "opp"].includes(this.currentUser?.role?.toLowerCase())) {
            calWrap.querySelectorAll("td:not(.day-empty)").forEach(td => {
                td.addEventListener("click", () => {
                const monthIndex = parseInt(td.getAttribute("data-month"), 10);
                const day = parseInt(td.getAttribute("data-day"), 10);
                const type = td.getAttribute("data-type");
                const title = td.getAttribute("data-title");
                this.openEditDayModal(monthIndex, day, type, title, month.month_name, month.year);
                });
            });
        }

        body.appendChild(calWrap);

        // 2. Events Column
        const evWrap = document.createElement("div");
        evWrap.className = "month-events-wrap";
        let evHtml = `
            <div class="events-title">
                <span><i class="fa-regular fa-calendar-check"></i> EVENTOS</span>
            </div>
            <div class="events-list">
        `;

        const events = month.events || [];
        if (events.length === 0) {
            evHtml += `<span style="font-size: 10px; color: #94A3B8; font-style: italic;">Nenhum evento registrado.</span>`;
        } else {
            events.forEach(ev => {
                const colorClass = `event-${ev.color_type || 'blue'}`;
                evHtml += `
                    <div class="event-item ${colorClass}">
                        <span class="event-date">• ${this.escapeHtml(ev.date_label)}:</span>
                        <span class="event-desc">${this.escapeHtml(ev.description)}</span>
                    </div>
                `;
            });
        }
        evHtml += `</div>`;
        evWrap.innerHTML = evHtml;
        body.appendChild(evWrap);

        card.appendChild(body);

        // Month Footer Note
        if (month.footer_note) {
            const footerNote = document.createElement("div");
            footerNote.className = "month-footer-note";
            footerNote.innerHTML = `<i class="fa-solid fa-circle-info" style="color: #0284C7;"></i> <span>${month.footer_note}</span>`;
            card.appendChild(footerNote);
        }

        // Below Grid: School Days for each course category
        const courseDaysRow = document.createElement("div");
        courseDaysRow.className = "month-course-days-row";
        
        let pillsHtml = ``;
        const courseDays = month.course_days || {};
        for (const [courseName, count] of Object.entries(courseDays)) {
            pillsHtml += `
                <div class="course-day-pill">
                    <span class="course-lbl">${courseName}:</span>
                    <span class="course-cnt">${count} d</span>
                </div>
            `;
        }
        courseDaysRow.innerHTML = pillsHtml || `<span style="font-size: 9px; color: #64748B;">Dias Letivos calculados por categoria</span>`;
        card.appendChild(courseDaysRow);

        return card;
    }

    renderCompensations() {
        const tableBody = document.querySelector("#compensationTable tbody");
        if (tableBody) {
            tableBody.innerHTML = "";
            (this.calendar.compensations || []).forEach(row => {
                const tr = document.createElement("tr");
                tr.innerHTML = `
                    <td><b>${row.dias_a_compensar}</b></td>
                    <td><b style="color: #0284C7;">${row.dias_compensacao}</b></td>
                    <td>${row.observacao || ''}</td>
                `;
                tableBody.appendChild(tr);
            });
        }

        const verStamp = document.getElementById("versionStamp");
        if (verStamp) {
            verStamp.textContent = this.calendar.version || "Versão 01 - 06/10/2026";
        }
    }

    renderApprovalBox() {
        const dirName = document.getElementById("approvalDirectorName");
        const statusBadge = document.getElementById("approvalStatusBadge");
        const signatureStamp = document.getElementById("approvalSignatureStamp");
        const btnSign = document.getElementById("btnDigitalSign");

        if (dirName) dirName.textContent = this.calendar.director_name || "Tiago Roberto Ferreira";

        const isSigned = this.calendar.director_signature_status === "Assinado Digitalmente";
        if (statusBadge) {
            statusBadge.className = `approval-status-badge ${isSigned ? 'approval-signed' : 'approval-pending'}`;
            statusBadge.innerHTML = isSigned 
                ? `<i class="fa-solid fa-circle-check"></i> Assinado Digitalmente`
                : `<i class="fa-solid fa-clock"></i> Pendente de Assinatura`;
        }

        if (signatureStamp) {
            if (isSigned) {
                signatureStamp.style.display = "block";
                signatureStamp.innerHTML = `
                    <div style="display: none"><b>CHAVE HASH DE AUTENTICAÇÃO:</b> ${this.calendar.signature_hash}</div>
                    <div><b>DATA/HORA DA ASSINATURA:</b> ${this.calendar.signature_date}</div>
                    <div style="font-size: 9.5px; margin-top: 2px;">Assinado com certificado digital SENAI-SP CFP 5.10</div>
                `;
                if (btnSign) btnSign.style.display = "none";
            } else {
                signatureStamp.style.display = "none";
                if (btnSign) btnSign.style.display = this.currentUser?.role?.toLowerCase() === "diretor"
                    ? "inline-flex"
                    : "none";
            }
        }
    }

    // Modal Operations
    openEditDayModal(monthIndex, day, currentType, currentTitle, monthName, year) {
        this.selectedDayContext = { monthIndex, day, year };
        document.getElementById("modalDayMonthName").textContent = `${monthName} / ${year}`;
        document.getElementById("modalDayNumber").textContent = `Dia ${day}`;
        document.getElementById("editDayType").value = currentType || "letivo";
        document.getElementById("editDayTitle").value = currentTitle || "";
        const dateValue = `${String(day).padStart(2, "0")}/${String(monthIndex).padStart(2, "0")}/${year}`;
        const matchingStart = this.calendar.categories.filter(category => category.start_date === dateValue);
        const matchingEnd = this.calendar.categories.filter(category => category.end_date === dateValue);
        document.getElementById("editDayMilestone").value = matchingEnd.length && !matchingStart.length ? "termino" : "inicio";
        this.renderMilestoneCategories(dateValue);
        this.toggleMilestoneFields();

        const modal = document.getElementById("modalEditDay");
        if (modal) modal.classList.add("active");
    }

    renderMilestoneCategories(dateValue, preserveSelection = false) {
        const milestone = document.getElementById("editDayMilestone").value;
        const dateField = milestone === "inicio" ? "start_date" : "end_date";
        const choices = document.getElementById("editDayCategories");
        const previouslySelected = preserveSelection
            ? new Set([...choices.querySelectorAll("input:checked")].map(input => input.value))
            : null;
        const matchingIds = new Set(
            this.calendar.categories
                .filter(category => category[dateField] === dateValue)
                .map(category => String(category.id))
        );
        if (preserveSelection && matchingIds.size === 0) {
            matchingIds.clear();
            previouslySelected.forEach(id => matchingIds.add(id));
        }
        choices.innerHTML = this.calendar.categories.map(category => `
            <label class="management-row">
                <input type="checkbox" value="${this.escapeHtml(category.id)}" ${matchingIds.has(String(category.id)) ? "checked" : ""}>
                <span>${this.escapeHtml(category.title)}</span>
            </label>
        `).join("") || "<p>Este calendário não possui categorias.</p>";
    }

    toggleMilestoneFields() {
        const isMilestone = document.getElementById("editDayType").value === "inicio_aulas";
        document.getElementById("editDayMilestoneGroup").hidden = !isMilestone;
        document.getElementById("editDayCategoriesGroup").hidden = !isMilestone;
    }

    updateMilestoneCategorySelection() {
        if (!this.selectedDayContext) return;
        const { monthIndex, day, year } = this.selectedDayContext;
        const dateValue = `${String(day).padStart(2, "0")}/${String(monthIndex).padStart(2, "0")}/${year}`;
        this.renderMilestoneCategories(dateValue, true);
    }

    async submitDayEdit() {
        if (!this.selectedDayContext || !this.calendar) return;

        const newType = document.getElementById("editDayType").value;
        const newTitle = document.getElementById("editDayTitle").value;
        const milestone = newType === "inicio_aulas" ? document.getElementById("editDayMilestone").value : null;
        const categoryIds = newType === "inicio_aulas"
            ? [...document.querySelectorAll("#editDayCategories input:checked")].map(input => input.value)
            : [];
        if (newType === "inicio_aulas" && categoryIds.length === 0) {
            this.showToast("Selecione ao menos uma categoria de curso.", "error");
            return;
        }
        const editedDay = this.selectedDayContext.day;

        try {
            const res = await window.apiService.updateDay(
                this.calendar.id,
                this.selectedDayContext.monthIndex,
                this.selectedDayContext.day,
                newType,
                newTitle,
                milestone,
                categoryIds
            );

            this.calendar = res.calendar;
            this.renderCalendar();
            document.getElementById("modalEditDay")?.classList.remove("active");
            this.selectedDayContext = null;
            this.showToast(`Dia ${editedDay} atualizado com sucesso!`, "success");
        } catch (err) {
            this.showToast("Falha ao atualizar dia: " + err.message, "error");
        }
    }

    async saveDraft() {
        if (!this.calendar) return;
        try {
            const res = await window.apiService.saveDraft(this.calendar.id, this.calendar);
            this.calendar = res.calendar;
            this.renderCalendar();
            this.showToast("Rascunho salvo com sucesso no banco de dados!", "success");
        } catch (err) {
            this.showToast("Erro ao salvar rascunho: " + err.message, "error");
        }
    }

    async publishCalendar() {
        if (!this.calendar) return;
        try {
            const res = await window.apiService.publishCalendar(this.calendar.id);
            this.calendar = res.calendar;
            this.renderCalendar();
            this.showToast(`Calendário publicado com sucesso! ${res.calendar.version}`, "success");
        } catch (err) {
            this.showToast("Erro ao publicar: " + err.message, "error");
        }
    }

    async signApproval() {
        if (!this.calendar) return;
        try {
            const res = await window.apiService.signApproval(this.calendar.id, "Tiago Roberto Ferreira");
            this.calendar = res.calendar;
            this.renderCalendar();
            this.showToast("Calendário assinado digitalmente com sucesso!", "success");
        } catch (err) {
            this.showToast("Erro na assinatura digital: " + err.message, "error");
        }
    }

    async openHistoryModal() {
        if (!this.calendar) return;
        const modal = document.getElementById("modalHistory");
        const list = document.getElementById("historyList");
        if (!modal || !list) return;

        list.innerHTML = `<div style="text-align:center; padding: 20px; color:#64748B;"><i class="fa-solid fa-spinner fa-spin"></i> Carregando histórico...</div>`;
        modal.classList.add("active");

        try {
            const history = await window.apiService.getHistory(this.calendar.id);
            list.innerHTML = "";
            if (history.length === 0) {
                list.innerHTML = `<div style="text-align: center; color: #94A3B8; padding: 20px;">Nenhuma ação anterior registrada.</div>`;
                return;
            }

            history.forEach(item => {
                const row = document.createElement("div");
                row.className = "history-item";
                row.innerHTML = `
                    <div>
                        <div style="font-weight: 700; color: #002B49;">${item.action}</div>
                        <div style="font-size: 10.5px; color: #64748B;">
                            <i class="fa-regular fa-clock"></i> ${item.created_at} | por ${item.user_name || 'Sistema'}
                        </div>
                    </div>
                    ${["diretor", "coordenador", "opp"].includes(this.currentUser?.role?.toLowerCase()) ? `
                        <button class="btn-toolbar btn-restore" data-id="${item.id}" style="font-size: 11px; padding: 4px 8px;">
                            <i class="fa-solid fa-rotate-left"></i> Restaurar
                        </button>
                    ` : ""}
                `;

                row.querySelector(".btn-restore")?.addEventListener("click", () => {
                    this.restoreHistoryItem(item.id);
                });

                list.appendChild(row);
            });
        } catch (err) {
            list.innerHTML = `<div style="color: #EF4444; padding: 20px;">Falha ao obter histórico: ${err.message}</div>`;
        }
    }

    async restoreHistoryItem(historyId) {
        if (!confirm("Deseja restaurar esta versão do calendário? As alterações posteriores serão revertidas.")) {
            return;
        }

        try {
            const res = await window.apiService.restoreHistory(this.calendar.id, historyId);
            this.calendar = res.calendar;
            this.renderCalendar();
            document.getElementById("modalHistory")?.classList.remove("active");
            this.showToast("Versão histórica restaurada com sucesso!", "success");
        } catch (err) {
            this.showToast("Erro ao restaurar: " + err.message, "error");
        }
    }

    toggleFilterModal() {
        const categories = this.calendar?.categories || [];
        const options = ["1. Todas", ...categories.map((category, index) => `${index + 2}. ${category.title}`)].join("\n");
        const selected = prompt(`Filtrar por categoria:\n${options}\n\nDigite o número desejado:`, "1");
        const index = Number(selected) - 2;
        this.filterCategory = selected === "1" || !Number.isInteger(index) || !categories[index]
            ? "all"
            : String(categories[index].id);
        this.renderSummaryCards();
        this.showToast("Filtro aplicado!", "info");
    }

    exportPdf() {
        if (!this.calendar) return;
        window.open(`/api/export/calendar/${this.calendar.id}/pdf`, "_blank");
    }

    exportJson() {
        if (!this.calendar) return;
        window.location.href = `/api/export/calendar/${this.calendar.id}/json`;
    }

    showToast(message, type = "info") {
        const container = document.getElementById("toastContainer");
        if (!container) return;

        const toast = document.createElement("div");
        toast.className = `toast toast-${type}`;
        
        let icon = "fa-circle-info";
        if (type === "success") icon = "fa-circle-check";
        if (type === "error") icon = "fa-triangle-exclamation";

        toast.innerHTML = `<i class="fa-solid ${icon}"></i> <span>${message}</span>`;
        container.appendChild(toast);

        setTimeout(() => {
            toast.style.opacity = "0";
            toast.style.transition = "opacity 0.3s";
            setTimeout(() => toast.remove(), 300);
        }, 3500);
    }
}
