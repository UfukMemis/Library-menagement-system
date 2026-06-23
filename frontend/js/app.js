import { api, getToken, setToken } from "./api.js";

const state = {
  user: null,
  editingIsbn: null,
  books: [],
};

const sections = {
  auth: document.getElementById("auth-section"),
  catalog: document.getElementById("catalog-section"),
  "my-account": document.getElementById("my-account-section"),
  "manage-books": document.getElementById("manage-books-section"),
  reports: document.getElementById("reports-section"),
};

function showMessage(containerId, text, type = "error") {
  const el = document.getElementById(containerId);
  if (!text) {
    el.innerHTML = "";
    return;
  }
  el.innerHTML = `<div class="message ${type}">${text}</div>`;
}

function badge(value) {
  return `<span class="badge ${value}">${String(value).replaceAll("_", " ")}</span>`;
}

function escapeHtml(text) {
  return String(text)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

function bookCoverHtml(isbn, title) {
  const src = `https://covers.openlibrary.org/b/isbn/${encodeURIComponent(isbn)}-S.jpg`;
  const initial = escapeHtml(title.trim().charAt(0).toUpperCase() || "?");
  return `
    <div class="book-cover" data-initial="${initial}">
      <img src="${src}" alt="Cover of ${escapeHtml(title)}" loading="lazy"
           onerror="this.remove(); this.parentElement.classList.add('book-cover--placeholder');" />
    </div>`;
}

function isStaff(role) {
  return role === "administrator" || role === "librarian";
}

function setView(view) {
  Object.entries(sections).forEach(([key, section]) => {
    section.classList.toggle("hidden", key !== view);
  });
  document.querySelectorAll("#main-nav button[data-view]").forEach((btn) => {
    btn.classList.toggle("active", btn.dataset.view === view);
  });
}

function updateShell() {
  const loggedIn = Boolean(state.user);
  document.getElementById("main-nav").classList.toggle("hidden", !loggedIn);
  sections.auth.classList.toggle("hidden", loggedIn);
  document.querySelectorAll(".staff-only").forEach((el) => {
    el.classList.toggle("hidden", !loggedIn || !isStaff(state.user?.role));
  });
  if (loggedIn) setView("catalog");
}

async function loadProfile() {
  const profile = document.getElementById("profile-box");
  profile.innerHTML = `
    <p><strong>${state.user.full_name}</strong> (${state.user.username})</p>
    <p>Email: ${state.user.email}</p>
    <p>Role: ${state.user.role}</p>
  `;
}

async function loadBooks() {
  showMessage("catalog-message");
  const params = {
    page: 1,
    page_size: 50,
    search: document.getElementById("search-input").value || undefined,
    author: document.getElementById("author-filter").value || undefined,
    publisher: document.getElementById("publisher-filter").value || undefined,
    year: document.getElementById("year-filter").value || undefined,
    available_only: document.getElementById("available-only").checked || undefined,
  };
  Object.keys(params).forEach((key) => params[key] === undefined && delete params[key]);

  try {
    const data = await api.getBooks(params);
    state.books = data.items;
    const tbody = document.getElementById("books-table");
    tbody.innerHTML = data.items
      .map((book) => {
        const canBorrow = state.user && book.available_copies > 0;
        const canReserve = state.user && book.available_copies === 0;
        return `
          <tr>
            <td>${book.isbn}</td>
            <td>${escapeHtml(book.title)}</td>
            <td class="book-cover-cell">${bookCoverHtml(book.isbn, book.title)}</td>
            <td>${escapeHtml(book.author)}</td>
            <td>${book.publisher || "-"}</td>
            <td>${book.publication_year || "-"}</td>
            <td>${badge(book.availability_status)} (${book.available_copies}/${book.total_copies})</td>
            <td class="card-actions">
              ${canBorrow ? `<button data-borrow="${book.isbn}">Borrow</button>` : ""}
              ${canReserve ? `<button data-reserve="${book.isbn}">Reserve</button>` : ""}
              ${
                isStaff(state.user?.role)
                  ? `<button data-edit-isbn="${book.isbn}">Edit</button>
                     <button data-delete="${book.isbn}">Delete</button>`
                  : ""
              }
            </td>
          </tr>`;
      })
      .join("");
  } catch (error) {
    showMessage("catalog-message", error.message);
  }
}

async function loadTransactions() {
  showMessage("transactions-message");
  try {
    const data = await api.getTransactions({ page: 1, page_size: 50 });
    document.getElementById("transactions-table").innerHTML = data.items
      .map(
        (tx) => `
        <tr>
          <td>${tx.transaction_id}</td>
          <td>${tx.book_title || tx.isbn}</td>
          <td>${tx.borrow_date}</td>
          <td>${tx.due_date}</td>
          <td>${tx.return_date || "-"}</td>
          <td>${badge(tx.status)}</td>
          <td>
            ${
              tx.status === "active" || tx.status === "overdue"
                ? `<button data-return="${tx.transaction_id}">Return</button>`
                : "-"
            }
          </td>
        </tr>`
      )
      .join("");
  } catch (error) {
    showMessage("transactions-message", error.message);
  }
}

async function loadReservations() {
  showMessage("reservations-message");
  try {
    const data = await api.getReservations({ page: 1, page_size: 50 });
    document.getElementById("reservations-table").innerHTML = data.items
      .map(
        (row) => `
        <tr>
          <td>${row.reservation_id}</td>
          <td>${row.book_title || row.isbn}</td>
          <td>${new Date(row.reservation_date).toLocaleString()}</td>
          <td>${badge(row.status)}</td>
          <td>
            ${
              row.status === "pending"
                ? `<button data-cancel-reservation="${row.reservation_id}">Cancel</button>`
                : "-"
            }
          </td>
        </tr>`
      )
      .join("");
  } catch (error) {
    showMessage("reservations-message", error.message);
  }
}

async function loadReports() {
  showMessage("reports-message");
  try {
    const data = await api.getReports();
    document.getElementById("reports-content").innerHTML = `
      <div class="grid two">
        <div class="panel">
          <h3>Most Borrowed Books</h3>
          <table>
            <thead><tr><th>Title</th><th>Author</th><th>Count</th></tr></thead>
            <tbody>
              ${data.most_borrowed_books
                .map((row) => `<tr><td>${row.title}</td><td>${row.author}</td><td>${row.borrow_count}</td></tr>`)
                .join("")}
            </tbody>
          </table>
        </div>
        <div class="panel">
          <h3>Active Users</h3>
          <table>
            <thead><tr><th>User</th><th>Name</th><th>Active Borrows</th></tr></thead>
            <tbody>
              ${data.active_users
                .map(
                  (row) =>
                    `<tr><td>${row.username}</td><td>${row.full_name}</td><td>${row.active_borrows}</td></tr>`
                )
                .join("")}
            </tbody>
          </table>
        </div>
      </div>
      <div class="panel">
        <h3>Monthly Borrowing Statistics</h3>
        <table>
          <thead><tr><th>Month</th><th>Borrows</th></tr></thead>
          <tbody>
            ${data.monthly_borrowing_statistics
              .map((row) => `<tr><td>${row.month}</td><td>${row.borrow_count}</td></tr>`)
              .join("")}
          </tbody>
        </table>
      </div>
      <div class="grid two">
        <div class="panel">
          <h3>Currently Borrowed</h3>
          <table>
            <thead><tr><th>Book</th><th>User</th><th>Due</th></tr></thead>
            <tbody>
              ${data.currently_borrowed_books
                .map(
                  (row) =>
                    `<tr><td>${row.book_title}</td><td>${row.username}</td><td>${row.due_date}</td></tr>`
                )
                .join("")}
            </tbody>
          </table>
        </div>
        <div class="panel">
          <h3>Overdue Books</h3>
          <table>
            <thead><tr><th>Book</th><th>User</th><th>Due</th></tr></thead>
            <tbody>
              ${data.overdue_books
                .map(
                  (row) =>
                    `<tr><td>${row.book_title}</td><td>${row.username}</td><td>${row.due_date}</td></tr>`
                )
                .join("")}
            </tbody>
          </table>
        </div>
      </div>`;
  } catch (error) {
    showMessage("reports-message", error.message);
  }
}

document.getElementById("login-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  showMessage("auth-message");
  try {
    const token = await api.login(
      document.getElementById("login-username").value,
      document.getElementById("login-password").value
    );
    setToken(token.access_token);
    state.user = await api.me();
    updateShell();
    await loadBooks();
  } catch (error) {
    showMessage("auth-message", error.message);
  }
});

document.getElementById("register-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  showMessage("auth-message");
  try {
    await api.register({
      username: document.getElementById("register-username").value,
      email: document.getElementById("register-email").value,
      full_name: document.getElementById("register-fullname").value,
      password: document.getElementById("register-password").value,
      role: "student",
    });
    showMessage("auth-message", "Registration successful. You can log in now.", "success");
  } catch (error) {
    showMessage("auth-message", error.message);
  }
});

document.getElementById("logout-btn").addEventListener("click", async () => {
  try {
    if (getToken()) await api.logout();
  } catch {
    /* ignore */
  }
  setToken(null);
  state.user = null;
  updateShell();
  setView("auth");
});

document.getElementById("main-nav").addEventListener("click", async (event) => {
  const view = event.target.dataset?.view;
  if (!view) return;
  setView(view);
  if (view === "catalog") await loadBooks();
  if (view === "my-account") {
    await loadProfile();
    await loadTransactions();
    await loadReservations();
  }
  if (view === "reports") await loadReports();
});

document.getElementById("search-btn").addEventListener("click", loadBooks);

document.getElementById("books-table").addEventListener("click", async (event) => {
  const borrowIsbn = event.target.dataset.borrow;
  const reserveIsbn = event.target.dataset.reserve;
  const deleteIsbn = event.target.dataset.delete;
  const editIsbn = event.target.dataset.editIsbn;

  try {
    if (borrowIsbn) {
      await api.borrow(borrowIsbn);
      showMessage("catalog-message", "Book borrowed successfully.", "success");
      await loadBooks();
    }
    if (reserveIsbn) {
      await api.createReservation(reserveIsbn);
      showMessage("catalog-message", "Reservation created.", "success");
    }
    if (deleteIsbn) {
      await api.deleteBook(deleteIsbn);
      showMessage("catalog-message", "Book deleted.", "success");
      await loadBooks();
    }
    if (editIsbn) {
      const book = state.books.find((item) => item.isbn === editIsbn);
      if (!book) return;
      state.editingIsbn = book.isbn;
      document.getElementById("book-isbn").value = book.isbn;
      document.getElementById("book-isbn").readOnly = true;
      document.getElementById("book-title").value = book.title;
      document.getElementById("book-author").value = book.author;
      document.getElementById("book-publisher").value = book.publisher || "";
      document.getElementById("book-year").value = book.publication_year || "";
      document.getElementById("book-copies").value = book.total_copies;
      setView("manage-books");
    }
  } catch (error) {
    showMessage("catalog-message", error.message);
  }
});

document.getElementById("transactions-table").addEventListener("click", async (event) => {
  const txId = event.target.dataset.return;
  if (!txId) return;
  try {
    await api.returnBook(Number(txId));
    showMessage("transactions-message", "Book returned.", "success");
    await loadTransactions();
    await loadBooks();
  } catch (error) {
    showMessage("transactions-message", error.message);
  }
});

document.getElementById("reservations-table").addEventListener("click", async (event) => {
  const reservationId = event.target.dataset.cancelReservation;
  if (!reservationId) return;
  try {
    await api.cancelReservation(Number(reservationId));
    showMessage("reservations-message", "Reservation cancelled.", "success");
    await loadReservations();
  } catch (error) {
    showMessage("reservations-message", error.message);
  }
});

document.getElementById("book-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  showMessage("manage-message");
  const payload = {
    isbn: document.getElementById("book-isbn").value.trim(),
    title: document.getElementById("book-title").value.trim(),
    author: document.getElementById("book-author").value.trim(),
    publisher: document.getElementById("book-publisher").value.trim() || null,
    publication_year: Number(document.getElementById("book-year").value) || null,
    total_copies: Number(document.getElementById("book-copies").value),
  };
  try {
    if (state.editingIsbn) {
      await api.updateBook(state.editingIsbn, {
        title: payload.title,
        author: payload.author,
        publisher: payload.publisher,
        publication_year: payload.publication_year,
        total_copies: payload.total_copies,
      });
      showMessage("manage-message", "Book updated.", "success");
    } else {
      await api.createBook(payload);
      showMessage("manage-message", "Book created.", "success");
    }
    resetBookForm();
    setView("catalog");
    await loadBooks();
  } catch (error) {
    showMessage("manage-message", error.message);
  }
});

document.getElementById("reset-book-form").addEventListener("click", resetBookForm);

function resetBookForm() {
  state.editingIsbn = null;
  document.getElementById("book-form").reset();
  document.getElementById("book-isbn").readOnly = false;
}

async function bootstrap() {
  if (!getToken()) {
    updateShell();
    return;
  }
  try {
    state.user = await api.me();
    updateShell();
    await loadBooks();
  } catch {
    setToken(null);
    updateShell();
  }
}

bootstrap();
