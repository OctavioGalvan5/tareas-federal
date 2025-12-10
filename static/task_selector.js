/**
 * Task Selector Modal for Parent Task Selection
 * Provides search and selection functionality for linking tasks in a hierarchy
 */

let selectedParentTask = null;

function openTaskSelector() {
    const modal = document.getElementById('taskSelectorModal');
    if (modal) {
        modal.style.display = 'flex';
        document.getElementById('taskSearchInput').focus();
        // Clear previous search
        document.getElementById('taskSearchInput').value = '';
        document.getElementById('taskSearchResults').innerHTML = '';
    }
}

function closeTaskSelector() {
    const modal = document.getElementById('taskSelectorModal');
    if (modal) {
        modal.style.display = 'none';
    }
}

function searchTasks() {
    const query = document.getElementById('taskSearchInput').value.trim();
    const resultsContainer = document.getElementById('taskSearchResults');

    if (query.length < 2) {
        resultsContainer.innerHTML = '<p style="text-align: center; color: #64748b; padding: 2rem;">Escribe al menos 2 caracteres para buscar...</p>';
        return;
    }

    // Get current task ID to exclude it from results (if editing)
    const currentTaskId = document.getElementById('current_task_id')?.value;
    let url = `/api/tasks/search?q=${encodeURIComponent(query)}`;
    if (currentTaskId) {
        url += `&exclude_id=${currentTaskId}`;
    }

    // Show loading
    resultsContainer.innerHTML = '<p style="text-align: center; color: #64748b; padding: 2rem;"><i class="fas fa-spinner fa-spin"></i> Buscando...</p>';

    fetch(url)
        .then(response => response.json())
        .then(data => {
            if (data.tasks.length === 0) {
                resultsContainer.innerHTML = '<p style="text-align: center; color: #64748b; padding: 2rem;">No se encontraron tareas</p>';
                return;
            }

            let html = '<div class="task-list">';
            data.tasks.forEach(task => {
                const priorityColors = {
                    'Urgente': '#ef4444',
                    'Media': '#f59e0b',
                    'Normal': '#3b82f6'
                };
                const priorityColor = priorityColors[task.priority] || '#3b82f6';

                html += `
                    <div class="task-item" onclick="selectParentTask(${task.id}, '${task.title.replace(/'/g, "\\'")}')">
                        <div class="task-item-header">
                            <span class="task-id">#${task.id}</span>
                            <span class="task-priority" style="background: ${priorityColor};">${task.priority}</span>
                        </div>
                        <div class="task-item-title">${task.title}</div>
                        <div class="task-item-meta">
                            <span><i class="fas fa-calendar"></i> ${task.due_date}</span>
                            <span><i class="fas fa-user"></i> ${task.assignees || 'Sin asignar'}</span>
                        </div>
                    </div>
                `;
            });
            html += '</div>';

            resultsContainer.innerHTML = html;
        })
        .catch(error => {
            console.error('Error searching tasks:', error);
            resultsContainer.innerHTML = '<p style="text-align: center; color: #ef4444; padding: 2rem;">Error al buscar tareas</p>';
        });
}

function selectParentTask(taskId, taskTitle) {
    selectedParentTask = { id: taskId, title: taskTitle };

    // Update hidden input
    document.getElementById('parent_id').value = taskId;

    // Update display
    const display = document.getElementById('parentTaskDisplay');
    display.innerHTML = `
        <div style="display: flex; align-items: center; gap: 0.5rem; padding: 0.75rem; background: #f0f9ff; border: 1px solid #bae6fd; border-radius: 6px;">
            <i class="fas fa-link" style="color: #0284c7;"></i>
            <span style="flex: 1; color: #0c4a6e; font-weight: 500;">#${taskId} - ${taskTitle}</span>
            <button type="button" onclick="clearParentTask()" class="btn-clear-parent" title="Quitar tarea padre">
                <i class="fas fa-times"></i>
            </button>
        </div>
    `;

    closeTaskSelector();
}

function clearParentTask() {
    selectedParentTask = null;
    document.getElementById('parent_id').value = '';
    document.getElementById('parentTaskDisplay').innerHTML = '<span style="color: #9ca3af;">Sin tarea padre</span>';
}

// Debounce search to avoid too many requests
let searchTimeout;
document.addEventListener('DOMContentLoaded', function () {
    const searchInput = document.getElementById('taskSearchInput');
    if (searchInput) {
        searchInput.addEventListener('input', function () {
            clearTimeout(searchTimeout);
            searchTimeout = setTimeout(searchTasks, 300);
        });

        // Search on enter key
        searchInput.addEventListener('keypress', function (e) {
            if (e.key === 'Enter') {
                e.preventDefault();
                searchTasks();
            }
        });
    }

    // Close modal on outside click
    const modal = document.getElementById('taskSelectorModal');
    if (modal) {
        modal.addEventListener('click', function (e) {
            if (e.target === modal) {
                closeTaskSelector();
                closeChildTaskSelector();
            }
        });
    }
});

// ===== CHILD TASK SELECTOR =====
let isSelectingChild = false;

function openChildTaskSelector() {
    isSelectingChild = true;
    const modal = document.getElementById('taskSelectorModal');
    if (modal) {
        // Update modal title for child selection
        const modalTitle = modal.querySelector('.modal-header h3');
        if (modalTitle) {
            modalTitle.innerHTML = '<i class="fas fa-sitemap"></i> Agregar Subtarea';
        }
        modal.style.display = 'flex';
        document.getElementById('taskSearchInput').focus();
        document.getElementById('taskSearchInput').value = '';
        document.getElementById('taskSearchResults').innerHTML = '';
    }
}

function closeChildTaskSelector() {
    isSelectingChild = false;
    const modal = document.getElementById('taskSelectorModal');
    if (modal) {
        // Restore original title
        const modalTitle = modal.querySelector('.modal-header h3');
        if (modalTitle) {
            modalTitle.innerHTML = '<i class="fas fa-search"></i> Seleccionar Tarea Padre';
        }
        modal.style.display = 'none';
    }
}

function addChildTask(taskId, taskTitle) {
    const childIdsInput = document.getElementById('child_ids');
    if (!childIdsInput) return;

    // Get current child IDs
    let currentIds = childIdsInput.value ? childIdsInput.value.split(',').filter(id => id) : [];

    // Check if already added
    if (currentIds.includes(String(taskId))) {
        alert('Esta tarea ya está vinculada como subtarea');
        return;
    }

    // Add new ID
    currentIds.push(String(taskId));
    childIdsInput.value = currentIds.join(',');

    // Update display
    const display = document.getElementById('childTasksDisplay');

    // Remove "Sin subtareas" message if present
    const noChildrenMsg = display.querySelector('span[style*="color: #9ca3af"]');
    if (noChildrenMsg) {
        noChildrenMsg.remove();
    }

    // Add new child item
    const newChild = document.createElement('div');
    newChild.className = 'child-task-item';
    newChild.setAttribute('data-child-id', taskId);
    newChild.style.cssText = 'display: flex; align-items: center; gap: 0.5rem; padding: 0.5rem 0.75rem; background: #f0fdf4; border: 1px solid #bbf7d0; border-radius: 6px;';
    newChild.innerHTML = `
        <i class="fas fa-level-down-alt" style="color: #16a34a;"></i>
        <span style="flex: 1; color: #166534; font-weight: 500;">#${taskId} - ${taskTitle}</span>
        <button type="button" onclick="removeChildTask(${taskId})" class="btn-clear-parent" title="Quitar subtarea" style="background: none; border: none; color: #dc2626; cursor: pointer; padding: 0.25rem 0.5rem;">
            <i class="fas fa-times"></i>
        </button>
    `;
    display.appendChild(newChild);

    closeChildTaskSelector();
}

function removeChildTask(taskId) {
    const childIdsInput = document.getElementById('child_ids');
    if (!childIdsInput) return;

    // Remove ID from list
    let currentIds = childIdsInput.value ? childIdsInput.value.split(',').filter(id => id) : [];
    currentIds = currentIds.filter(id => id !== String(taskId));
    childIdsInput.value = currentIds.join(',');

    // Remove from display
    const display = document.getElementById('childTasksDisplay');
    const childItem = display.querySelector(`[data-child-id="${taskId}"]`);
    if (childItem) {
        childItem.remove();
    }

    // Show "Sin subtareas" message if no children left
    if (currentIds.length === 0) {
        display.innerHTML = '<span style="color: #9ca3af;">Sin subtareas vinculadas</span>';
    }
}

// Override selectParentTask to handle both modes
const originalSelectParentTask = selectParentTask;
selectParentTask = function (taskId, taskTitle) {
    if (isSelectingChild) {
        addChildTask(taskId, taskTitle);
    } else {
        originalSelectParentTask(taskId, taskTitle);
    }
};
