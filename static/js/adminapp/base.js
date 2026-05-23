// ============================================
// J.J. DOSSEN ADMIN DASHBOARD - BASE JS
// Fixed Active Link Highlighting
// ============================================

document.addEventListener('DOMContentLoaded', function() {
    
    // Sidebar Toggle for Mobile
    const menuToggle = document.getElementById('menuToggle');
    const sidebar = document.getElementById('sidebar');
    
    if (menuToggle && sidebar) {
        menuToggle.addEventListener('click', function() {
            sidebar.classList.toggle('active');
        });
        
        // Close sidebar when clicking outside on mobile
        document.addEventListener('click', function(event) {
            const isClickInsideSidebar = sidebar.contains(event.target);
            const isClickOnToggle = menuToggle.contains(event.target);
            
            if (!isClickInsideSidebar && !isClickOnToggle && window.innerWidth <= 768) {
                sidebar.classList.remove('active');
            }
        });
    }
    
    // Handle window resize - reset sidebar state
    window.addEventListener('resize', function() {
        if (window.innerWidth > 768) {
            if (sidebar) {
                sidebar.classList.remove('active');
            }
        }
    });
    
    // ============================================
    // FIXED: Active Link Highlighting
    // ============================================
    const currentPath = window.location.pathname;
    const navLinks = document.querySelectorAll('.nav-link');
    
    // Remove all active classes first
    navLinks.forEach(link => {
        link.classList.remove('active');
    });
    
    // Check each link and add active class if href matches current path
    navLinks.forEach(link => {
        const href = link.getAttribute('href');
        
        if (href && href !== '#') {
            // Remove domain and query string for comparison
            let linkPath = href.split('?')[0];
            let currentPathWithoutQuery = currentPath.split('?')[0];
            
            // Exact match
            if (linkPath === currentPathWithoutQuery) {
                link.classList.add('active');
            }
            // Handle trailing slash
            else if (linkPath + '/' === currentPathWithoutQuery) {
                link.classList.add('active');
            }
            // Handle root path
            else if (linkPath === '/' && currentPathWithoutQuery === '') {
                link.classList.add('active');
            }
            // Handle partial matches for nested routes
            else if (currentPathWithoutQuery.startsWith(linkPath) && linkPath !== '/') {
                if (currentPathWithoutQuery === linkPath || 
                    currentPathWithoutQuery.startsWith(linkPath + '/')) {
                    link.classList.add('active');
                }
            }
        }
    });
    
    // Fallback for when no exact match is found
    const activeLinks = document.querySelectorAll('.nav-link.active');
    if (activeLinks.length === 0) {
        const pathSegments = currentPath.split('/').filter(seg => seg);
        if (pathSegments.length > 0) {
            const firstSegment = '/' + pathSegments[0];
            navLinks.forEach(link => {
                const href = link.getAttribute('href');
                if (href && href === firstSegment) {
                    link.classList.add('active');
                }
            });
        }
    }
    
    // Notification Button
    const notificationBtn = document.getElementById('notificationBtn');
    if (notificationBtn) {
        notificationBtn.addEventListener('click', function() {
            console.log('Notifications clicked');
        });
    }
    
    // Auto-hide alerts after 5 seconds
    const alerts = document.querySelectorAll('.alert-auto-hide');
    if (alerts.length) {
        setTimeout(() => {
            alerts.forEach(alert => {
                alert.style.opacity = '0';
                setTimeout(() => {
                    if (alert.parentNode) {
                        alert.remove();
                    }
                }, 300);
            });
        }, 5000);
    }
    
    // Tooltip functionality
    const tooltips = document.querySelectorAll('[data-tooltip]');
    tooltips.forEach(element => {
        element.addEventListener('mouseenter', function(e) {
            const tooltipText = this.getAttribute('data-tooltip');
            const tooltip = document.createElement('div');
            tooltip.className = 'custom-tooltip';
            tooltip.textContent = tooltipText;
            tooltip.style.cssText = `
                position: absolute;
                background: var(--text-primary);
                color: white;
                padding: 4px 8px;
                border-radius: 6px;
                font-size: 12px;
                white-space: nowrap;
                z-index: 1000;
                pointer-events: none;
            `;
            
            const rect = this.getBoundingClientRect();
            tooltip.style.top = rect.top - 30 + 'px';
            tooltip.style.left = rect.left + (rect.width / 2) - (tooltip.offsetWidth / 2) + 'px';
            
            document.body.appendChild(tooltip);
            
            this.addEventListener('mouseleave', function() {
                tooltip.remove();
            });
        });
    });
    
    console.log('Admin Dashboard - Base JS Loaded');
    console.log('Current Path:', currentPath);
});