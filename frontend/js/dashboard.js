// js/dashboard.js
// Dashboard functionality with toast notifications, confirmation modal, mobile menu,
// and Track-by-Request feature (best-effort search + user selection) + Delete Request.

requireAuth();

/* ---------------------------
   Mobile Menu
---------------------------- */
function initMobileMenu() {
  const menuToggle = document.getElementById("menuToggle");
  const closeMenu = document.getElementById("closeMenu");
  const mobileMenuOverlay = document.getElementById("mobileMenuOverlay");
  const mobileMenu = document.getElementById("mobileMenu");
  const mobileLogoutBtn = document.getElementById("mobileLogoutBtn");

  if (!menuToggle || !closeMenu || !mobileMenuOverlay || !mobileMenu || !mobileLogoutBtn) {
    console.warn("Some mobile menu elements not found, skipping mobile menu initialization");
    return;
  }

  function toggleMenu() {
    const isActive = menuToggle.classList.toggle("active");
    mobileMenu.classList.toggle("active");
    mobileMenuOverlay.classList.toggle("active");
    document.body.style.overflow = isActive ? "hidden" : "";
  }

  function closeMobileMenu() {
    menuToggle.classList.remove("active");
    mobileMenu.classList.remove("active");
    mobileMenuOverlay.classList.remove("active");
    document.body.style.overflow = "";
  }

  menuToggle.addEventListener("click", toggleMenu);
  closeMenu.addEventListener("click", closeMobileMenu);
  mobileMenuOverlay.addEventListener("click", closeMobileMenu);

  mobileMenu.querySelectorAll(".mobile-nav-links a").forEach((link) => {
    link.addEventListener("click", (e) => {
      if (link.id === "mobileAdminLink" && link.style.display === "none") {
        e.preventDefault();
        return;
      }
      setTimeout(closeMobileMenu, 300);
    });
  });

  mobileLogoutBtn.addEventListener("click", async (e) => {
    e.preventDefault();
    closeMobileMenu();

    const confirmed = await confirmationModal.show({
      title: "Logout",
      message: "Are you sure you want to logout from your account?",
      confirmText: "Logout",
      cancelText: "Stay",
      type: "warning",
    });

    if (confirmed) {
      toast.info("Logging you out...", { duration: 1500, showProgress: true });
      setTimeout(() => logout(), 1500);
    }
  });

  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && mobileMenu.classList.contains("active")) {
      closeMobileMenu();
    }
  });

  mobileMenu.addEventListener(
    "touchmove",
    (e) => {
      if (mobileMenu.scrollHeight > mobileMenu.clientHeight) return;
      e.preventDefault();
    },
    { passive: false }
  );
}

document.addEventListener("DOMContentLoaded", initMobileMenu);

/* ---------------------------
   Helpers
---------------------------- */
function escapeHtml(str) {
  return String(str || "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function safeDate(d) {
  try {
    const dt = new Date(d);
    return isNaN(dt.getTime()) ? null : dt;
  } catch {
    return null;
  }
}

/* ---------------------------
   Load Dashboard
---------------------------- */
async function load() {
  try {
    const user = await me();

    const whoElement = document.getElementById("who");
    if (whoElement) whoElement.textContent = `${user.name} (${user.role})`;

    const mobileWhoElement = document.getElementById("mobileWho");
    if (mobileWhoElement) mobileWhoElement.textContent = `${user.name} (${user.role})`;

    if (user.role === "ADMIN") {
      const adminLink = document.getElementById("adminLink");
      const mobileAdminLink = document.getElementById("mobileAdminLink");
      if (adminLink) adminLink.style.display = "inline-flex";
      if (mobileAdminLink) mobileAdminLink.style.display = "flex";
    }

    toast.info(`Welcome back, ${user.name}!`, { duration: 3000, showProgress: true });

    await loadProducts();
    await loadNotifications();
    await loadRequests();
  } catch (error) {
    console.error("Failed to load dashboard:", error);
    toast.error("Failed to load dashboard data. Please refresh the page.", {
      duration: 5000,
      showProgress: true,
    });
  }
}

/* ---------------------------
   Products
---------------------------- */
async function loadProducts() {
  try {
    const items = await apiFetch("/products");
    const tbody = document.getElementById("productsBody");
    if (!tbody) return;

    tbody.innerHTML = "";

    if (!items || items.length === 0) {
      tbody.innerHTML = `
        <tr class="empty-row">
          <td colspan="5">
            <div class="empty-state">
              <div class="empty-state__icon">📦</div>
              <div class="empty-state__message">No products tracked yet</div>
              <div class="empty-state__hint">Add your first product using the form above</div>
            </div>
          </td>
        </tr>
      `;
      return;
    }

    for (const p of items) {
      const statusClass =
        p.status === "blocked"
          ? "badge--error"
          : p.status === "pending"
          ? "badge--warning"
          : p.status === "active"
          ? "badge--success"
          : "badge--info";

      const lastChecked = p.last_checked ? safeDate(p.last_checked) : null;

      const row = document.createElement("tr");
      row.className = "product-row";
      row.innerHTML = `
        <td class="product-info">
          <div class="product-title"><b>${escapeHtml(p.title || "Untitled")}</b></div>
          <div class="product-meta">
            <span class="product-platform">${escapeHtml((p.platform || "").toUpperCase())}</span>
            <span class="product-divider">•</span>
            <a href="${escapeHtml(p.url)}" target="_blank" class="product-link" rel="noopener">Open product page</a>
          </div>
        </td>
        <td class="product-price">${fmtMoney(p.current_price, p.currency)}</td>
        <td class="product-status">
          <span class="badge ${statusClass}">${escapeHtml(p.status || "—")}</span>
        </td>
        <td class="product-checked">
          <div class="last-checked">${lastChecked ? lastChecked.toLocaleDateString() : "—"}</div>
          <div class="last-checked-time">${
            lastChecked
              ? lastChecked.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })
              : ""
          }</div>
        </td>
        <td class="product-actions">
          <div class="actions">
            <button class="action-button button--secondary" data-view="${p.id}">View</button>
            <button class="action-button button--danger" data-del="${p.id}">Delete</button>
          </div>
        </td>
      `;
      tbody.appendChild(row);
    }

    tbody.querySelectorAll("button[data-view]").forEach((btn) => {
      btn.addEventListener("click", () => {
        const id = btn.getAttribute("data-view");
        window.location.href = `product.html?id=${encodeURIComponent(id)}`;
      });
    });

    tbody.querySelectorAll("button[data-del]").forEach((btn) => {
      btn.addEventListener("click", async () => {
        const id = btn.getAttribute("data-del");
        const productRow = btn.closest("tr");
        const productTitle =
          productRow?.querySelector(".product-title b")?.textContent || "Product";

        const confirmed = await confirmationModal.show({
          title: "Delete Product",
          message: `Are you sure you want to delete "${productTitle}"? This action cannot be undone.`,
          confirmText: "Delete",
          cancelText: "Cancel",
          type: "danger",
        });
        if (!confirmed) return;

        const originalText = btn.textContent;
        btn.textContent = "Deleting...";
        btn.disabled = true;

        try {
          await apiFetch(`/products/${id}`, { method: "DELETE" });
          toast.success(`✓ "${productTitle}" deleted successfully`, { duration: 3000, showProgress: true });
          await loadProducts();
        } catch (err) {
          toast.error(`Failed to delete "${productTitle}": ${err.message}`, { duration: 5000, showProgress: true });
        } finally {
          btn.textContent = originalText;
          btn.disabled = false;
        }
      });
    });
  } catch (error) {
    console.error("Failed to load products:", error);
    toast.error("Failed to load products. Please try again.", { duration: 4000, showProgress: true });
  }
}

/* ---------------------------
   Notifications - UPDATED
---------------------------- */
async function loadNotifications() {
  try {
    const items = await apiFetch("/notifications");
    const box = document.getElementById("notifBox");
    if (!box) return;

    box.innerHTML = "";

    if (!items || items.length === 0) {
      box.innerHTML = `
        <div class="empty-state">
          <div class="empty-state__icon">🔔</div>
          <div class="empty-state__message">No notifications yet</div>
          <div class="empty-state__hint">Price drop alerts will appear here</div>
        </div>
      `;
      return;
    }

    // Filter out email notifications - only show in_app
    const inAppNotifications = items.filter(n => n.channel === "in_app");
    
    if (inAppNotifications.length === 0) {
      box.innerHTML = `
        <div class="empty-state">
          <div class="empty-state__icon">🔔</div>
          <div class="empty-state__message">No in-app notifications</div>
          <div class="empty-state__hint">Email notifications are sent to your inbox</div>
        </div>
      `;
      return;
    }

    for (const n of inAppNotifications.slice(0, 5)) {
      const notificationClass =
        n.status === "sent"
          ? "notification--success"
          : n.status === "failed"
          ? "notification--error"
          : n.status === "pending"
          ? "notification--warning"
          : "notification--info";

      const notification = document.createElement("div");
      notification.className = `notification ${notificationClass}`;

      const d = safeDate(n.sent_at);
      const dateText = d ? d.toLocaleDateString() : "";
      const timeText = d ? d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }) : "";

      // Extract URL from message if present
      const urlMatch = n.message?.match(/https?:\/\/[^\s]+/);
      const productUrl = urlMatch ? urlMatch[0] : null;
      
      // Remove URL from message display
      let displayMessage = n.message || "";
      if (productUrl) {
        displayMessage = displayMessage.replace(productUrl, '').trim();
      }

      notification.innerHTML = `
        <div class="notification__header">
          <span class="notification__time">${escapeHtml(dateText)} • ${escapeHtml(timeText)}</span>
        </div>
        <div class="notification__title">${escapeHtml(n.type || "Price Alert")}</div>
        <div class="notification__message">${escapeHtml(displayMessage)}</div>
        ${productUrl ? `
          <div class="notification__actions">
            <a href="${escapeHtml(productUrl)}" target="_blank" rel="noopener" class="notification__view-button">
              View Product
            </a>
          </div>
        ` : ''}
      `;
      box.appendChild(notification);
    }

    // Count only in-app notifications for the "View all" link
    if (inAppNotifications.length > 5) {
      const viewAll = document.createElement("div");
      viewAll.className = "view-all-notifications";
      viewAll.innerHTML = `<a href="notifications.html" class="small">View all ${inAppNotifications.length} notifications →</a>`;
      box.appendChild(viewAll);
    }
  } catch (error) {
    console.error("Failed to load notifications:", error);
  }
}

/* ---------------------------
   Track by URL
---------------------------- */
document.getElementById("trackForm")?.addEventListener("submit", async (e) => {
  e.preventDefault();

  const urlEl = document.getElementById("url");
  const platformEl = document.getElementById("platform");

  const url = urlEl?.value?.trim();
  const platform = platformEl?.value;

  if (!url) {
    toast.error("Please enter a product URL", { duration: 4000, showProgress: true });
    return;
  }

  try {
    new URL(url);
  } catch {
    toast.error("Please enter a valid URL", { duration: 4000, showProgress: true });
    return;
  }

  const submitBtn = e.target.querySelector('button[type="submit"]');
  const originalText = submitBtn.textContent;
  submitBtn.textContent = "Tracking...";
  submitBtn.disabled = true;

  try {
    await apiFetch("/products/track", { method: "POST", body: JSON.stringify({ url, platform }) });
    if (urlEl) urlEl.value = "";
    toast.success("✓ Product added successfully!", { duration: 4000, showProgress: true });
    await loadProducts();
  } catch (err) {
    toast.error(`Tracking failed: ${err.message}`, { duration: 5000, showProgress: true });
  } finally {
    submitBtn.textContent = originalText;
    submitBtn.disabled = false;
  }
});

/* ---------------------------
   Track by Request
---------------------------- */
async function createRequest(payload) {
  return apiFetch("/requests", { method: "POST", body: JSON.stringify(payload) });
}

async function fetchRequests() {
  return apiFetch("/requests", { method: "GET" });
}

async function fetchRequestDetail(id) {
  return apiFetch(`/requests/${id}`, { method: "GET" });
}

async function selectRequestCandidate(requestId, url) {
  return apiFetch(`/requests/${requestId}/select`, {
    method: "POST",
    body: JSON.stringify({ url }),
  });
}

async function deleteRequest(requestId) {
  return apiFetch(`/requests/${requestId}`, { method: "DELETE" });
}

async function loadRequests() {
  const listEl = document.getElementById("requestsList");
  if (!listEl) return;

  try {
    const items = await fetchRequests();
    renderRequests(items);
  } catch (e) {
    console.error("Failed to load requests:", e);
    listEl.innerHTML = `<div class="small">Failed to load requests. Try refresh.</div>`;
  }
}

function renderRequests(items) {
  const el = document.getElementById("requestsList");
  if (!el) return;

  if (!items || items.length === 0) {
    el.innerHTML = `
      <div class="empty-state">
        <div class="empty-state__icon">🧾</div>
        <div class="empty-state__message">No requests yet</div>
        <div class="empty-state__hint">Submit a request above to see options</div>
      </div>
    `;
    return;
  }

  el.innerHTML = items
    .map((r) => {
      const status = escapeHtml(r.status || "—");
      const rc = Number(r.result_count || 0);
      const mp = r.max_price ? `<span class="badge">≤ ${escapeHtml(r.max_price)}</span>` : "";

      const blocked = r.blocked_reason ? `<div class="request-row__notice">${escapeHtml(r.blocked_reason)}</div>` : "";
      const err = r.error_message ? `<div class="request-row__notice">${escapeHtml(r.error_message)}</div>` : "";

      return `
        <div class="request-row">
          <div class="request-row__top">
            <div class="request-row__meta">
              <div class="request-row__title">
                <b>${escapeHtml((r.platform || "").toUpperCase())}</b> — ${escapeHtml(r.query)}
              </div>
              <div class="small">Status: <b>${status}</b> • Results: <b>${rc}</b> ${mp}</div>
              ${blocked}
              ${err}
            </div>

            <div class="request-row__actions">
              <button class="secondary view-req-btn" data-req-id="${escapeHtml(r.id)}">View</button>
              <button class="button--danger del-req-btn" data-req-id="${escapeHtml(r.id)}">Delete</button>
            </div>
          </div>
        </div>
      `;
    })
    .join("");

  document.querySelectorAll(".view-req-btn").forEach((btn) => {
    btn.addEventListener("click", async () => {
      const id = btn.getAttribute("data-req-id");
      btn.disabled = true;
      const prev = btn.textContent;
      btn.textContent = "Loading...";

      try {
        const detail = await fetchRequestDetail(id);
        showRequestResultsModal(detail);
      } catch (e) {
        toast.error(e?.message || "Failed to load request detail", { duration: 4000, showProgress: true });
      } finally {
        btn.textContent = prev;
        btn.disabled = false;
      }
    });
  });

  document.querySelectorAll(".del-req-btn").forEach((btn) => {
    btn.addEventListener("click", async () => {
      const id = btn.getAttribute("data-req-id");

      const row = btn.closest(".request-row");
      const title = row?.querySelector(".request-row__title")?.textContent?.trim() || "this request";

      const confirmed = await confirmationModal.show({
        title: "Delete Request",
        message: `Are you sure you want to delete "${escapeHtml(title)}"? This cannot be undone.`,
        confirmText: "Delete",
        cancelText: "Cancel",
        type: "danger",
      });

      if (!confirmed) return;

      const prev = btn.textContent;
      btn.textContent = "Deleting...";
      btn.disabled = true;

      try {
        await deleteRequest(id);
        toast.success("✓ Request deleted", { duration: 3000, showProgress: true });
        await loadRequests();
      } catch (e) {
        toast.error(e?.message || "Failed to delete request", { duration: 4500, showProgress: true });
      } finally {
        btn.textContent = prev;
        btn.disabled = false;
      }
    });
  });
}

function showRequestResultsModal(detail) {
  const results = detail.results || [];

  const modalHtml = `
    <div class="req-modal" id="reqModalBackdrop">
      <div class="req-modal__overlay" id="reqModalOverlay"></div>

      <div class="req-modal__panel">
        <div class="req-modal__header">
          <div>
            <div class="req-modal__title">
              Results — ${escapeHtml(detail.query)} (${escapeHtml(detail.platform)})
            </div>

            <div class="req-modal__status">
              Status: <b>${escapeHtml(detail.status || "—")}</b>
            </div>

            ${detail.blocked_reason ? `<div class="req-danger-text" style="margin-top:8px;">${escapeHtml(detail.blocked_reason)}</div>` : ""}
            ${detail.error_message ? `<div class="req-danger-text" style="margin-top:8px;">${escapeHtml(detail.error_message)}</div>` : ""}
          </div>

          <button id="closeReqModal" class="secondary">Close</button>
        </div>

        <div class="req-modal__body">
          <div class="req-cards">
            ${
              results.length
                ? results
                    .map((c) => {
                      const title = escapeHtml(c.title || "(no title)");
                      const priceText = c.price
                        ? `${escapeHtml(c.price)} ${escapeHtml(c.currency || "")}`
                        : "Price not detected";
                      const openUrl = escapeHtml(c.url);

                      return `
                        <div class="req-card">
                          <div class="req-card__title">${title}</div>
                          <div class="req-card__price">${escapeHtml(priceText)}</div>

                          <div class="req-card__actions">
                            <a class="secondary" href="${openUrl}" target="_blank" rel="noopener">Open</a>
                            <button class="track-candidate-btn" data-url="${openUrl}" data-req="${escapeHtml(detail.id)}">
                              Track This
                            </button>
                          </div>
                        </div>
                      `;
                    })
                    .join("")
                : `<div class="req-muted">No results yet. If blocked, the system will retry later. Click Refresh and check again.</div>`
            }
          </div>
        </div>
      </div>
    </div>
  `;

  document.body.insertAdjacentHTML("beforeend", modalHtml);

  const closeBtn = document.getElementById("closeReqModal");
  const overlay = document.getElementById("reqModalOverlay");

  function close() {
    const m = document.getElementById("reqModalBackdrop");
    if (m) m.remove();
  }

  closeBtn?.addEventListener("click", close);
  overlay?.addEventListener("click", close);

  document.querySelectorAll(".track-candidate-btn").forEach((btn) => {
    btn.addEventListener("click", async () => {
      const url = btn.getAttribute("data-url");
      const requestId = btn.getAttribute("data-req");

      const confirmed = await confirmationModal.show({
        title: "Track selected listing",
        message: "This will add the selected listing to your tracked products. Continue?",
        confirmText: "Track",
        cancelText: "Cancel",
        type: "info",
      });

      if (!confirmed) return;

      const prev = btn.textContent;
      btn.textContent = "Tracking...";
      btn.disabled = true;

      try {
        await selectRequestCandidate(requestId, url);
        toast.success("✓ Now tracking selected listing!", { duration: 3500, showProgress: true });
        close();
        await loadProducts();
        await loadRequests();
      } catch (e) {
        toast.error(e?.message || "Failed to track selected listing", { duration: 4500, showProgress: true });
      } finally {
        btn.textContent = prev;
        btn.disabled = false;
      }
    });
  });
}

/* Request form submit */
document.getElementById("requestForm")?.addEventListener("submit", async (e) => {
  e.preventDefault();

  const platform = document.getElementById("reqPlatform")?.value;
  const queryEl = document.getElementById("reqQuery");
  const maxEl = document.getElementById("reqMaxPrice");

  const query = queryEl?.value?.trim();
  const maxPriceRaw = maxEl?.value?.trim();
  const max_price = maxPriceRaw ? Number(maxPriceRaw) : null;

  if (!query || query.length < 3) {
    toast.error("Please enter a longer request (at least 3 characters)", { duration: 4000, showProgress: true });
    return;
  }

  const submitBtn = e.target.querySelector('button[type="submit"]');
  const originalText = submitBtn.textContent;
  submitBtn.textContent = "Submitting...";
  submitBtn.disabled = true;

  try {
    await createRequest({ platform, query, max_price });

    if (queryEl) queryEl.value = "";
    if (maxEl) maxEl.value = "";

    toast.success("✓ Request submitted. Check back for results shortly.", { duration: 4000, showProgress: true });
    await loadRequests();
  } catch (err) {
    toast.error(err?.message || "Failed to submit request", { duration: 5000, showProgress: true });
  } finally {
    submitBtn.textContent = originalText;
    submitBtn.disabled = false;
  }
});

/* Refresh requests button */
document.getElementById("refreshRequestsBtn")?.addEventListener("click", async () => {
  toast.info("Refreshing requests...", { duration: 1500, showProgress: true });
  await loadRequests();
});

/* ---------------------------
   Desktop logout
---------------------------- */
document.getElementById("logoutBtn")?.addEventListener("click", async (e) => {
  e.preventDefault();

  const confirmed = await confirmationModal.show({
    title: "Logout",
    message: "Are you sure you want to logout from your account?",
    confirmText: "Logout",
    cancelText: "Stay",
    type: "warning",
  });

  if (confirmed) {
    toast.info("Logging you out...", { duration: 1500, showProgress: true });
    setTimeout(() => logout(), 1500);
  }
});

/* ---------------------------
   Start
---------------------------- */
load().catch((err) => {
  console.error("Failed to load dashboard:", err);
  toast.error("Failed to load dashboard data. Please refresh the page.", { duration: 5000, showProgress: true });
});