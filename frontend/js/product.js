// js/product.js
// Product page functionality with toast notifications and confirmation modal

requireAuth();

function getId() {
  const u = new URL(window.location.href);
  return u.searchParams.get("id");
}

function drawLineChart(canvas, points) {
  const ctx = canvas.getContext("2d");
  const w = canvas.width = canvas.clientWidth * window.devicePixelRatio;
  const h = canvas.height = canvas.clientHeight * window.devicePixelRatio;
  
  // Clear canvas
  ctx.clearRect(0, 0, w, h);
  
  if (points.length < 2) {
    // Draw empty state
    ctx.font = '14px Poppins';
    ctx.fillStyle = '#5A6361';
    ctx.textAlign = 'center';
    ctx.fillText('Not enough data yet. Wait for checks to accumulate.', w / 2, h / 2);
    return;
  }

  // Sort points by timestamp
  points.sort((a, b) => a.t - b.t);
  
  const prices = points.map(p => p.price);
  const min = Math.min(...prices);
  const max = Math.max(...prices);
  const padding = 60 * window.devicePixelRatio;
  
  const chartX = padding;
  const chartY = padding;
  const chartWidth = w - (padding * 2);
  const chartHeight = h - (padding * 2);
  
  // Draw grid
  ctx.strokeStyle = '#E8ECEB';
  ctx.lineWidth = 1;
  
  // Horizontal grid lines
  const gridLines = 5;
  for (let i = 0; i <= gridLines; i++) {
    const y = chartY + (chartHeight / gridLines) * i;
    ctx.beginPath();
    ctx.moveTo(chartX, y);
    ctx.lineTo(chartX + chartWidth, y);
    ctx.stroke();
    
    // Y-axis labels
    const priceValue = max - ((max - min) / gridLines) * i;
    ctx.fillStyle = '#5A6361';
    ctx.font = '12px Poppins';
    ctx.textAlign = 'right';
    ctx.fillText(priceValue.toFixed(2), chartX - 10, y + 4);
  }
  
  // Draw line
  ctx.strokeStyle = '#5285E8';
  ctx.lineWidth = 3;
  ctx.lineJoin = 'round';
  ctx.lineCap = 'round';
  ctx.beginPath();
  
  points.forEach((point, index) => {
    const x = chartX + (chartWidth / (points.length - 1)) * index;
    const y = chartY + chartHeight - ((point.price - min) / (max - min)) * chartHeight;
    
    if (index === 0) {
      ctx.moveTo(x, y);
    } else {
      ctx.lineTo(x, y);
    }
  });
  
  ctx.stroke();
  
  // Draw data points
  ctx.fillStyle = '#5285E8';
  points.forEach((point, index) => {
    const x = chartX + (chartWidth / (points.length - 1)) * index;
    const y = chartY + chartHeight - ((point.price - min) / (max - min)) * chartHeight;
    
    ctx.beginPath();
    ctx.arc(x, y, 4, 0, Math.PI * 2);
    ctx.fill();
  });
  
  // Draw min/max labels
  const minIndex = prices.indexOf(min);
  const maxIndex = prices.indexOf(max);
  
  if (minIndex !== -1) {
    const x = chartX + (chartWidth / (points.length - 1)) * minIndex;
    const y = chartY + chartHeight;
    
    ctx.fillStyle = '#E63946';
    ctx.font = 'bold 12px Poppins';
    ctx.textAlign = 'center';
    ctx.fillText(`Low: ${min.toFixed(2)}`, x, y + 20);
  }
  
  if (maxIndex !== -1) {
    const x = chartX + (chartWidth / (points.length - 1)) * maxIndex;
    const y = chartY;
    
    ctx.fillStyle = '#2A9D8F';
    ctx.font = 'bold 12px Poppins';
    ctx.textAlign = 'center';
    ctx.fillText(`High: ${max.toFixed(2)}`, x, y - 10);
  }
}

async function loadDetail() {
  const id = getId();
  if (!id) {
    toast.error("Missing product ID. Redirecting to dashboard...", {
      duration: 3000,
      showProgress: true
    });
    
    setTimeout(() => {
      window.location.href = 'dashboard.html';
    }, 2500);
    return;
  }

  try {
    toast.info('Loading product details...', {
      duration: 2000,
      showProgress: true
    });

    const data = await apiFetch(`/products/${id}`);
    document.getElementById("title").textContent = data.title || "Untitled";
    document.getElementById("meta").textContent = `${data.platform.toUpperCase()} • ${data.status}`;
    document.getElementById("price").textContent = fmtMoney(data.current_price, data.currency);
    document.getElementById("urlLink").href = data.url;
    document.getElementById("urlLink").textContent = "Open product page";
    
    // Update status badge
    const statusBadge = document.getElementById("status");
    statusBadge.textContent = data.status;
    statusBadge.className = 'badge';
    
    if (data.status === 'blocked') {
      statusBadge.classList.add('badge--error');
    } else if (data.status === 'pending') {
      statusBadge.classList.add('badge--warning');
    } else if (data.status === 'active') {
      statusBadge.classList.add('badge--success');
    } else {
      statusBadge.classList.add('badge--info');
    }
    
    // Show blocked reason if exists
    const blockedReason = document.getElementById("blockedReason");
    if (data.blocked_reason) {
      blockedReason.textContent = data.blocked_reason;
      blockedReason.className = 'blocked-reason';
    } else {
      blockedReason.textContent = '';
    }

    // Draw chart
    const points = (data.history_6m || []).map(x => ({
      t: new Date(x.timestamp).getTime(),
      price: Number(x.price)
    }));
    
    drawLineChart(document.getElementById("chart"), points);

    await loadAlerts(id);
  } catch (error) {
    console.error('Failed to load product details:', error);
    toast.error('Failed to load product details. Please try again.', {
      duration: 5000,
      showProgress: true
    });
  }
}

async function loadAlerts(productId) {
  try {
    const alerts = await apiFetch("/alerts");
    const mine = alerts.filter(a => a.tracked_product_id === productId);
    const box = document.getElementById("alertsBox");
    box.innerHTML = "";

    if (mine.length === 0) {
      box.innerHTML = `
        <div class="empty-state">
          <div class="empty-state__icon">🔔</div>
          <div class="empty-state__message">No alerts set up yet</div>
          <div class="empty-state__hint">Create your first alert using the form above</div>
        </div>
      `;
      return;
    }

    for (const a of mine) {
      const alertCard = document.createElement('div');
      alertCard.className = 'alert-card';
      alertCard.innerHTML = `
        <div class="alert-card__header">
          <div class="alert-card__status ${a.is_active ? 'alert-card__status--active' : 'alert-card__status--inactive'}">
            ${a.is_active ? 'Active' : 'Inactive'}
          </div>
          <div class="alert-card__meta">
            Notify once: ${a.notify_once ? 'Yes' : 'No'} • Notified: ${a.has_notified_once ? 'Yes' : 'No'}
          </div>
        </div>
        <div class="alert-card__content">
          <div class="alert-card__criteria">
            ${a.target_price ? `<div class="alert-card__criterion"><span class="alert-card__label">Target Price:</span> <span class="alert-card__value">${fmtMoney(a.target_price, '')}</span></div>` : ''}
            ${a.discount_threshold ? `<div class="alert-card__criterion"><span class="alert-card__label">Discount Threshold:</span> <span class="alert-card__value">${a.discount_threshold}%</span></div>` : ''}
            ${!a.target_price && !a.discount_threshold ? '<div class="alert-card__criterion">No criteria set</div>' : ''}
          </div>
        </div>
        <div class="alert-card__actions">
          <button class="action-button button--secondary" data-toggle="${a.id}">${a.is_active ? "Disable" : "Enable"}</button>
          <button class="action-button button--danger" data-del="${a.id}">Delete</button>
        </div>
      `;
      box.appendChild(alertCard);
    }

    // Add event listeners for toggle buttons
    box.querySelectorAll("button[data-toggle]").forEach(btn => {
      btn.addEventListener("click", async () => {
        const id = btn.getAttribute("data-toggle");
        const current = mine.find(x => x.id === id);
        const newState = !current.is_active;
        
        const originalText = btn.textContent;
        btn.textContent = "Updating...";
        btn.disabled = true;
        
        try {
          await apiFetch(`/alerts/${id}`, {
            method: "PATCH",
            body: JSON.stringify({ is_active: newState })
          });
          
          toast.success(`Alert ${newState ? 'enabled' : 'disabled'} successfully`, {
            duration: 3000,
            showProgress: true
          });
          
          await loadAlerts(productId);
        } catch (error) {
          toast.error(`Failed to update alert: ${error.message}`, {
            duration: 5000,
            showProgress: true
          });
        } finally {
          btn.textContent = originalText;
          btn.disabled = false;
        }
      });
    });

    // Add event listeners for delete buttons with confirmation modal
    box.querySelectorAll("button[data-del]").forEach(btn => {
      btn.addEventListener("click", async () => {
        const id = btn.getAttribute("data-del");
        
        const confirmed = await confirmationModal.show({
          title: 'Delete Alert',
          message: 'Are you sure you want to delete this alert? This action cannot be undone.',
          confirmText: 'Delete',
          cancelText: 'Cancel',
          type: 'danger'
        });
        
        if (!confirmed) return;
        
        const originalText = btn.textContent;
        btn.textContent = "Deleting...";
        btn.disabled = true;
        
        try {
          await apiFetch(`/alerts/${id}`, { method: "DELETE" });
          
          toast.success('Alert deleted successfully', {
            duration: 3000,
            showProgress: true
          });
          
          await loadAlerts(productId);
        } catch (error) {
          toast.error(`Failed to delete alert: ${error.message}`, {
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
    console.error('Failed to load alerts:', error);
    toast.error('Failed to load alerts. Please try again.', {
      duration: 5000,
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

// Alert form submission
document.getElementById("alertForm").addEventListener("submit", async (e) => {
  e.preventDefault();
  const productId = getId();
  if (!productId) {
    toast.error("Product ID is missing. Please reload the page.", {
      duration: 4000,
      showProgress: true
    });
    return;
  }

  const submitBtn = e.target.querySelector('button[type="submit"]');
  const originalText = submitBtn.textContent;
  submitBtn.textContent = "Creating...";
  submitBtn.disabled = true;

  const target = document.getElementById("targetPrice").value.trim();
  const disc = document.getElementById("discountThreshold").value.trim();
  const notifyOnce = document.getElementById("notifyOnce").checked;

  // Validate at least one criteria is provided
  if (!target && !disc) {
    toast.warning("Please provide either a target price or discount threshold", {
      duration: 4000,
      showProgress: true
    });
    submitBtn.textContent = originalText;
    submitBtn.disabled = false;
    return;
  }

  // Validate target price is positive
  if (target && Number(target) <= 0) {
    toast.error("Target price must be greater than 0", {
      duration: 4000,
      showProgress: true
    });
    submitBtn.textContent = originalText;
    submitBtn.disabled = false;
    return;
  }

  // Validate discount threshold is between 0 and 100
  if (disc && (Number(disc) <= 0 || Number(disc) > 100)) {
    toast.error("Discount threshold must be between 1% and 100%", {
      duration: 4000,
      showProgress: true
    });
    submitBtn.textContent = originalText;
    submitBtn.disabled = false;
    return;
  }

  const payload = {
    tracked_product_id: productId,
    target_price: target ? Number(target) : null,
    discount_threshold: disc ? Number(disc) : null,
    notify_once: notifyOnce,
    is_active: true
  };

  try {
    await apiFetch("/alerts", { 
      method: "POST", 
      body: JSON.stringify(payload) 
    });
    
    document.getElementById("targetPrice").value = "";
    document.getElementById("discountThreshold").value = "";
    document.getElementById("notifyOnce").checked = true;
    
    toast.success("✓ Alert created successfully", {
      duration: 3000,
      showProgress: true
    });
    
    await loadAlerts(productId);
  } catch (err) {
    toast.error(`Failed to create alert: ${err.message}`, {
      duration: 5000,
      showProgress: true
    });
  } finally {
    submitBtn.textContent = originalText;
    submitBtn.disabled = false;
  }
});

// Load on page load
loadDetail().catch(err => {
  console.error('Page load error:', err);
  toast.error('Failed to load product page. Please try again.', {
    duration: 5000,
    showProgress: true
  });
});

// Handle window resize for chart
let resizeTimeout;
window.addEventListener('resize', () => {
  clearTimeout(resizeTimeout);
  resizeTimeout = setTimeout(async () => {
    await loadDetail();
  }, 250);
});