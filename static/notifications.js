// Task & Expiration Notifications System
// Shows pop-up alerts for tasks and expirations due soon or overdue

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
            const hasOverdueTasks = data.overdue_tasks && data.overdue_tasks.length > 0;
            const hasOverdueExpirations = data.overdue_expirations && data.overdue_expirations.length > 0;

            if (hasTasks || hasExpirations || hasOverdueTasks || hasOverdueExpirations) {
                showNotificationModal(
                    data.tasks || [],
                    data.expirations || [],
                    data.overdue_tasks || [],
                    data.overdue_expirations || []
                );
            }
        })
        .catch(error => console.error('Error checking tasks:', error));
}

function showNotificationModal(tasks, expirations, overdueTasks, overdueExpirations) {
    const content = document.getElementById('notificationContent');
    let html = '';

    // === OVERDUE SECTION (RED - MOST URGENT) ===
    if (overdueTasks.length > 0 || overdueExpirations.length > 0) {
        html += '<div style="margin-bottom: 1.5rem;">';
        html += '<p style="margin-bottom: 0.75rem; color: #dc2626; font-weight: 700; font-size: 1.1rem;"><i class="fas fa-exclamation-triangle"></i> ¡VENCIDAS!</p>';
        html += '<ul class="notification-task-list">';

        // Overdue Tasks
        overdueTasks.forEach(task => {
            const priorityClass = task.priority.toLowerCase();
            const daysText = task.days_overdue === 1 ? '1 día hábil' : `${task.days_overdue} días hábiles`;

            html += `
                <li class="notification-task-item overdue-item priority-${priorityClass}">
                    <div class="task-icon" style="background: linear-gradient(135deg, #fecaca 0%, #fca5a5 100%); color: #dc2626;"><i class="fas fa-times-circle"></i></div>
                    <div class="task-info">
                        <h4 onclick="goToTask(${task.id})" style="cursor: pointer;">${escapeHtml(task.title)} <i class="fas fa-external-link-alt" style="font-size: 0.7rem; color: #94a3b8;"></i></h4>
                        <p style="color: #dc2626; font-weight: 700;"><i class="fas fa-exclamation-triangle"></i> ¡VENCIDA hace ${daysText}!</p>
                        <p><i class="fas fa-calendar-times"></i> Venció el: ${task.due_date}</p>
                        ${task.description ? `<p class="task-desc">${escapeHtml(task.description)}</p>` : ''}
                        <div class="task-actions">
                            <span class="task-priority">${task.priority}</span>
                            <button class="postpone-btn" onclick="event.stopPropagation(); showPostponeMenu(${task.id}, this)">
                                <i class="fas fa-clock"></i> Posponer
                            </button>
                        </div>
                    </div>
                </li>
            `;
        });

        // Overdue Expirations
        overdueExpirations.forEach(exp => {
            const daysText = exp.days_overdue === 1 ? '1 día hábil' : `${exp.days_overdue} días hábiles`;

            html += `
                <li class="notification-task-item overdue-item expiration-overdue" onclick="goToExpirations()" style="cursor: pointer;">
                    <div class="task-icon" style="background: linear-gradient(135deg, #fecaca 0%, #fca5a5 100%); color: #dc2626;"><i class="fas fa-clock"></i></div>
                    <div class="task-info">
                        <h4>${escapeHtml(exp.title)} <i class="fas fa-external-link-alt" style="font-size: 0.7rem; color: #94a3b8;"></i></h4>
                        <p style="color: #dc2626; font-weight: 700;"><i class="fas fa-exclamation-triangle"></i> ¡VENCIDO hace ${daysText}!</p>
                        <p><i class="fas fa-calendar-times"></i> Venció el: ${exp.due_date}</p>
                        <p><i class="fas fa-user"></i> Creado por: ${escapeHtml(exp.creator)}</p>
                        ${exp.description ? `<p class="task-desc">${escapeHtml(exp.description)}</p>` : ''}
                    </div>
                </li>
            `;
        });

        html += '</ul>';
        html += '</div>';
    }

    // === DUE SOON TASKS SECTION ===
    if (tasks.length > 0) {
        if (overdueTasks.length > 0 || overdueExpirations.length > 0) {
            html += '<hr style="margin: 1.5rem 0; border: none; border-top: 2px solid #e2e8f0;">';
        }
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
                <li class="notification-task-item priority-${priorityClass}">
                    <div class="task-icon"><i class="fas fa-tasks"></i></div>
                    <div class="task-info">
                        <h4 onclick="goToTask(${task.id})" style="cursor: pointer;">${escapeHtml(task.title)} <i class="fas fa-external-link-alt" style="font-size: 0.7rem; color: #94a3b8;"></i></h4>
                        <p style="color: ${urgencyColor}; font-weight: 700;"><i class="fas fa-exclamation-circle"></i> ${urgencyText}</p>
                        <p><i class="fas fa-calendar"></i> Fecha de vencimiento: ${task.due_date}</p>
                        ${task.enabled_at ? `<p style="color: #8b5cf6;"><i class="fas fa-unlock"></i> Habilitada el: ${task.enabled_at}</p>` : ''}
                        ${task.description ? `<p class="task-desc">${escapeHtml(task.description)}</p>` : ''}
                        <div class="task-actions">
                            <span class="task-priority">${task.priority}</span>
                            <button class="postpone-btn" onclick="event.stopPropagation(); showPostponeMenu(${task.id}, this)">
                                <i class="fas fa-clock"></i> Posponer
                            </button>
                        </div>
                    </div>
                </li>
            `;
        });
        html += '</ul>';
    }

    // === DUE SOON EXPIRATIONS SECTION ===
    if (expirations.length > 0) {
        if (tasks.length > 0 || overdueTasks.length > 0 || overdueExpirations.length > 0) {
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
            const notificationText = toggle.querySelector('.notification-text');

            if (data.notifications_enabled) {
                toggle.classList.add('active');
                if (notificationText) {
                    notificationText.innerHTML = '<span style="color: #86efac;"><i class="fas fa-check-circle"></i> Activadas</span>';
                }
                checkTasksDueSoon();
            } else {
                toggle.classList.remove('active');
                if (notificationText) {
                    notificationText.innerHTML = '<span style="color: #fca5a5;"><i class="fas fa-times-circle"></i> Desactivadas</span>';
                }
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

// ========== POSTPONE FUNCTIONALITY ==========

function showPostponeMenu(taskId, buttonElement) {
    // Hide any existing menus first
    hidePostponeMenus();

    // Get tomorrow's date for the min attribute
    const tomorrow = new Date();
    tomorrow.setDate(tomorrow.getDate() + 1);
    const minDate = tomorrow.toISOString().split('T')[0];

    // Create the menu
    const menu = document.createElement('div');
    menu.className = 'postpone-menu';
    menu.id = `postpone-menu-${taskId}`;
    menu.innerHTML = `
        <div class="postpone-menu-header">Posponer hasta</div>
        <div class="postpone-option" onclick="postponeTask(${taskId}, 1)">
            <i class="fas fa-forward"></i> 1 día
        </div>
        <div class="postpone-option" onclick="postponeTask(${taskId}, 3)">
            <i class="fas fa-forward"></i> 3 días
        </div>
        <div class="postpone-option" onclick="postponeTask(${taskId}, 7)">
            <i class="fas fa-calendar-week"></i> 1 semana
        </div>
        <div class="postpone-option custom-date" onclick="toggleCustomDateInput(${taskId})">
            <i class="fas fa-calendar-alt"></i> Fecha personalizada
        </div>
        <div class="postpone-custom-input" id="custom-date-input-${taskId}">
            <input type="date" id="custom-date-${taskId}" min="${minDate}">
            <button class="confirm-btn" onclick="postponeTaskCustom(${taskId})">
                <i class="fas fa-check"></i> Confirmar
            </button>
        </div>
    `;

    // Position the menu near the button
    const rect = buttonElement.getBoundingClientRect();
    menu.style.position = 'fixed';
    menu.style.top = (rect.bottom + 5) + 'px';
    menu.style.left = rect.left + 'px';

    // Append to body to avoid overflow issues
    document.body.appendChild(menu);

    // Close menu when clicking outside
    setTimeout(() => {
        document.addEventListener('click', handleOutsideClick);
    }, 0);
}

function handleOutsideClick(event) {
    const menus = document.querySelectorAll('.postpone-menu');
    let clickedInside = false;

    menus.forEach(menu => {
        if (menu.contains(event.target)) {
            clickedInside = true;
        }
    });

    if (!clickedInside && !event.target.classList.contains('postpone-btn')) {
        hidePostponeMenus();
        document.removeEventListener('click', handleOutsideClick);
    }
}

function hidePostponeMenus() {
    const menus = document.querySelectorAll('.postpone-menu');
    menus.forEach(menu => menu.remove());
}

function toggleCustomDateInput(taskId) {
    const input = document.getElementById(`custom-date-input-${taskId}`);
    input.classList.toggle('show');
}

function postponeTask(taskId, days) {
    fetch(`/api/tasks/${taskId}/postpone`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ days: days })
    })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                hidePostponeMenus();
                showPostponeSuccess(data.message, data.new_due_date);
                // Refresh notifications after a short delay
                setTimeout(() => {
                    checkTasksDueSoon();
                }, 1500);
            } else {
                showPostponeError(data.message);
            }
        })
        .catch(error => {
            console.error('Error postponing task:', error);
            showPostponeError('Error al posponer la tarea');
        });
}

function postponeTaskCustom(taskId) {
    const dateInput = document.getElementById(`custom-date-${taskId}`);
    const customDate = dateInput.value;

    if (!customDate) {
        showPostponeError('Por favor selecciona una fecha');
        return;
    }

    fetch(`/api/tasks/${taskId}/postpone`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ custom_date: customDate })
    })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                hidePostponeMenus();
                showPostponeSuccess(data.message, data.new_due_date);
                // Refresh notifications after a short delay
                setTimeout(() => {
                    checkTasksDueSoon();
                }, 1500);
            } else {
                showPostponeError(data.message);
            }
        })
        .catch(error => {
            console.error('Error postponing task:', error);
            showPostponeError('Error al posponer la tarea');
        });
}

function showPostponeSuccess(message, newDate) {
    // Create a toast notification
    const toast = document.createElement('div');
    toast.style.cssText = `
        position: fixed;
        bottom: 20px;
        right: 20px;
        background: linear-gradient(135deg, #10b981 0%, #059669 100%);
        color: white;
        padding: 1rem 1.5rem;
        border-radius: 12px;
        box-shadow: 0 10px 40px rgba(0, 0, 0, 0.2);
        z-index: 10002;
        animation: fadeInUp 0.3s ease-out;
        display: flex;
        align-items: center;
        gap: 0.75rem;
        font-weight: 500;
    `;
    toast.innerHTML = `
        <i class="fas fa-check-circle" style="font-size: 1.25rem;"></i>
        <div>
            <div>${message}</div>
            <div style="font-size: 0.85rem; opacity: 0.9;">Nueva fecha: ${newDate}</div>
        </div>
    `;

    document.body.appendChild(toast);

    // Remove after 3 seconds
    setTimeout(() => {
        toast.style.animation = 'fadeOut 0.3s ease-out forwards';
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

function showPostponeError(message) {
    const toast = document.createElement('div');
    toast.style.cssText = `
        position: fixed;
        bottom: 20px;
        right: 20px;
        background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%);
        color: white;
        padding: 1rem 1.5rem;
        border-radius: 12px;
        box-shadow: 0 10px 40px rgba(0, 0, 0, 0.2);
        z-index: 10002;
        animation: fadeInUp 0.3s ease-out;
        display: flex;
        align-items: center;
        gap: 0.75rem;
        font-weight: 500;
    `;
    toast.innerHTML = `
        <i class="fas fa-exclamation-circle" style="font-size: 1.25rem;"></i>
        <div>${message}</div>
    `;

    document.body.appendChild(toast);

    setTimeout(() => {
        toast.style.animation = 'fadeOut 0.3s ease-out forwards';
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}
