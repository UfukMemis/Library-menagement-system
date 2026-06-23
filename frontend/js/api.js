const API_BASE = window.location.port === "8080" ? "/api" : "http://localhost:8000";

function getToken() {
  return localStorage.getItem("lms_token");
}

function setToken(token) {
  if (token) localStorage.setItem("lms_token", token);
  else localStorage.removeItem("lms_token");
}

async function apiRequest(path, options = {}) {
  const headers = { ...(options.headers || {}) };
  const token = getToken();
  if (token) headers.Authorization = `Bearer ${token}`;

  const isForm = options.body instanceof FormData;
  if (!isForm && options.body && !headers["Content-Type"]) {
    headers["Content-Type"] = "application/json";
  }

  const response = await fetch(`${API_BASE}${path}`, { ...options, headers });
  const text = await response.text();
  let data = null;
  if (text) {
    try {
      data = JSON.parse(text);
    } catch {
      data = text;
    }
  }

  if (!response.ok) {
    const detail = data?.detail || data || response.statusText;
    throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
  }
  return data;
}

export const api = {
  login(username, password) {
    const body = new FormData();
    body.append("username", username);
    body.append("password", password);
    return apiRequest("/auth/login", { method: "POST", body });
  },
  register(payload) {
    return apiRequest("/auth/register", { method: "POST", body: JSON.stringify(payload) });
  },
  logout() {
    return apiRequest("/auth/logout", { method: "POST" });
  },
  me() {
    return apiRequest("/auth/me");
  },
  getBooks(params = {}) {
    const query = new URLSearchParams(params).toString();
    return apiRequest(`/books?${query}`);
  },
  createBook(payload) {
    return apiRequest("/books", { method: "POST", body: JSON.stringify(payload) });
  },
  updateBook(isbn, payload) {
    return apiRequest(`/books/${encodeURIComponent(isbn)}`, {
      method: "PUT",
      body: JSON.stringify(payload),
    });
  },
  deleteBook(isbn) {
    return apiRequest(`/books/${encodeURIComponent(isbn)}`, { method: "DELETE" });
  },
  borrow(isbn) {
    return apiRequest("/borrow", { method: "POST", body: JSON.stringify({ isbn }) });
  },
  returnBook(transactionId) {
    return apiRequest("/return", {
      method: "POST",
      body: JSON.stringify({ transaction_id: transactionId }),
    });
  },
  getTransactions(params = {}) {
    const query = new URLSearchParams(params).toString();
    return apiRequest(`/transactions?${query}`);
  },
  createReservation(isbn) {
    return apiRequest("/reservations", { method: "POST", body: JSON.stringify({ isbn }) });
  },
  getReservations(params = {}) {
    const query = new URLSearchParams(params).toString();
    return apiRequest(`/reservations?${query}`);
  },
  cancelReservation(id) {
    return apiRequest(`/reservations/${id}/cancel`, { method: "POST" });
  },
  getReports() {
    return apiRequest("/reports");
  },
  getUsers(params = {}) {
    const query = new URLSearchParams(params).toString();
    return apiRequest(`/users?${query}`);
  },
};

export { getToken, setToken };
