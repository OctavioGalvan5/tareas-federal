// Task & Expiration Notifications System
// Shows pop-up alerts for tasks and expirations due soon (0, 1, or 2 business days)

document.addEventListener('DOMContentLoaded', function () {
    checkTasksDueSoon();
    updateNotificationToggle();
});

function checkTasksDueSoon() {
    fetch('/api/tasks/due_soon')
        .then(response => response.json())
        .then(data => {
            const hasTasks = data.tasks && data.tasks.length > 0;
            const hasExpirations = data.expirations && data.expirations.length > 0;
            if (hasTasks || hasExpirations) {
                showNotificationModal(data.tasks || [], data.expirations || []);
            }
        })
        .catch(error => console.error('Error checking tasks:', error));
}

function showNotificationModal(tasks, expirations) {
    const content = document.getElementById('notificationContent');
    let html = '';

    // Show tasks section
    if (tasks.length > 0) {
        html += '<p style="margin-bottom: 0.5rem; color: #6366f1; font-weight: 700;"><i class="fas fa-tasks"></i> Tareas Próximas a Vencer</p>';
        html += '<ul class="notification-task-list">';

        tasks.forEach(task => {
            const priorityClass = task.priority.toLowerCase();
            let urgencyText = '';
            let urgencyColor = '';
            if (task.days_remaining === 0) {
                urgencyText = '¡VENCE HOY!';
                urgencyColor = '#dc2626';
            } else if (task.days_remaining === 1) {
                urgencyText = 'Vence mañana (1 día hábil)';
                urgencyColor = '#f59e0b';
            } else {
                urgencyText = `Vence en ${task.days_remaining} días hábiles`;
                urgencyColor = '#059669';
            }

            html += `
                <li class="notification-task-item priority-${priorityClass}" onclick="goToTask(${task.id})" style="cursor: pointer;">
                    <div class="task-icon"><i class="fas fa-tasks"></i></div>
                    <div class="task-info">
                        <h4>${escapeHtml(task.title)} <i class="fas fa-external-link-alt" style="font-size: 0.7rem; color: #94a3b8;"></i></h4>
                        <p style="color: ${urgencyColor}; font-weight: 700;"><i class="fas fa-exclamation-circle"></i> ${urgencyText}</p>
                        <p><i class="fas fa-calendar"></i> Fecha de vencimiento: ${task.due_date}</p>
                        ${task.description ? `<p class="task-desc">${escapeHtml(task.description)}</p>` : ''}
                        <span class="task-priority">${task.priority}</span>
                    </div>
                </li>
            `;
        });
        html += '</ul>';
    }

    // Show expirations section
    if (expirations.length > 0) {
        if (tasks.length > 0) {
            html += '<hr style="margin: 1.5rem 0; border: none; border-top: 1px solid #e2e8f0;">';
        }
        html += '<p style="margin-bottom: 0.5rem; color: #f59e0b; font-weight: 700;"><i class="fas fa-clock"></i> Vencimientos Próximos</p>';
        html += '<ul class="notification-task-list">';

        expirations.forEach(exp => {
            let urgencyText = '';
            let urgencyColor = '';
            if (exp.days_remaining === 0) {
                urgencyText = '¡VENCE HOY!';
                urgencyColor = '#dc2626';
            } else if (exp.days_remaining === 1) {
                urgencyText = 'Vence mañana (1 día hábil)';
                urgencyColor = '#f59e0b';
            } else {
                urgencyText = `Vence en ${exp.days_remaining} días hábiles`;
                urgencyColor = '#059669';
            }

            html += `
                <li class="notification-task-item expiration-item" onclick="goToExpirations()" style="cursor: pointer;">
                    <div class="task-icon" style="background: linear-gradient(135deg, #fef3c7 0%, #fde68a 100%); color: #d97706;"><i class="fas fa-clock"></i></div>
                    <div class="task-info">
                        <h4>${escapeHtml(exp.title)} <i class="fas fa-external-link-alt" style="font-size: 0.7rem; color: #94a3b8;"></i></h4>
                        <p style="color: ${urgencyColor}; font-weight: 700;"><i class="fas fa-exclamation-circle"></i> ${urgencyText}</p>
                        <p><i class="fas fa-calendar"></i> Fecha: ${exp.due_date}</p>
                        <p><i class="fas fa-user"></i> Creado por: ${escapeHtml(exp.creator)}</p>
                        ${exp.description ? `<p class="task-desc">${escapeHtml(exp.description)}</p>` : ''}
                    </div>
                </li>
            `;
        });
        html += '</ul>';
    }


    content.innerHTML = html;
    document.getElementById('notificationModal').style.display = 'flex';
}

function closeNotificationModal() {
    document.getElementById('notificationModal').style.display = 'none';
}

function toggleNotifications() {
    fetch('/api/user/toggle_notifications', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        }
    })
        .then(response => response.json())
        .then(data => {
            const toggle = document.getElementById('notificationToggle');
            if (data.notifications_enabled) {
                toggle.classList.add('active');
                alert('✅ Notificaciones activadas');
                checkTasksDueSoon();
            } else {
                toggle.classList.remove('active');
                alert('🔕 Notificaciones desactivadas');
                closeNotificationModal();
            }
        })
        .catch(error => console.error('Error toggling notifications:', error));
}

function updateNotificationToggle() {
    // This will be called from inline script in base.html
    // to check current user's notification status
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Navigation functions for clickable notifications
function goToTask(taskId) {
    closeNotificationModal();
    window.location.href = `/task/${taskId}`;
}

function goToExpirations() {
    closeNotificationModal();
    window.location.href = '/expirations';
}
