// js/register.js
// Handles registration form submission with spinner loading animation

document.addEventListener('DOMContentLoaded', () => {
  const form = document.getElementById('form');
  const nameInput = document.getElementById('name');
  const emailInput = document.getElementById('email');
  const passwordInput = document.getElementById('password');
  const termsCheckbox = document.getElementById('terms');
  const registerButton = document.getElementById('register-button');
  const spinnerOverlay = document.getElementById('spinner-overlay');
  const errorContainer = document.getElementById('form-error');

  // Preserve existing validation and registration flow
  // Simulate API registration - replace with real fetch when ready
  const simulateRegistration = async (name, email, password, terms) => {
    // Fake API call - mimics network delay
    return new Promise((resolve, reject) => {
      setTimeout(() => {
        // Demo validation - keep existing behavior
        if (!terms) {
          reject(new Error('You must agree to the Terms of Service'));
          return;
        }
        
        if (name && email && password) {
          // Basic validation for demo
          if (password.length < 6) {
            reject(new Error('Password must be at least 6 characters'));
            return;
          }
          
          if (!email.includes('@')) {
            reject(new Error('Please enter a valid email address'));
            return;
          }
          
          resolve({ success: true, token: 'fake-jwt-token' });
        } else {
          reject(new Error('All fields are required'));
        }
      }, 1500); // 1.5s spinner display for demo
    });
  };

  // Show spinner and disable form
  const showLoading = () => {
    registerButton.disabled = true;
    spinnerOverlay.classList.add('active');
    spinnerOverlay.setAttribute('aria-hidden', 'false');
    nameInput.disabled = true;
    emailInput.disabled = true;
    passwordInput.disabled = true;
    if (termsCheckbox) termsCheckbox.disabled = true;
    hideError(); // Clear any previous errors
  };

  // Hide spinner and re-enable form
  const hideLoading = () => {
    registerButton.disabled = false;
    spinnerOverlay.classList.remove('active');
    spinnerOverlay.setAttribute('aria-hidden', 'true');
    nameInput.disabled = false;
    emailInput.disabled = false;
    passwordInput.disabled = false;
    if (termsCheckbox) termsCheckbox.disabled = false;
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
    const name = nameInput.value.trim();
    const email = emailInput.value.trim();
    const password = passwordInput.value;
    const terms = termsCheckbox ? termsCheckbox.checked : true; // Default to true if checkbox doesn't exist

    if (!name || !email || !password) {
      showError('Please fill in all fields');
      return;
    }

    // Email format validation
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(email)) {
      showError('Please enter a valid email address');
      return;
    }

    // Password length validation (can be customized)
    if (password.length < 6) {
      showError('Password must be at least 6 characters');
      return;
    }

    // Terms agreement validation
    if (termsCheckbox && !termsCheckbox.checked) {
      showError('You must agree to the Terms of Service');
      return;
    }

    // Start loading
    showLoading();

    try {
      // Call register function from auth.js (preserved)
      // This integrates with your existing auth system
      await register(name, email, password);
      
      // If successful, redirect to dashboard
      window.location.href = 'dashboard.html';
    } catch (err) {
      // Show error message
      showError(err.message || 'Registration failed. Please try again.');
    } finally {
      // Always hide spinner
      hideLoading();
    }
  });

  // Optional: Add password strength indicator integration
  // This can be expanded later with the existing CSS classes
  if (passwordInput) {
    passwordInput.addEventListener('input', () => {
      // Placeholder for future password strength feature
      // The CSS classes are already prepared
    });
  }
});