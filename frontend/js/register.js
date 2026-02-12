// js/register.js
// Handles registration form submission with spinner loading animation and toast notifications

document.addEventListener('DOMContentLoaded', () => {
  const form = document.getElementById('form');
  const nameInput = document.getElementById('name');
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

  // Simulate API registration - replace with real fetch when ready
  const simulateRegistration = async (name, email, password) => {
    // Fake API call - mimics network delay
    return new Promise((resolve, reject) => {
      setTimeout(() => {
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
          
          // Check if email already exists (demo)
          if (email === 'demo@example.com') {
            reject(new Error('Email already registered'));
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
    submitButton.disabled = true;
    spinnerOverlay.classList.add('active');
    spinnerOverlay.setAttribute('aria-hidden', 'false');
    nameInput.disabled = true;
    emailInput.disabled = true;
    passwordInput.disabled = true;
  };

  // Hide spinner and re-enable form
  const hideLoading = () => {
    submitButton.disabled = false;
    spinnerOverlay.classList.remove('active');
    spinnerOverlay.setAttribute('aria-hidden', 'true');
    nameInput.disabled = false;
    emailInput.disabled = false;
    passwordInput.disabled = false;
  };

  // Form submit handler
  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    
    // Basic validation
    const name = nameInput.value.trim();
    const email = emailInput.value.trim();
    const password = passwordInput.value;

    if (!name || !email || !password) {
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

    // Password length validation
    if (password.length < 6) {
      toast.warning('Password must be at least 6 characters for security', { 
        duration: 5000,
        showProgress: true 
      });
      return;
    }

    // Start loading
    showLoading();

    try {
      // Check if register function exists (from auth.js)
      if (typeof register === 'function') {
        await register(name, email, password);
      } else {
        // Fallback to simulateRegistration if register doesn't exist
        await simulateRegistration(name, email, password);
      }
      
      // Show success message before redirect
      toast.success('Account created successfully! Redirecting to dashboard...', { 
        duration: 2500,
        showProgress: true
      });
      
      // If successful, redirect to dashboard
      setTimeout(() => {
        window.location.href = 'dashboard.html';
      }, 2000);
      
    } catch (err) {
      // Show error message as toast
      toast.error(err.message || 'Registration failed. Please try again.', { 
        duration: 5000,
        showProgress: true
      });
    } finally {
      // Always hide spinner
      hideLoading();
    }
  });

  // Optional: Show welcome message on page load
  setTimeout(() => {
    toast.info('Join Smart Price Tracker today!', { 
      duration: 4000,
      showProgress: true
    });
  }, 500);

  // Remove error styling on input
  [nameInput, emailInput, passwordInput].forEach(input => {
    input.addEventListener('input', () => {
      input.classList.remove('error');
    });
  });

  // Optional: Add password strength indicator integration
  if (passwordInput) {
    passwordInput.addEventListener('input', () => {
      const password = passwordInput.value;
      
      // Simple password strength indicator
      if (password.length === 0) {
        // No indicator needed
      } else if (password.length < 6) {
        toast.warning('Weak password - minimum 6 characters required', { 
          duration: 2000,
          showProgress: false,
          showClose: true
        });
      } else if (password.length < 10) {
        toast.info('Medium password strength', { 
          duration: 2000,
          showProgress: false,
          showClose: true
        });
      } else {
        toast.success('Strong password!', { 
          duration: 2000,
          showProgress: false,
          showClose: true
        });
      }
    });
  }
});