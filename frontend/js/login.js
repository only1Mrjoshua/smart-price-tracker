// js/login.js
// Handles login form submission with spinner loading animation

document.addEventListener('DOMContentLoaded', () => {
  const form = document.getElementById('form');
  const emailInput = document.getElementById('email');
  const passwordInput = document.getElementById('password');
  const submitButton = form.querySelector('button[type="submit"]');
  
  // Create spinner overlay if it doesn't exist
  let spinnerOverlay = document.getElementById('spinner-overlay');
  if (!spinnerOverlay) {
    spinnerOverlay = document.createElement('div');
    spinnerOverlay.id = 'spinner-overlay';
    spinnerOverlay.className = 'spinner-overlay';
    spinnerOverlay.setAttribute('aria-hidden', 'true');
    
    const spinner = document.createElement('div');
    spinner.className = 'spinner';
    spinnerOverlay.appendChild(spinner);
    
    form.style.position = 'relative';
    form.appendChild(spinnerOverlay);
  }
  
  // Create error container if it doesn't exist
  let errorContainer = document.getElementById('form-error');
  if (!errorContainer) {
    errorContainer = document.createElement('div');
    errorContainer.id = 'form-error';
    errorContainer.className = 'form-error';
    errorContainer.style.display = 'none';
    form.insertBefore(errorContainer, form.firstChild);
  }

  // Simulate API delay - replace with real fetch when ready
  const simulateLogin = async (email, password) => {
    // Fake API call - mimics network delay
    return new Promise((resolve, reject) => {
      setTimeout(() => {
        // Demo credentials - keep existing behavior
        if (email && password) {
          // Demo validation - you can change this logic
          if (email === 'demo@example.com' && password === 'password123') {
            resolve({ success: true, token: 'fake-jwt-token' });
          } else {
            reject(new Error('Invalid email or password'));
          }
        } else {
          reject(new Error('Please enter both email and password'));
        }
      }, 1500); // 1.5s spinner display for demo
    });
  };

  // Show spinner and disable form
  const showLoading = () => {
    submitButton.disabled = true;
    spinnerOverlay.classList.add('active');
    spinnerOverlay.setAttribute('aria-hidden', 'false');
    emailInput.disabled = true;
    passwordInput.disabled = true;
    hideError(); // Clear any previous errors
  };

  // Hide spinner and re-enable form
  const hideLoading = () => {
    submitButton.disabled = false;
    spinnerOverlay.classList.remove('active');
    spinnerOverlay.setAttribute('aria-hidden', 'true');
    emailInput.disabled = false;
    passwordInput.disabled = false;
  };

  // Display error message
  const showError = (message) => {
    if (errorContainer) {
      errorContainer.textContent = message;
      errorContainer.style.display = 'block';
      
      // Auto-hide error after 5 seconds
      setTimeout(() => {
        if (errorContainer) {
          errorContainer.style.display = 'none';
        }
      }, 5000);
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

    if (!email || !password) {
      showError('Please fill in all fields');
      return;
    }

    // Email format validation
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(email)) {
      showError('Please enter a valid email address');
      return;
    }

    // Start loading
    showLoading();

    try {
      // Check if login function exists from auth.js
      if (typeof login === 'function') {
        await login(email, password);
      } else {
        // Fallback to simulateLogin if login doesn't exist
        await simulateLogin(email, password);
      }
      
      // If successful, redirect to dashboard
      window.location.href = 'dashboard.html';
    } catch (err) {
      // Show error message
      showError(err.message || 'Login failed. Please try again.');
    } finally {
      // Always hide spinner
      hideLoading();
    }
  });

  // Optional: Clear error when user starts typing
  [emailInput, passwordInput].forEach(input => {
    input.addEventListener('input', () => {
      hideError();
    });
  });
});