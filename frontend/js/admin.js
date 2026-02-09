requireAuth();

// Initialize mobile menu
function initMobileMenu() {
  const menuToggle = document.getElementById('menuToggle');
  const closeMenu = document.getElementById('closeMenu');
  const mobileMenuOverlay = document.getElementById('mobileMenuOverlay');
  const mobileMenu = document.getElementById('mobileMenu');
  const mobileLogoutBtn = document.getElementById('mobileLogoutBtn');
  
  if (!menuToggle || !closeMenu || !mobileMenuOverlay || !mobileMenu || !mobileLogoutBtn) {
    console.error('Mobile menu elements not found');
    return;
  }
  
  // Toggle mobile menu
  function toggleMenu() {
    const isActive = menuToggle.classList.toggle('active');
    mobileMenu.classList.toggle('active');
    mobileMenuOverlay.classList.toggle('active');
    document.body.style.overflow = isActive ? 'hidden' : '';
  }
  
  // Close menu
  function closeMobileMenu() {
    menuToggle.classList.remove('active');
    mobileMenu.classList.remove('active');
    mobileMenuOverlay.classList.remove('active');
    document.body.style.overflow = '';
  }
  
  // Event listeners
  menuToggle.addEventListener('click', toggleMenu);
  closeMenu.addEventListener('click', closeMobileMenu);
  mobileMenuOverlay.addEventListener('click', closeMobileMenu);
  
  // Close menu when clicking on a link
  mobileMenu.querySelectorAll('.mobile-nav-links a').forEach(link => {
    link.addEventListener('click', (e) => {
      if (link.href === '#' || link.getAttribute('href') === 'javascript:void(0)') {
        e.preventDefault();
        return;
      }
      setTimeout(closeMobileMenu, 300);
    });
  });
  
  // Mobile logout button
  mobileLogoutBtn.addEventListener('click', (e) => {
    e.preventDefault();
    closeMobileMenu();
    if (confirm("Are you sure you want to logout?")) {
      logout();
    }
  });
  
  // Close menu on escape key
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && mobileMenu.classList.contains('active')) {
      closeMobileMenu();
    }
  });
  
  // Prevent body scroll when menu is open (touch devices)
  mobileMenu.addEventListener('touchmove', (e) => {
    if (mobileMenu.scrollHeight > mobileMenu.clientHeight) {
      return;
    }
    e.preventDefault();
  }, { passive: false });
}

// Initialize mobile menu on DOM load
document.addEventListener('DOMContentLoaded', initMobileMenu);

async function load() {
  try {
    const user = await me();
    
    // Update mobile user info
    const mobileWho = document.getElementById('mobileWho');
    if (mobileWho) {
      mobileWho.textContent = `${user.name} (${user.role})`;
    }
    
    if (user.role !== "ADMIN") {
      alert("Admin access required");
      window.location.href = "dashboard.html";
      return;
    }

    await loadUsers();
    await loadProducts();
  } catch (error) {
    console.error("Failed to load admin page:", error);
    alert("Failed to load admin dashboard. Please refresh the page.");
  }
}

async function loadUsers() {
  try {
    const users = await apiFetch("/admin/users");
    const tbody = document.getElementById("usersBody");
    tbody.innerHTML = "";

    if (users.length === 0) {
      tbody.innerHTML = `
        <tr class="empty-row">
          <td colspan="4">
            <div class="empty-state">
              <div class="empty-state__icon">👤</div>
              <div class="empty-state__message">No users found</div>
            </div>
          </td>
        </tr>
      `;
      return;
    }

    for (const u of users) {
      const roleClass = u.role === "ADMIN" ? "badge--success" : "badge--info";
      const row = document.createElement("tr");
      row.className = "user-row";
      row.innerHTML = `
        <td class="user-name">
          <div class="user-name__primary">${u.name}</div>
          <div class="user-name__id">ID: ${u.id}</div>
        </td>
        <td class="user-email">${u.email}</td>
        <td class="user-role">
          <span class="badge ${roleClass}">${u.role}</span>
        </td>
        <td class="user-created">
          <div class="user-created__date">${new Date(
            u.created_at
          ).toLocaleDateString()}</div>
          <div class="user-created__time">${new Date(
            u.created_at
          ).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}</div>
        </td>
      `;
      tbody.appendChild(row);
    }
  } catch (error) {
    console.error("Failed to load users:", error);
    alert("Failed to load users. Please try again.");
  }
}

async function loadProducts() {
  try {
    const items = await apiFetch("/admin/products");
    const tbody = document.getElementById("productsBody");
    tbody.innerHTML = "";

    if (items.length === 0) {
      tbody.innerHTML = `
        <tr class="empty-row">
          <td colspan="5">
            <div class="empty-state">
              <div class="empty-state__icon">📦</div>
              <div class="empty-state__message">No tracked products found</div>
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

      const row = document.createElement("tr");
      row.className = "admin-product-row";
      row.innerHTML = `
        <td class="admin-product-user">
          <div class="admin-product-user__id">User ID: ${p.user_id}</div>
          <div class="admin-product-user__email">${p.user_email || ""}</div>
        </td>
        <td class="admin-product-info">
          <div class="admin-product-info__title"><b>${p.title || "Untitled"}</b></div>
          <div class="admin-product-info__meta">
            <span class="admin-product-info__platform">${p.platform.toUpperCase()}</span>
            <span class="admin-product-info__divider">•</span>
            <a href="${p.url}" target="_blank" class="admin-product-info__link">Open</a>
          </div>
        </td>
        <td class="admin-product-price">${fmtMoney(p.current_price, p.currency)}</td>
        <td class="admin-product-status">
          <span class="badge ${statusClass}">${p.status}</span>
          ${
            p.blocked_reason
              ? `<div class="admin-product-status__reason">${p.blocked_reason}</div>`
              : ""
          }
        </td>
        <td class="admin-product-actions">
          <button class="action-button button--secondary" data-recheck="${p.id}">Force Recheck</button>
        </td>
      `;
      tbody.appendChild(row);
    }

    // Add event listeners for recheck buttons
    tbody.querySelectorAll("button[data-recheck]").forEach((btn) => {
      btn.addEventListener("click", async () => {
        const id = btn.getAttribute("data-recheck");
        const originalText = btn.textContent;
        btn.textContent = "Rechecking...";
        btn.disabled = true;

        try {
          await apiFetch(`/admin/recheck/${id}`, { method: "POST" });
          alert("Recheck queued successfully. The system will process it shortly.");
          await loadProducts();
        } catch (error) {
          alert("Failed to queue recheck: " + error.message);
        } finally {
          btn.textContent = originalText;
          btn.disabled = false;
        }
      });
    });
  } catch (error) {
    console.error("Failed to load products:", error);
    alert("Failed to load products. Please try again.");
  }
}

document.getElementById("logoutBtn").addEventListener("click", (e) => {
  e.preventDefault();
  if (confirm("Are you sure you want to logout?")) {
    logout();
  }
});

// Load data on page load
load().catch((error) => {
  console.error("Failed to load admin page:", error);
  alert("Failed to load admin dashboard. Please refresh the page.");
});