// js/login.js
// Handles login form submission with spinner loading animation and toast notifications

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
  };

  // Hide spinner and re-enable form
  const hideLoading = () => {
    submitButton.disabled = false;
    spinnerOverlay.classList.remove('active');
    spinnerOverlay.setAttribute('aria-hidden', 'true');
    emailInput.disabled = false;
    passwordInput.disabled = false;
  };

  // Form submit handler
  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    
    // Basic validation
    const email = emailInput.value.trim();
    const password = passwordInput.value;

    if (!email || !password) {
      toast.error('Please fill in all fields', { 
        duration: 4000,
        showProgress: true 
      });
      return;
    }

    // Email format validation
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(email)) {
      toast.error('Please enter a valid email address', { 
        duration: 4000,
        showProgress: true 
      });
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
      
      // Show success message before redirect
      toast.success('Login successful! Redirecting to dashboard...', { 
        duration: 2000,
        showProgress: true
      });
      
      // If successful, redirect to dashboard
      setTimeout(() => {
        window.location.href = 'dashboard.html';
      }, 1500);
      
    } catch (err) {
      // Show error message as toast
      toast.error(err.message || 'Login failed. Please try again.', { 
        duration: 5000,
        showProgress: true
      });
    } finally {
      // Always hide spinner
      hideLoading();
    }
  });

  // Optional: Show welcome toast on page load
  setTimeout(() => {
    toast.info('Welcome back! Please log in to continue.', { 
      duration: 4000,
      showProgress: true
    });
  }, 500);

  // Remove error styling on input
  [emailInput, passwordInput].forEach(input => {
    input.addEventListener('input', () => {
      input.classList.remove('error');
    });
  });
});