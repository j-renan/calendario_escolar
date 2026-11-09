/**
 * Antigravity - API Service Client
 * Handles JWT storage, headers, and endpoints.
 */

class ApiService {
    constructor() {
        this.tokenKey = "senai_auth_token";
        this.userKey = "senai_user_data";
    }

    getToken() {
        return localStorage.getItem(this.tokenKey);
    }

    setAuth(token, user) {
        if (token) localStorage.setItem(this.tokenKey, token);
        if (user) localStorage.setItem(this.userKey, JSON.stringify(user));
    }

    clearAuth() {
        localStorage.removeItem(this.tokenKey);
        localStorage.removeItem(this.userKey);
    }

    getCurrentUser() {
        const u = localStorage.getItem(this.userKey);
        return u ? JSON.parse(u) : null;
    }

    async request(url, options = {}) {
        const headers = {
            "Content-Type": "application/json",
            ...(options.headers || {})
        };

        const token = this.getToken();
        if (token) {
            headers["Authorization"] = `Bearer ${token}`;
        }

        const config = {
            ...options,
            headers
        };

        try {
            const res = await fetch(url, config);
            const data = await res.json();
            if (!res.ok) {
                if (res.status === 401 && !url.includes("/login")) {
                    // Token expired or invalid
                    this.clearAuth();
                }
                throw new Error(data.error || `Erro na requisição HTTP (${res.status})`);
            }
            return data;
        } catch (err) {
            throw err;
        }
    }

    // Auth
    async login(email, password) {
        const data = await this.request("/api/auth/login", {
            method: "POST",
            body: JSON.stringify({ email, password })
        });
        if (data.token) {
            this.setAuth(data.token, data.user);
        }
        return data;
    }

    async register(name, email, password, role = "coordenador") {
        const data = await this.request("/api/auth/register", {
            method: "POST",
            body: JSON.stringify({ name, email, password, role })
        });
        if (data.token) {
            this.setAuth(data.token, data.user);
        }
        return data;
    }

    async getProfile() {
        return this.request("/api/auth/me");
    }

    async getCalendars() {
        return this.request("/api/calendars");
    }

    async getCalendar(calendarId) {
        return this.request(`/api/calendars/${calendarId}`);
    }

    async createCalendar(year, semester, categoryIds) {
        return this.request("/api/calendars", {
            method: "POST",
            body: JSON.stringify({ year, semester, category_ids: categoryIds })
        });
    }

    async getCategories(activeOnly = false) {
        return this.request(`/api/categories?active_only=${activeOnly}`);
    }

    async createCategory(name) {
        return this.request("/api/categories", {
            method: "POST",
            body: JSON.stringify({ name })
        });
    }

    async updateCategory(id, name, isActive) {
        return this.request(`/api/categories/${id}`, {
            method: "PUT",
            body: JSON.stringify({ name, is_active: isActive })
        });
    }

    async deleteCategory(id) {
        return this.request(`/api/categories/${id}`, { method: "DELETE" });
    }

    async getUsers() {
        return this.request("/api/users");
    }

    async createUser(payload) {
        return this.request("/api/users", {
            method: "POST",
            body: JSON.stringify(payload)
        });
    }

    async updateUser(id, payload) {
        return this.request(`/api/users/${id}`, {
            method: "PUT",
            body: JSON.stringify(payload)
        });
    }

    async deleteUser(id) {
        return this.request(`/api/users/${id}`, { method: "DELETE" });
    }

    // Calendars
    async getActiveCalendar() {
        return this.request("/api/calendars/active");
    }

    async saveDraft(calendarId, payload) {
        return this.request(`/api/calendars/${calendarId}/draft`, {
            method: "PUT",
            body: JSON.stringify(payload)
        });
    }

    async publishCalendar(calendarId) {
        return this.request(`/api/calendars/${calendarId}/publish`, {
            method: "POST"
        });
    }

    async signApproval(calendarId, directorName) {
        return this.request(`/api/calendars/${calendarId}/sign`, {
            method: "POST",
            body: JSON.stringify({ director_name: directorName })
        });
    }

    async updateCalendarNotes(calendarId, payload) {
        return this.request(`/api/calendars/${calendarId}/notes`, {
            method: "PUT",
            body: JSON.stringify(payload)
        });
    }

    async updateDay(
        calendarId,
        monthIndex,
        day,
        dayType,
        title,
        milestone = null,
        categoryIds = [],
        compensationFor = null
    ) {
        return this.request(`/api/calendars/${calendarId}/day`, {
            method: "POST",
            body: JSON.stringify({
                month_index: monthIndex,
                day: day,
                day_type: dayType,
                title: title,
                milestone,
                category_ids: categoryIds,
                compensation_for: compensationFor
            })
        });
    }

    async deleteCalendar(calendarId) {
        return this.request(`/api/calendars/${calendarId}`, { method: "DELETE" });
    }

    async getHistory(calendarId) {
        return this.request(`/api/calendars/${calendarId}/history`);
    }

    async restoreHistory(calendarId, historyId) {
        return this.request(`/api/calendars/${calendarId}/history/${historyId}/restore`, {
            method: "POST"
        });
    }
}

window.apiService = new ApiService();
