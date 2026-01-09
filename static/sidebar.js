/**
 * Sidebar Toggle Functionality
 * - Handles expand/collapse state
 * - Persists state to localStorage
 * - Mobile responsive behavior
 */

document.addEventListener('DOMContentLoaded', function () {
    const sidebar = document.querySelector('.sidebar');
    const toggleBtn = document.querySelector('.sidebar-toggle');
    const mobileMenuBtn = document.querySelector('.mobile-menu-btn');
    const overlay = document.querySelector('.sidebar-overlay');

    // Storage key for sidebar state
    const STORAGE_KEY = 'sidebar_collapsed';

    // Initialize sidebar state from localStorage
    function initSidebarState() {
        const isCollapsed = localStorage.getItem(STORAGE_KEY) === 'true';
        if (isCollapsed && window.innerWidth > 992) {
            sidebar.classList.add('collapsed');
        }
    }

    // Toggle sidebar collapsed state
    function toggleSidebar() {
        sidebar.classList.toggle('collapsed');
        const isCollapsed = sidebar.classList.contains('collapsed');
        localStorage.setItem(STORAGE_KEY, isCollapsed);
    }

    // Toggle mobile menu
    function toggleMobileMenu() {
        sidebar.classList.toggle('mobile-open');
        overlay.classList.toggle('active');
        document.body.style.overflow = sidebar.classList.contains('mobile-open') ? 'hidden' : '';
    }

    // Close mobile menu
    function closeMobileMenu() {
        sidebar.classList.remove('mobile-open');
        overlay.classList.remove('active');
        document.body.style.overflow = '';
    }

    // Event listeners
    if (toggleBtn) {
        toggleBtn.addEventListener('click', function (e) {
            e.preventDefault();
            if (window.innerWidth > 992) {
                toggleSidebar();
            } else {
                closeMobileMenu();
            }
        });
    }

    if (mobileMenuBtn) {
        mobileMenuBtn.addEventListener('click', toggleMobileMenu);
    }

    if (overlay) {
        overlay.addEventListener('click', closeMobileMenu);
    }

    // Handle window resize
    let resizeTimer;
    window.addEventListener('resize', function () {
        clearTimeout(resizeTimer);
        resizeTimer = setTimeout(function () {
            if (window.innerWidth > 992) {
                closeMobileMenu();
                // Restore collapsed state on desktop
                const isCollapsed = localStorage.getItem(STORAGE_KEY) === 'true';
                if (isCollapsed) {
                    sidebar.classList.add('collapsed');
                }
            } else {
                // Remove collapsed state on mobile
                sidebar.classList.remove('collapsed');
            }
        }, 100);
    });

    // Initialize
    initSidebarState();

    // Mark current page as active
    const currentPath = window.location.pathname;
    document.querySelectorAll('.nav-link').forEach(link => {
        const href = link.getAttribute('href');
        if (href === currentPath || (currentPath === '/' && href === '/')) {
            link.classList.add('active');
        }
    });
});
