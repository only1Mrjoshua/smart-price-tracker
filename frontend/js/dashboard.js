requireAuth();

// Initialize mobile menu
function initMobileMenu() {
  const menuToggle = document.getElementById('menuToggle');
  const closeMenu = document.getElementById('closeMenu');
  const mobileMenuOverlay = document.getElementById('mobileMenuOverlay');
  const mobileMenu = document.getElementById('mobileMenu');
  const mobileLogoutBtn = document.getElementById('mobileLogoutBtn');
  const mobileAdminLink = document.getElementById('mobileAdminLink');
  
  // Check if elements exist
  if (!menuToggle || !closeMenu || !mobileMenuOverlay || !mobileMenu || !mobileLogoutBtn) {
    console.warn('Some mobile menu elements not found, skipping mobile menu initialization');
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
      // Don't close for admin link if it's hidden or doesn't have href
      if (link.id === 'mobileAdminLink' && link.style.display === 'none') {
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
    
    // Update desktop user badge
    const whoElement = document.getElementById("who");
    if (whoElement) {
      whoElement.textContent = `${user.name} (${user.role})`;
    }
    
    // Update mobile user info
    const mobileWhoElement = document.getElementById("mobileWho");
    if (mobileWhoElement) {
      mobileWhoElement.textContent = `${user.name} (${user.role})`;
    }

    // Show admin links if user is admin
    if (user.role === "ADMIN") {
      const adminLink = document.getElementById("adminLink");
      const mobileAdminLink = document.getElementById("mobileAdminLink");
      
      if (adminLink) {
        adminLink.style.display = "inline-flex";
      }
      
      if (mobileAdminLink) {
        mobileAdminLink.style.display = "flex";
      }
    }

    await loadProducts();
    await loadNotifications();
  } catch (error) {
    console.error("Failed to load dashboard:", error);
    alert("Failed to load dashboard data. Please refresh the page.");
  }
}

async function loadProducts() {
  const items = await apiFetch("/products");
  const tbody = document.getElementById("productsBody");
  tbody.innerHTML = "";

  if (items.length === 0) {
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
    const statusClass = p.status === 'blocked' ? 'badge--error' : 
                       p.status === 'pending' ? 'badge--warning' : 
                       p.status === 'active' ? 'badge--success' : 'badge--info';
    
    const row = document.createElement('tr');
    row.className = 'product-row';
    row.innerHTML = `
      <td class="product-info">
        <div class="product-title"><b>${p.title || "Untitled"}</b></div>
        <div class="product-meta">
          <span class="product-platform">${p.platform.toUpperCase()}</span>
          <span class="product-divider">•</span>
          <a href="${p.url}" target="_blank" class="product-link">Open product page</a>
        </div>
      </td>
      <td class="product-price">${fmtMoney(p.current_price, p.currency)}</td>
      <td class="product-status">
        <span class="badge ${statusClass}">${p.status}</span>
      </td>
      <td class="product-checked">
        <div class="last-checked">${p.last_checked ? new Date(p.last_checked).toLocaleDateString() : "—"}</div>
        <div class="last-checked-time">${p.last_checked ? new Date(p.last_checked).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'}) : ""}</div>
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

  // Add event listeners
  tbody.querySelectorAll("button[data-view]").forEach(btn => {
    btn.addEventListener("click", () => {
      const id = btn.getAttribute("data-view");
      window.location.href = `product.html?id=${encodeURIComponent(id)}`;
    });
  });

  tbody.querySelectorAll("button[data-del]").forEach(btn => {
    btn.addEventListener("click", async () => {
      const id = btn.getAttribute("data-del");
      if (!confirm("Delete this tracked product? This action cannot be undone.")) return;
      try {
        await apiFetch(`/products/${id}`, { method: "DELETE" });
        await loadProducts();
      } catch (err) {
        alert("Failed to delete product: " + err.message);
      }
    });
  });
}

async function loadNotifications() {
  const items = await apiFetch("/notifications");
  const box = document.getElementById("notifBox");
  box.innerHTML = "";

  if (items.length === 0) {
    box.innerHTML = `
      <div class="empty-state">
        <div class="empty-state__icon">🔔</div>
        <div class="empty-state__message">No notifications yet</div>
        <div class="empty-state__hint">Price drop alerts will appear here</div>
      </div>
    `;
    return;
  }

  // Add notifications with proper styling
  for (const n of items.slice(0, 5)) { // Show only 5 most recent
    const notificationClass = n.status === 'sent' ? 'notification--success' :
                            n.status === 'failed' ? 'notification--error' :
                            n.status === 'pending' ? 'notification--warning' : 'notification--info';
    
    const notification = document.createElement('div');
    notification.className = `notification ${notificationClass}`;
    notification.innerHTML = `
      <div class="notification__header">
        <span class="notification__channel">${n.channel}</span>
        <span class="notification__time">${new Date(n.sent_at).toLocaleDateString()} • ${new Date(n.sent_at).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}</span>
      </div>
      <div class="notification__title">${n.type || 'Price Alert'}</div>
      <div class="notification__message">${n.message}</div>
    `;
    box.appendChild(notification);
  }

  // Show "view all" link if there are more than 5
  if (items.length > 5) {
    const viewAll = document.createElement('div');
    viewAll.className = 'view-all-notifications';
    viewAll.innerHTML = `<a href="notifications.html" class="small">View all ${items.length} notifications →</a>`;
    box.appendChild(viewAll);
  }
}

document.getElementById("logoutBtn").addEventListener("click", (e) => {
  e.preventDefault();
  if (confirm("Are you sure you want to logout?")) {
    logout();
  }
});

document.getElementById("trackForm").addEventListener("submit", async (e) => {
  e.preventDefault();
  const url = document.getElementById("url").value.trim();
  const platform = document.getElementById("platform").value;

  if (!url) {
    alert("Please enter a product URL");
    return;
  }

  const submitBtn = e.target.querySelector('button[type="submit"]');
  const originalText = submitBtn.textContent;
  submitBtn.textContent = "Tracking...";
  submitBtn.disabled = true;

  try {
    await apiFetch("/products/track", {
      method: "POST",
      body: JSON.stringify({ url, platform })
    });
    document.getElementById("url").value = "";
    await loadProducts();
  } catch (err) {
    alert("Tracking failed: " + err.message);
  } finally {
    submitBtn.textContent = originalText;
    submitBtn.disabled = false;
  }
});

// Load data on page load
load().catch(err => {
  console.error("Failed to load dashboard:", err);
  alert("Failed to load dashboard data. Please refresh the page.");
});