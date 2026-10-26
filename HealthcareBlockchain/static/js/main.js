/**
 * Healthcare Record Management System
 * Vanilla JavaScript interactions: Demo quick-fill, hash copying, table filter, and confirmation dialogs.
 */

document.addEventListener('DOMContentLoaded', () => {
    // 1. Quick Demo Account Autofill on Login Page
    const demoButtons = document.querySelectorAll('.demo-chip');
    const usernameInput = document.getElementById('username');
    const passwordInput = document.getElementById('password');

    demoButtons.forEach(btn => {
        btn.addEventListener('click', (e) => {
            e.preventDefault();
            const u = btn.getAttribute('data-username');
            const p = btn.getAttribute('data-password');
            if (usernameInput && passwordInput) {
                usernameInput.value = u;
                passwordInput.value = p;
                // Subtle highlight animation
                usernameInput.style.borderColor = 'var(--primary)';
                passwordInput.style.borderColor = 'var(--primary)';
                setTimeout(() => {
                    usernameInput.style.borderColor = '';
                    passwordInput.style.borderColor = '';
                }, 800);
            }
        });
    });

    // 2. Alert Dismissal
    const closeButtons = document.querySelectorAll('.alert-close');
    closeButtons.forEach(btn => {
        btn.addEventListener('click', () => {
            const alertBox = btn.closest('.alert');
            if (alertBox) {
                alertBox.style.opacity = '0';
                alertBox.style.transform = 'translateY(-10px)';
                alertBox.style.transition = 'all 0.2s ease';
                setTimeout(() => alertBox.remove(), 200);
            }
        });
    });

    // 3. Table Search / Filtering
    const searchInputs = document.querySelectorAll('.table-search-input');
    searchInputs.forEach(input => {
        const tableId = input.getAttribute('data-target-table');
        const targetTable = document.getElementById(tableId);
        if (!targetTable) return;

        input.addEventListener('keyup', () => {
            const query = input.value.toLowerCase().trim();
            const rows = targetTable.querySelectorAll('tbody tr');
            rows.forEach(row => {
                const text = row.textContent.toLowerCase();
                row.style.display = text.includes(query) ? '' : 'none';
            });
        });
    });

    // 4. Click to Copy Hash
    const copyBadges = document.querySelectorAll('.hash-copyable');
    copyBadges.forEach(badge => {
        badge.style.cursor = 'pointer';
        badge.title = 'Click to copy full SHA-256 hash';
        badge.addEventListener('click', () => {
            const fullHash = badge.getAttribute('data-full-hash') || badge.textContent.trim();
            navigator.clipboard.writeText(fullHash).then(() => {
                const origText = badge.textContent;
                badge.textContent = 'COPIED!';
                badge.style.backgroundColor = 'var(--success-bg)';
                badge.style.color = 'var(--success-text)';
                setTimeout(() => {
                    badge.textContent = origText;
                    badge.style.backgroundColor = '';
                    badge.style.color = '';
                }, 1200);
            }).catch(err => {
                console.error('Failed to copy: ', err);
            });
        });
    });

    // 5. Confirmation for critical actions
    const confirmButtons = document.querySelectorAll('[data-confirm]');
    confirmButtons.forEach(btn => {
        btn.addEventListener('click', (e) => {
            const msg = btn.getAttribute('data-confirm') || 'Are you sure you want to proceed?';
            if (!confirm(msg)) {
                e.preventDefault();
            }
        });
    });
});
