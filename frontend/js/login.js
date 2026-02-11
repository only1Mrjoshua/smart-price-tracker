// js/login.js
// Handles login form submission with spinner loading animation

document.addEventListener('DOMContentLoaded', () => {
  const form = document.getElementById('form');
  const emailInput = document.getElementById('email');
  const passwordInput = document.getElementById('password');
  const rememberCheckbox = document.getElementById('remember');
  const loginButton = document.getElementById('login-button');
  const spinnerOverlay = document.getElementById('spinner-overlay');
  const errorContainer = document.getElementById('form-error');

  // Preserve existing validation and login flow
  // Simulate API delay - replace with real fetch when ready
  const simulateLogin = async (email, password, remember) => {
    // Fake API call - mimics network delay
    return new Promise((resolve, reject) => {
      setTimeout(() => {
        // Demo credentials - keep existing behavior
        if (email && password) {
          // Store remember me preference if needed
          if (remember) {
            localStorage.setItem('rememberEmail', email);
          } else {
            localStorage.removeItem('rememberEmail');
          }
          resolve({ success: true, token: 'fake-jwt-token' });
        } else {
          reject(new Error('Invalid credentials'));
        }
      }, 1500); // 1.5s spinner display for demo
    });
  };

  // Show spinner and disable form
  const showLoading = () => {
    loginButton.disabled = true;
    spinnerOverlay.classList.add('active');
    spinnerOverlay.setAttribute('aria-hidden', 'false');
    emailInput.disabled = true;
    passwordInput.disabled = true;
    if (rememberCheckbox) rememberCheckbox.disabled = true;
    hideError(); // Clear any previous errors
  };

  // Hide spinner and re-enable form
  const hideLoading = () => {
    loginButton.disabled = false;
    spinnerOverlay.classList.remove('active');
    spinnerOverlay.setAttribute('aria-hidden', 'true');
    emailInput.disabled = false;
    passwordInput.disabled = false;
    if (rememberCheckbox) rememberCheckbox.disabled = false;
  };

  // Display error message
  const showError = (message) => {
    if (errorContainer) {
      errorContainer.textContent = message;
      errorContainer.style.display = 'block';
    } else {
      // Fallback to alert if no container
      alert(message);
    }
  };

  // Hide error message
  const hideError = () => {
    if (errorContainer) {
      errorContainer.style.display = 'none';
      errorContainer.textContent = '';
    }
  };

  // Form submit handler
  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    
    // Basic validation
    const email = emailInput.value.trim();
    const password = passwordInput.value;
    const remember = rememberCheckbox ? rememberCheckbox.checked : false;

    if (!email || !password) {
      showError('Please fill in all fields');
      return;
    }

    // Start loading
    showLoading();

    try {
      // Call login function from auth.js (preserved)
      // This integrates with your existing auth system
      await login(email, password, remember);
      
      // If successful, redirect (handled in auth.js or here)
      window.location.href = 'dashboard.html';
    } catch (err) {
      // Show error message
      showError(err.message || 'Login failed. Please try again.');
    } finally {
      // Always hide spinner
      hideLoading();
    }
  });

  // Optional: Pre-fill remember me email
  const savedEmail = localStorage.getItem('rememberEmail');
  if (savedEmail && emailInput && rememberCheckbox) {
    emailInput.value = savedEmail;
    rememberCheckbox.checked = true;
  }
});