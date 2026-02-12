// js/admin.js
// Admin dashboard functionality with toast notifications and confirmation modal

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
  
  function toggleMenu() {
    const isActive = menuToggle.classList.toggle('active');
    mobileMenu.classList.toggle('active');
    mobileMenuOverlay.classList.toggle('active');
    document.body.style.overflow = isActive ? 'hidden' : '';
  }
  
  function closeMobileMenu() {
    menuToggle.classList.remove('active');
    mobileMenu.classList.remove('active');
    mobileMenuOverlay.classList.remove('active');
    document.body.style.overflow = '';
  }
  
  menuToggle.addEventListener('click', toggleMenu);
  closeMenu.addEventListener('click', closeMobileMenu);
  mobileMenuOverlay.addEventListener('click', closeMobileMenu);
  
  mobileMenu.querySelectorAll('.mobile-nav-links a').forEach(link => {
    link.addEventListener('click', (e) => {
      if (link.href === '#' || link.getAttribute('href') === 'javascript:void(0)') {
        e.preventDefault();
        return;
      }
      setTimeout(closeMobileMenu, 300);
    });
  });
  
  // Mobile logout button with confirmation modal
  mobileLogoutBtn.addEventListener('click', async (e) => {
    e.preventDefault();
    closeMobileMenu();
    
    const confirmed = await confirmationModal.show({
      title: 'Logout',
      message: 'Are you sure you want to logout from your account?',
      confirmText: 'Logout',
      cancelText: 'Stay',
      type: 'warning'
    });
    
    if (confirmed) {
      toast.info('Logging you out...', {
        duration: 1500,
        showProgress: true
      });
      
      setTimeout(() => {
        logout();
      }, 1500);
    }
  });
  
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && mobileMenu.classList.contains('active')) {
      closeMobileMenu();
    }
  });
  
  mobileMenu.addEventListener('touchmove', (e) => {
    if (mobileMenu.scrollHeight > mobileMenu.clientHeight) {
      return;
    }
    e.preventDefault();
  }, { passive: false });
}

document.addEventListener('DOMContentLoaded', initMobileMenu);

async function load() {
  try {
    const user = await me();
    
    const mobileWho = document.getElementById('mobileWho');
    if (mobileWho) {
      mobileWho.textContent = `${user.name} (${user.role})`;
    }
    
    if (user.role !== "ADMIN") {
      toast.error("Admin access required. Redirecting to dashboard...", {
        duration: 3000,
        showProgress: true
      });
      
      setTimeout(() => {
        window.location.href = "dashboard.html";
      }, 2500);
      return;
    }

    toast.info('Loading admin dashboard...', {
      duration: 2000,
      showProgress: true
    });

    await loadUsers();
    await loadProducts();
    
    toast.success('Admin dashboard loaded successfully', {
      duration: 3000,
      showProgress: true
    });
    
  } catch (error) {
    console.error("Failed to load admin page:", error);
    toast.error("Failed to load admin dashboard. Please refresh the page.", {
      duration: 5000,
      showProgress: true
    });
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
    
    toast.success(`Loaded ${users.length} users`, {
      duration: 2000,
      showProgress: false
    });
    
  } catch (error) {
    console.error("Failed to load users:", error);
    toast.error("Failed to load users. Please try again.", {
      duration: 4000,
      showProgress: true
    });
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

    toast.success(`Loaded ${items.length} tracked products`, {
      duration: 2000,
      showProgress: false
    });

    // Add event listeners for recheck buttons
    tbody.querySelectorAll("button[data-recheck]").forEach((btn) => {
      btn.addEventListener("click", async () => {
        const id = btn.getAttribute("data-recheck");
        const originalText = btn.textContent;
        const productRow = btn.closest('tr');
        const productTitle = productRow?.querySelector('.admin-product-info__title b')?.textContent || 'Product';
        
        // Confirm before recheck using confirmationModal
        const confirmed = await confirmationModal.show({
          title: 'Force Recheck',
          message: `Are you sure you want to force a price recheck for "${productTitle}"?`,
          confirmText: 'Recheck',
          cancelText: 'Cancel',
          type: 'info'
        });
        
        if (!confirmed) {
          return;
        }
        
        btn.textContent = "Rechecking...";
        btn.disabled = true;

        try {
          toast.info(`Queuing recheck for "${productTitle}"...`, {
            duration: 2000,
            showProgress: true
          });
          
          await apiFetch(`/admin/recheck/${id}`, { method: "POST" });
          
          toast.success(`✓ Recheck queued for "${productTitle}"`, {
            duration: 4000,
            showProgress: true
          });
          
          await loadProducts();
        } catch (error) {
          toast.error(`✗ Failed to queue recheck for "${productTitle}": ${error.message}`, {
            duration: 5000,
            showProgress: true
          });
        } finally {
          btn.textContent = originalText;
          btn.disabled = false;
        }
      });
    });
  } catch (error) {
    console.error("Failed to load products:", error);
    toast.error("Failed to load products. Please try again.", {
      duration: 4000,
      showProgress: true
    });
  }
}

// Desktop logout button with confirmation modal
document.getElementById("logoutBtn").addEventListener("click", async (e) => {
  e.preventDefault();
  
  const confirmed = await confirmationModal.show({
    title: 'Logout',
    message: 'Are you sure you want to logout from your account?',
    confirmText: 'Logout',
    cancelText: 'Stay',
    type: 'warning'
  });
  
  if (confirmed) {
    toast.info('Logging you out...', {
      duration: 1500,
      showProgress: true
    });
    
    setTimeout(() => {
      logout();
    }, 1500);
  }
});

// Load data on page load
load().catch((error) => {
  console.error("Failed to load admin page:", error);
  toast.error("Failed to load admin dashboard. Please refresh the page.", {
    duration: 5000,
    showProgress: true
  });
});