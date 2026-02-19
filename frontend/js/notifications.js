// js/notifications.js
// Notifications page functionality

requireAuth();

/* =========================
   Mobile Menu
   ========================= */
function initMobileMenu() {
  const menuToggle = document.getElementById("menuToggle");
  const closeMenu = document.getElementById("closeMenu");
  const mobileMenuOverlay = document.getElementById("mobileMenuOverlay");
  const mobileMenu = document.getElementById("mobileMenu");
  const mobileLogoutBtn = document.getElementById("mobileLogoutBtn");

  if (!menuToggle || !closeMenu || !mobileMenuOverlay || !mobileMenu) return;

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

  mobileLogoutBtn?.addEventListener("click", async (e) => {
    e.preventDefault();
    closeMobileMenu();
    
    const confirmed = await confirmationModal.show({
      title: "Logout",
      message: "Are you sure you want to logout?",
      confirmText: "Logout",
      cancelText: "Stay",
      type: "warning",
    });

    if (confirmed) {
      toast.info("Logging you out...", { duration: 1500 });
      setTimeout(() => logout(), 1500);
    }
  });

  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && mobileMenu.classList.contains("active")) {
      closeMobileMenu();
    }
  });
}

/* =========================
   Load User Info
   ========================= */
async function loadUserInfo() {
  try {
    const user = await me();
    
    document.getElementById("who").textContent = `${user.name} (${user.role})`;
    document.getElementById("mobileWho").textContent = `${user.name} (${user.role})`;
    
    if (user.role === "ADMIN") {
      document.getElementById("adminLink").style.display = "inline-flex";
      document.getElementById("mobileAdminLink").style.display = "flex";
    }
  } catch (error) {
    console.error("Failed to load user info:", error);
  }
}

/* =========================
   State Management
   ========================= */
let allNotifications = [];

/* =========================
   Load Notifications
   ========================= */
async function loadNotifications() {
  const listEl = document.getElementById("notificationsList");
  
  try {
    // Show loading state
    listEl.innerHTML = `
      <div class="loading-state">
        <div class="loading-spinner"></div>
        <div class="loading-text">Loading notifications...</div>
      </div>
    `;

    const notifications = await apiFetch("/notifications");
    // Filter out email notifications - only show in_app
    allNotifications = (notifications || []).filter(n => n.channel === "in_app");
    
    updateNotificationCount();
    renderNotifications();
  } catch (error) {
    console.error("Failed to load notifications:", error);
    listEl.innerHTML = `
      <div class="empty-state">
        <div class="empty-state__icon">⚠️</div>
        <div class="empty-state__message">Failed to load notifications</div>
        <div class="empty-state__hint">Please try refreshing the page</div>
        <button class="secondary" onclick="loadNotifications()" style="margin-top: var(--space-md);">Retry</button>
      </div>
    `;
  }
}

/* =========================
   Update Notification Count
   ========================= */
function updateNotificationCount() {
  const countEl = document.getElementById("notificationsCount");
  const unreadCount = allNotifications.filter(n => !n.read).length;
  countEl.textContent = unreadCount;
  
  // Update page title
  if (unreadCount > 0) {
    document.title = `(${unreadCount}) Notifications • Smart Price Tracker`;
  } else {
    document.title = `Notifications • Smart Price Tracker`;
  }
}

/* =========================
   Format Date
   ========================= */
function formatNotificationDate(dateString) {
  if (!dateString) return "";
  
  const date = new Date(dateString);
  const now = new Date();
  const diffMs = now - date;
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMs / 3600000);
  const diffDays = Math.floor(diffMs / 86400000);

  if (diffMins < 1) return "Just now";
  if (diffMins < 60) return `${diffMins} minute${diffMins > 1 ? 's' : ''} ago`;
  if (diffHours < 24) return `${diffHours} hour${diffHours > 1 ? 's' : ''} ago`;
  if (diffDays < 7) return `${diffDays} day${diffDays > 1 ? 's' : ''} ago`;
  
  return date.toLocaleDateString([], { 
    year: 'numeric', 
    month: 'short', 
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  });
}

/* =========================
   Get Notification Icon
   ========================= */
function getNotificationIcon(status) {
  switch(status) {
    case "sent": return "✅";
    case "failed": return "❌";
    case "warning": return "⚠️";
    default: return "🔔";
  }
}

/* =========================
   Extract URL from Message
   ========================= */
function extractUrlFromMessage(message) {
  if (!message) return null;
  const urlMatch = message.match(/https?:\/\/[^\s]+/);
  return urlMatch ? urlMatch[0] : null;
}

/* =========================
   Clean Message (remove URL)
   ========================= */
function cleanMessage(message) {
  if (!message) return "";
  return message.replace(/https?:\/\/[^\s]+/g, '').trim();
}

/* =========================
   Render Notifications
   ========================= */
function renderNotifications() {
  const listEl = document.getElementById("notificationsList");

  if (!allNotifications || allNotifications.length === 0) {
    listEl.innerHTML = `
      <div class="empty-state">
        <div class="empty-state__icon">🔔</div>
        <div class="empty-state__message">No notifications yet</div>
        <div class="empty-state__hint">When you get price alerts, they'll appear here</div>
      </div>
    `;
    return;
  }

  listEl.innerHTML = allNotifications.map(notification => {
    const date = formatNotificationDate(notification.sent_at);
    const isUnread = !notification.read;
    const icon = getNotificationIcon(notification.status);
    const productUrl = extractUrlFromMessage(notification.message);
    const cleanMsg = cleanMessage(notification.message);
    
    let statusClass = "notification-item--info";
    if (notification.status === "sent") statusClass = "notification-item--success";
    else if (notification.status === "failed") statusClass = "notification-item--error";
    else if (notification.status === "warning") statusClass = "notification-item--warning";
    
    const unreadClass = isUnread ? "notification-item--unread" : "";
    
    return `
      <div class="notification-item ${statusClass} ${unreadClass}" data-id="${escapeHtml(notification.id)}">
        <div class="notification-item__icon">${icon}</div>
        
        <div class="notification-item__content">
          <div class="notification-item__header">
            <span class="notification-item__time">${escapeHtml(date)}</span>
          </div>
          
          <div class="notification-item__title">${escapeHtml(notification.type || "Price Alert")}</div>
          
          <div class="notification-item__message">${escapeHtml(cleanMsg)}</div>
          
          ${productUrl ? `
            <div class="notification-item__product-link">
              <a href="${escapeHtml(productUrl)}" target="_blank" rel="noopener" class="notification-item__view-button">
                View Product
              </a>
            </div>
          ` : ''}
        </div>
        
        <div class="notification-item__actions">
          ${isUnread ? `
            <button class="notification-item__mark-read" title="Mark as read" onclick="markAsRead('${notification.id}')">
              ✓
            </button>
          ` : ''}
          <button class="notification-item__delete" title="Delete notification" onclick="deleteNotification('${notification.id}')">
            ×
          </button>
        </div>
      </div>
    `;
  }).join("");
}

/* =========================
   Mark Notification as Read
   ========================= */
async function markAsRead(notificationId) {
  try {
    await apiFetch(`/notifications/${notificationId}/read`, { 
      method: "PATCH" 
    });
    
    // Update local state
    const notification = allNotifications.find(n => n.id === notificationId);
    if (notification) {
      notification.read = true;
    }
    
    updateNotificationCount();
    renderNotifications();
    
    toast.success("Notification marked as read", { duration: 2000 });
  } catch (error) {
    console.error("Failed to mark as read:", error);
    toast.error("Failed to mark notification as read", { duration: 3000 });
  }
}

/* =========================
   Mark All as Read
   ========================= */
async function markAllAsRead() {
  try {
    await apiFetch("/notifications/read-all", { 
      method: "POST" 
    });
    
    // Update local state
    allNotifications.forEach(n => n.read = true);
    
    updateNotificationCount();
    renderNotifications();
    
    toast.success("All notifications marked as read", { duration: 3000 });
  } catch (error) {
    console.error("Failed to mark all as read:", error);
    toast.error("Failed to mark all as read", { duration: 3000 });
  }
}

/* =========================
   Delete Single Notification
   ========================= */
async function deleteNotification(notificationId) {
  // Find notification for the message
  const notification = allNotifications.find(n => n.id === notificationId);
  const message = notification?.message || "this notification";
  const shortMessage = message.length > 50 ? message.substring(0, 50) + "..." : message;
  
  const confirmed = await confirmationModal.show({
    title: "Delete Notification",
    message: `Are you sure you want to delete "${escapeHtml(shortMessage)}"?`,
    confirmText: "Delete",
    cancelText: "Cancel",
    type: "danger"
  });

  if (!confirmed) return;

  try {
    await apiFetch(`/notifications/${notificationId}`, { 
      method: "DELETE" 
    });
    
    // Remove from local state
    allNotifications = allNotifications.filter(n => n.id !== notificationId);
    
    updateNotificationCount();
    renderNotifications();
    
    toast.success("Notification deleted", { duration: 2000 });
  } catch (error) {
    console.error("Failed to delete notification:", error);
    toast.error("Failed to delete notification", { duration: 3000 });
  }
}

/* =========================
   Clear All Notifications
   ========================= */
async function clearAllNotifications() {
  const confirmed = await confirmationModal.show({
    title: "Clear All Notifications",
    message: "Are you sure you want to delete ALL notifications? This action cannot be undone.",
    confirmText: "Clear All",
    cancelText: "Cancel",
    type: "danger"
  });

  if (!confirmed) return;

  // Show loading state on button
  const clearBtn = document.getElementById("clearAllBtn");
  const originalText = clearBtn.innerHTML;
  clearBtn.innerHTML = '<span class="btn-icon">⏳</span><span class="btn-text">Clearing...</span>';
  clearBtn.disabled = true;

  try {
    await apiFetch("/notifications/clear-all", { 
      method: "DELETE" 
    });
    
    // Clear local state
    allNotifications = [];
    
    updateNotificationCount();
    renderNotifications();
    
    toast.success("All notifications cleared", { duration: 3000 });
  } catch (error) {
    console.error("Failed to clear notifications:", error);
    toast.error("Failed to clear notifications", { duration: 3000 });
  } finally {
    // Restore button
    clearBtn.innerHTML = originalText;
    clearBtn.disabled = false;
  }
}

/* =========================
   Escape HTML Helper
   ========================= */
function escapeHtml(str) {
  if (!str) return "";
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

/* =========================
   Desktop Logout
   ========================= */
document.getElementById("logoutBtn")?.addEventListener("click", async (e) => {
  e.preventDefault();

  const confirmed = await confirmationModal.show({
    title: "Logout",
    message: "Are you sure you want to logout?",
    confirmText: "Logout",
    cancelText: "Stay",
    type: "warning",
  });

  if (confirmed) {
    toast.info("Logging you out...", { duration: 1500 });
    setTimeout(() => logout(), 1500);
  }
});

/* =========================
   Event Listeners
   ========================= */
document.getElementById("markAllReadBtn")?.addEventListener("click", markAllAsRead);
document.getElementById("clearAllBtn")?.addEventListener("click", clearAllNotifications);

/* =========================
   Initialize
   ========================= */
document.addEventListener("DOMContentLoaded", () => {
  initMobileMenu();
  loadUserInfo();
  loadNotifications();
});