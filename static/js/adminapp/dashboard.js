// ============================================
// J.J. DOSSEN ADMIN DASHBOARD - DASHBOARD JS
// Charts, Statistics, Interactive Elements
// ============================================

document.addEventListener('DOMContentLoaded', function() {
    
    // Initialize charts if Chart.js is loaded
    if (typeof Chart !== 'undefined') {
        // Patient Trends Chart
        const patientTrendsCtx = document.getElementById('patientTrendsChart');
        if (patientTrendsCtx) {
            new Chart(patientTrendsCtx, {
                type: 'line',
                data: {
                    labels: ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun'],
                    datasets: [{
                        label: 'Patients',
                        data: [65, 78, 82, 91, 88, 102],
                        borderColor: '#0A5C8E',
                        backgroundColor: 'rgba(10, 92, 142, 0.05)',
                        borderWidth: 3,
                        tension: 0.4,
                        fill: true,
                        pointBackgroundColor: '#0A5C8E',
                        pointBorderColor: '#fff',
                        pointBorderWidth: 2,
                        pointRadius: 4,
                        pointHoverRadius: 6
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: { display: false },
                        tooltip: {
                            backgroundColor: '#fff',
                            titleColor: '#111827',
                            bodyColor: '#6B7280',
                            borderColor: '#E5E7EB',
                            borderWidth: 1,
                            callbacks: {
                                label: function(context) {
                                    return `Patients: ${context.raw}`;
                                }
                            }
                        }
                    },
                    scales: {
                        y: {
                            beginAtZero: true,
                            grid: { color: 'rgba(0, 0, 0, 0.05)' },
                            ticks: { stepSize: 20 }
                        },
                        x: { grid: { display: false } }
                    }
                }
            });
        }
        
        // Referral Flow Chart
        const referralFlowCtx = document.getElementById('referralFlowChart');
        if (referralFlowCtx) {
            new Chart(referralFlowCtx, {
                type: 'doughnut',
                data: {
                    labels: ['CHW → Clinic', 'Clinic → Hospital', 'Hospital → Specialist'],
                    datasets: [{
                        data: [12, 5, 2],
                        backgroundColor: ['#0A5C8E', '#1E88E5', '#10B981'],
                        borderWidth: 0
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: { position: 'bottom' }
                    }
                }
            });
        }
    }
    
    // Animate statistics on load
    const statNumbers = document.querySelectorAll('.stat-value');
    statNumbers.forEach(stat => {
        const target = parseInt(stat.getAttribute('data-target') || stat.innerText);
        if (target && !isNaN(target)) {
            let current = 0;
            const increment = target / 50;
            const timer = setInterval(() => {
                current += increment;
                if (current >= target) {
                    stat.innerText = target.toLocaleString();
                    clearInterval(timer);
                } else {
                    stat.innerText = Math.floor(current).toLocaleString();
                }
            }, 20);
        }
    });
    
    // Resolve Alert Buttons
    const resolveButtons = document.querySelectorAll('.resolve-alert');
    resolveButtons.forEach(btn => {
        btn.addEventListener('click', function(e) {
            e.preventDefault();
            const alertId = this.getAttribute('data-alert-id');
            if (confirm('Mark this alert as resolved?')) {
                console.log(`Resolving alert ${alertId}`);
                const alertItem = this.closest('.alert-card, .alert-item');
                if (alertItem) {
                    alertItem.style.opacity = '0';
                    setTimeout(() => {
                        alertItem.remove();
                    }, 300);
                }
            }
        });
    });
    
    // Refresh Data Button
    const refreshBtn = document.getElementById('refreshData');
    if (refreshBtn) {
        refreshBtn.addEventListener('click', function() {
            this.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Refreshing...';
            setTimeout(() => {
                location.reload();
            }, 1000);
        });
    }
    
    console.log('Admin Dashboard - Dashboard JS Loaded');
});