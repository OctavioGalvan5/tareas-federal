// Task Notifications System
// Shows pop-up alerts for tasks due soon (0, 1, or 2 business days)

document.addEventListener('DOMContentLoaded', function () {
    checkTasksDueSoon();
    updateNotificationToggle();
});

function checkTasksDueSoon() {
    fetch('/api/tasks/due_soon')
        .then(response => response.json())
        .then(data => {
            if (data.tasks && data.tasks.length > 0) {
                showNotificationModal(data.tasks);
            }
        })
        .catch(error => console.error('Error checking tasks:', error));
}

function showNotificationModal(tasks) {
    const content = document.getElementById('notificationContent');
    let html = '<p style="margin-bottom: 1rem; color: #475569;">Las siguientes tareas están próximas a vencer:</p><ul class="notification-task-list">';

    tasks.forEach(task => {
        const priorityClass = task.priority.toLowerCase();

        // Determine urgency text and color based on days remaining
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
            <li class="notification-task-item priority-${priorityClass}">
                <div class="task-icon"><i class="fas fa-clock"></i></div>
                <div class="task-info">
                    <h4>${escapeHtml(task.title)}</h4>
                    <p style="color: ${urgencyColor}; font-weight: 700;"><i class="fas fa-exclamation-circle"></i> ${urgencyText}</p>
                    <p><i class="fas fa-calendar"></i> Fecha de vencimiento: ${task.due_date}</p>
                    ${task.description ? `<p class="task-desc">${escapeHtml(task.description)}</p>` : ''}
                    <span class="task-priority">${task.priority}</span>
                </div>
            </li>
        `;
    });

    html += '</ul>';
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
