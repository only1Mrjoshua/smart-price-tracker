// mobile-menu.js - Mobile menu functionality for all pages

// Initialize mobile menu
function initMobileMenu() {
  const menuToggle = document.getElementById('menuToggle');
  const closeMenu = document.getElementById('closeMenu');
  const mobileMenuOverlay = document.getElementById('mobileMenuOverlay');
  const mobileMenu = document.getElementById('mobileMenu');
  
  // Check if elements exist
  if (!menuToggle || !closeMenu || !mobileMenuOverlay || !mobileMenu) {
    console.warn('Mobile menu elements not found');
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
    link.addEventListener('click', () => {
      setTimeout(closeMobileMenu, 300);
    });
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
  
  console.log('Mobile menu initialized');
}

// Initialize mobile menu when DOM is loaded
document.addEventListener('DOMContentLoaded', initMobileMenu);