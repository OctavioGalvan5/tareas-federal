from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, make_response
from flask_login import login_user, logout_user, login_required, current_user
from extensions import db
from models import User, Task, Tag, TaskTemplate
from datetime import datetime, date, timedelta
from pdf_utils import generate_task_pdf
from excel_utils import generate_task_excel
from io import BytesIO
from utils import calculate_business_days_until
from sqlalchemy.orm import joinedload

main_bp = Blueprint('main', __name__)
auth_bp = Blueprint('auth', __name__)
admin_bp = Blueprint('admin', __name__)

# --- Auth Routes ---
@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        print(f"DEBUG: Login attempt for username='{username}', password='{password}'")
        
        user = User.query.filter_by(username=username).first()
        print(f"DEBUG: User found: {user}")
        
        if user:
            check = user.check_password(password)
            print(f"DEBUG: Password check result: {check}")
            if check:
                login_user(user)
                return redirect(url_for('main.dashboard'))
        
        print("DEBUG: Login failed")
        flash('Usuario o contraseña incorrectos.', 'danger')
            
    return render_template('login.html')

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('auth.login'))

# --- Main Routes ---
@main_bp.route('/')
@login_required
def dashboard():
    # Filter logic
    filter_assignee = request.args.get('assignee')
    filter_creator = request.args.get('creator')
    filter_status = request.args.get('status')
    filter_tag = request.args.get('tag_filter')  # AGREGADO
    sort_order = request.args.get('sort', 'asc')  # Default: ascending

    # Base query: Show ALL tasks to ALL users by default
    # Optimize: Eager load assignees and tags to prevent N+1 queries
    tasks_query = Task.query.options(joinedload(Task.assignees), joinedload(Task.tags))
    
    if filter_assignee:
        tasks_query = tasks_query.filter(Task.assignees.any(id=filter_assignee))
    
    if filter_creator:
        tasks_query = tasks_query.filter(Task.creator_id == filter_creator)
        
    # Handle status filter - exclude 'Anulado' by default
    if filter_status:
        if filter_status in ['Pending', 'Completed', 'Anulado']:
            tasks_query = tasks_query.filter(Task.status == filter_status)
    else:
        # By default, exclude 'Anulado' tasks
        tasks_query = tasks_query.filter(Task.status != 'Anulado')

    if filter_tag:  # NUEVO
        tasks_query = tasks_query.filter(Task.tags.any(id=int(filter_tag)))

    # Search filter
    search_query = request.args.get('q')
    if search_query:
        search_term = f"%{search_query}%"
        tasks_query = tasks_query.filter(
            (Task.title.ilike(search_term)) | 
            (Task.description.ilike(search_term))
        )
        
    # Sort by due_date - ascending or descending
    if sort_order == 'desc':
        tasks = tasks_query.order_by(Task.due_date.desc()).all()
    else:
        tasks = tasks_query.order_by(Task.due_date.asc()).all()
    
    # Check for tasks due today for highlighting
    today = date.today()
    
    users = User.query.all() # For filters
    all_tags = Tag.query.order_by(Tag.name).all()  # NUEVO
    
    return render_template('dashboard.html', tasks=tasks, today=today, users=users, all_tags=all_tags, sort_order=sort_order)

@main_bp.route('/task/new', methods=['GET', 'POST'])
@login_required
def create_task():
    users = User.query.all()
    available_tags = Tag.query.order_by(Tag.name).all()
    templates = TaskTemplate.query.order_by(TaskTemplate.name).all()

    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description')
        priority = request.form.get('priority')
        due_date_str = request.form.get('due_date')
        assignee_ids = request.form.getlist('assignees')
        time_spent_str = request.form.get('time_spent')
        
        due_date = datetime.strptime(due_date_str, '%Y-%m-%d')
        
        # Parse time_spent (in minutes)
        time_spent = None
        if time_spent_str and time_spent_str.strip():
            try:
                time_spent = int(time_spent_str)
            except ValueError:
                time_spent = None
        
        new_task = Task(
            title=title,
            description=description,
            priority=priority,
            due_date=due_date,
            creator_id=current_user.id,
            time_spent=time_spent
        )
        
        # Add assignees
        for user_id in assignee_ids:
            user = User.query.get(int(user_id))
            if user:
                new_task.assignees.append(user)

        # Add tags
        tag_ids = request.form.getlist('tags')
        for tag_id in tag_ids:
            tag = Tag.query.get(int(tag_id))
            if tag:
                new_task.tags.append(tag)
                
        db.session.add(new_task)
        db.session.commit()
        flash('Tarea creada exitosamente.', 'success')
        return redirect(url_for('main.dashboard'))
        
    return render_template('create_task.html', users=users, available_tags=available_tags, templates=templates)

@main_bp.route('/task/<int:task_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_task(task_id):
    task = Task.query.get_or_404(task_id)
    
    # Verify user has access to this task (either creator or assignee)
    # Ideally only creator or admin should edit, or maybe assignees too?
    # For now let's allow creator and assignees to edit
    if task.creator_id != current_user.id and current_user not in task.assignees and not current_user.is_admin:
        flash('No tienes permiso para editar esta tarea.', 'danger')
        return redirect(url_for('main.dashboard'))

    users = User.query.all()
    available_tags = Tag.query.order_by(Tag.name).all()

    if request.method == 'POST':
        task.title = request.form.get('title')
        task.description = request.form.get('description')
        task.status = request.form.get('status') # Update status
        
        # Update priority and due_date - ONLY if user is admin
        if current_user.is_admin:
            task.priority = request.form.get('priority')
            due_date_str = request.form.get('due_date')
            if due_date_str:
                task.due_date = datetime.strptime(due_date_str, '%Y-%m-%d')
        
        # Update time_spent - ONLY if user is admin
        if current_user.is_admin:
            time_spent_str = request.form.get('time_spent')
            if time_spent_str and time_spent_str.strip():
                try:
                    task.time_spent = int(time_spent_str)
                except ValueError:
                    pass  # Keep existing value if invalid
            else:
                task.time_spent = None
        
        # Update assignees - ONLY if user is admin
        if current_user.is_admin:
            assignee_ids = request.form.getlist('assignees')
            task.assignees = [] # Clear current assignees
            for user_id in assignee_ids:
                user = User.query.get(int(user_id))
                if user:
                    task.assignees.append(user)

        # Update tags
        tag_ids = request.form.getlist('tags')
        task.tags = [] # Clear current tags
        for tag_id in tag_ids:
            tag = Tag.query.get(int(tag_id))
            if tag:
                task.tags.append(tag)
        
        # Handle completion tracking if status changed to Completed
        if task.status == 'Completed' and not task.completed_at:
             task.completed_by_id = current_user.id
             task.completed_at = datetime.now()
        elif task.status == 'Pending':
             task.completed_by_id = None
             task.completed_at = None

        # Track edit history
        task.last_edited_by_id = current_user.id
        task.last_edited_at = datetime.now()

        db.session.commit()
        flash('Tarea actualizada exitosamente.', 'success')
        return redirect(url_for('main.dashboard'))
        
        return redirect(url_for('main.dashboard'))
        
    return render_template('edit_task.html', task=task, users=users, available_tags=available_tags)

@main_bp.route('/task/<int:task_id>')
@login_required
def task_details(task_id):
    task = Task.query.get_or_404(task_id)
    return render_template('task_details.html', task=task)

@main_bp.route('/calendar')
@login_required
def calendar():
    # Get filter parameters
    period = request.args.get('period', 'all')  # today, week, month, all
    start_date_str = request.args.get('start_date')
    end_date_str = request.args.get('end_date')
    filter_creator = request.args.get('creator')
    
    # Base query: tasks assigned to current user
    query = Task.query.options(joinedload(Task.assignees), joinedload(Task.tags)).filter(Task.assignees.any(id=current_user.id))
    
    if filter_creator:
        query = query.filter(Task.creator_id == filter_creator)
    
    # Apply date filters
    today = date.today()
    
    if period == 'today':
        query = query.filter(db.func.date(Task.due_date) == today)
    elif period == 'week':
        week_start = today - timedelta(days=today.weekday())
        week_end = week_start + timedelta(days=6)
        query = query.filter(db.func.date(Task.due_date) >= week_start,
                           db.func.date(Task.due_date) <= week_end)
    elif period == 'month':
        month_start = today.replace(day=1)
        # Get last day of month
        if today.month == 12:
            month_end = today.replace(day=31)
        else:
            month_end = (today.replace(month=today.month + 1, day=1) - timedelta(days=1))
        query = query.filter(db.func.date(Task.due_date) >= month_start,
                           db.func.date(Task.due_date) <= month_end)
    elif start_date_str and end_date_str:
        # Custom date range
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
        query = query.filter(db.func.date(Task.due_date) >= start_date,
                           db.func.date(Task.due_date) <= end_date)
    # else: period == 'all' - no date filtering
    
    tasks = query.order_by(Task.due_date.asc()).all()
    users = User.query.all()
    
    return render_template('calendar.html', tasks=tasks, current_period=period, today=today, users=users)

@main_bp.route('/task/<int:task_id>/toggle', methods=['POST'])
@login_required
def toggle_task_status(task_id):
    task = Task.query.get_or_404(task_id)
    
    # Verify user has access to this task (either creator or assignee)
    if task.creator_id != current_user.id and current_user not in task.assignees:
        return jsonify({'success': False, 'error': 'Acceso denegado'}), 403
    
    # Toggle status and track completion
    if task.status == 'Pending':
        task.status = 'Completed'
        task.completed_by_id = current_user.id
        task.completed_at = datetime.now()
    else:
        task.status = 'Pending'
        task.completed_by_id = None
        task.completed_at = None
    
    db.session.commit()
    
    return jsonify({
        'success': True,
        'task_id': task.id,
        'new_status': task.status
    })

@main_bp.route('/task/<int:task_id>/anular', methods=['POST'])
@login_required
def anular_task(task_id):
    """Mark a task as 'Anulado' (soft delete)"""
    task = Task.query.get_or_404(task_id)
    
    # Only creator or admin can anular
    if task.creator_id != current_user.id and not current_user.is_admin:
        return jsonify({'success': False, 'error': 'Solo el creador o un admin puede anular esta tarea'}), 403
    
    task.status = 'Anulado'
    task.completed_by_id = current_user.id  # Track who anulled it
    task.completed_at = datetime.now()  # Track when
    
    db.session.commit()
    
    return jsonify({
        'success': True,
        'task_id': task.id,
        'new_status': 'Anulado'
    })

@main_bp.route('/export_pdf')
@login_required
def export_pdf():
    # Re-use filter logic from dashboard
    filter_assignee = request.args.get('assignee')
    filter_creator = request.args.get('creator')
    filter_status = request.args.get('status')
    
    # Calendar specific filters
    period = request.args.get('period')
    start_date_str = request.args.get('start_date')
    end_date_str = request.args.get('end_date')
    
    # Base query - start without user filter to match dashboard behavior
    query = Task.query.options(joinedload(Task.assignees), joinedload(Task.tags))
    
    filters = {}
    
    # Apply Assignee Filter
    if filter_assignee:
        query = query.filter(Task.assignees.any(id=filter_assignee))
        assignee = User.query.get(filter_assignee)
        filters['assignee_name'] = assignee.full_name if assignee else 'Desconocido'
    # If no assignee filter, show ALL tasks (matching dashboard behavior)
    
    # Apply Creator Filter
    if filter_creator:
        query = query.filter(Task.creator_id == filter_creator)
        creator = User.query.get(filter_creator)
        filters['creator_name'] = creator.full_name if creator else 'Desconocido'
        filters['creator'] = filter_creator
        
    # Apply Status Filter - exclude 'Anulado' by default like dashboard
    if filter_status:
        if filter_status in ['Pending', 'Completed', 'Anulado']:
            query = query.filter(Task.status == filter_status)
            filters['status'] = filter_status
    else:
        # By default, exclude 'Anulado' tasks (matching dashboard behavior)
        query = query.filter(Task.status != 'Anulado')

    # Apply Date/Period Filters
    today = date.today()
    if period == 'today':
        query = query.filter(db.func.date(Task.due_date) == today)
        filters['date_range'] = 'Hoy'
    elif period == 'week':
        week_start = today - timedelta(days=today.weekday())
        week_end = week_start + timedelta(days=6)
        query = query.filter(db.func.date(Task.due_date) >= week_start,
                           db.func.date(Task.due_date) <= week_end)
        filters['date_range'] = 'Esta Semana'
    elif period == 'month':
        month_start = today.replace(day=1)
        if today.month == 12:
            month_end = today.replace(day=31)
        else:
            month_end = (today.replace(month=today.month + 1, day=1) - timedelta(days=1))
        query = query.filter(db.func.date(Task.due_date) >= month_start,
                           db.func.date(Task.due_date) <= month_end)
        filters['date_range'] = 'Este Mes'
    elif start_date_str and end_date_str:
        try:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
            query = query.filter(db.func.date(Task.due_date) >= start_date,
                               db.func.date(Task.due_date) <= end_date)
            filters['date_range'] = f"{start_date_str} a {end_date_str}"
        except ValueError:
            pass
            
    # Tag filter
    filter_tag = request.args.get('tag_filter')
    if filter_tag:
        query = query.filter(Task.tags.any(id=int(filter_tag)))
        tag = Tag.query.get(int(filter_tag))
        filters['tag'] = tag.name if tag else ''

    # Search filter
    search_query = request.args.get('q')
    if search_query:
        search_term = f"%{search_query}%"
        query = query.filter(
            (Task.title.ilike(search_term)) | 
            (Task.description.ilike(search_term))
        )
        filters['search'] = search_query
        
    tasks = query.order_by(Task.due_date.asc()).all()
    
    pdf = generate_task_pdf(tasks, filters)
    
    response = make_response(pdf.output(dest='S').encode('latin-1'))
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = f'attachment; filename=reporte_tareas_{date.today()}.pdf'
    
    return response

@main_bp.route('/export_excel')
@login_required
def export_excel():
    # Re-use filter logic from dashboard (same as export_pdf)
    filter_assignee = request.args.get('assignee')
    filter_creator = request.args.get('creator')
    filter_status = request.args.get('status')
    
    # Calendar specific filters
    period = request.args.get('period')
    start_date_str = request.args.get('start_date')
    end_date_str = request.args.get('end_date')
    
    # Base query - start without user filter to match dashboard behavior
    query = Task.query.options(joinedload(Task.assignees), joinedload(Task.tags))
    
    filters = {}
    
    # Apply Assignee Filter
    if filter_assignee:
        query = query.filter(Task.assignees.any(id=filter_assignee))
        assignee = User.query.get(filter_assignee)
        filters['assignee_name'] = assignee.full_name if assignee else 'Desconocido'
    # If no assignee filter, show ALL tasks (matching dashboard behavior)
    
    # Apply Creator Filter
    if filter_creator:
        query = query.filter(Task.creator_id == filter_creator)
        creator = User.query.get(filter_creator)
        filters['creator_name'] = creator.full_name if creator else 'Desconocido'
        filters['creator'] = filter_creator
        
    # Apply Status Filter - exclude 'Anulado' by default like dashboard
    if filter_status:
        if filter_status in ['Pending', 'Completed', 'Anulado']:
            query = query.filter(Task.status == filter_status)
            filters['status'] = filter_status
    else:
        # By default, exclude 'Anulado' tasks (matching dashboard behavior)
        query = query.filter(Task.status != 'Anulado')

    # Apply Date/Period Filters
    today = date.today()
    if period == 'today':
        query = query.filter(db.func.date(Task.due_date) == today)
        filters['date_range'] = 'Hoy'
    elif period == 'week':
        week_start = today - timedelta(days=today.weekday())
        week_end = week_start + timedelta(days=6)
        query = query.filter(db.func.date(Task.due_date) >= week_start,
                           db.func.date(Task.due_date) <= week_end)
        filters['date_range'] = 'Esta Semana'
    elif period == 'month':
        month_start = today.replace(day=1)
        if today.month == 12:
            month_end = today.replace(day=31)
        else:
            month_end = (today.replace(month=today.month + 1, day=1) - timedelta(days=1))
        query = query.filter(db.func.date(Task.due_date) >= month_start,
                           db.func.date(Task.due_date) <= month_end)
        filters['date_range'] = 'Este Mes'
    elif start_date_str and end_date_str:
        try:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
            query = query.filter(db.func.date(Task.due_date) >= start_date,
                               db.func.date(Task.due_date) <= end_date)
            filters['date_range'] = f"{start_date_str} a {end_date_str}"
        except ValueError:
            pass
            
    # Tag filter
    filter_tag = request.args.get('tag_filter')
    if filter_tag:
        query = query.filter(Task.tags.any(id=int(filter_tag)))
        tag = Tag.query.get(int(filter_tag))
        filters['tag'] = tag.name if tag else ''

    # Search filter
    search_query = request.args.get('q')
    if search_query:
        search_term = f"%{search_query}%"
        query = query.filter(
            (Task.title.ilike(search_term)) | 
            (Task.description.ilike(search_term))
        )
        filters['search'] = search_query
        
    tasks = query.order_by(Task.due_date.asc()).all()
    
    wb = generate_task_excel(tasks, filters)
    
    # Save to BytesIO
    excel_file = BytesIO()
    wb.save(excel_file)
    excel_file.seek(0)
    
    response = make_response(excel_file.read())
    response.headers['Content-Type'] = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    response.headers['Content-Disposition'] = f'attachment; filename=reporte_tareas_{date.today()}.xlsx'
    
    return response

# --- Admin Routes ---
@admin_bp.route('/users', methods=['GET', 'POST'])
@login_required
def manage_users():
    # Ideally only for admins, but for now let's allow all or check is_admin
    if not current_user.is_admin:
        flash('Acceso denegado.', 'danger')
        return redirect(url_for('main.dashboard'))
        
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        full_name = request.form.get('full_name')
        is_admin = 'is_admin' in request.form
        
        if User.query.filter_by(username=username).first():
            flash('El nombre de usuario ya existe.', 'warning')
        else:
            new_user = User(username=username, full_name=full_name, is_admin=is_admin, email=f"{username}@example.com") # Mock email
            new_user.set_password(password)
            db.session.add(new_user)
            db.session.commit()
            flash('Usuario creado exitosamente.', 'success')
            
    users = User.query.all()
    return render_template('users.html', users=users)

# --- API Routes for Notifications ---
@main_bp.route('/api/tasks/due_soon')
@login_required
def api_tasks_due_soon():
    """
    Return tasks that are due in 2 business days.
    Used for popup notifications.
    """
    if not current_user.notifications_enabled:
        return jsonify({'tasks': []})
    
    # Get all pending tasks assigned to current user
    pending_tasks = Task.query.filter(
        Task.assignees.any(id=current_user.id),
        Task.status == 'Pending'
    ).all()
    
    # Filter tasks that are due in 2 or fewer business days
    due_soon_tasks = []
    for task in pending_tasks:
        business_days = calculate_business_days_until(task.due_date)
        if business_days <= 2:  # 0, 1, or 2 business days
            due_soon_tasks.append({
                'id': task.id,
                'title': task.title,
                'due_date': task.due_date.strftime('%d/%m/%Y'),
                'priority': task.priority,
                'description': task.description[:100] if task.description else '',
                'days_remaining': business_days
            })
    
    return jsonify({'tasks': due_soon_tasks})

@main_bp.route('/api/user/toggle_notifications', methods=['POST'])
@login_required
def api_toggle_notifications():
    """
    Toggle user's notification preference.
    """
    current_user.notifications_enabled = not current_user.notifications_enabled
    db.session.commit()
    
    return jsonify({
        'success': True,
        'notifications_enabled': current_user.notifications_enabled
    })
# Tags Routes - Append to routes.py

# --- Tags Management Routes ---
@main_bp.route('/tags')
@login_required
def tags():
    """Tags management page - accessible to all users"""
    all_tags = Tag.query.order_by(Tag.name).all()
    return render_template('tags.html', tags=all_tags)

@main_bp.route('/api/tags', methods=['GET'])
@login_required
def api_get_tags():
    """Get all tags"""
    tags = Tag.query.order_by(Tag.name).all()
    return jsonify({
        'tags': [{
            'id': tag.id,
            'name': tag.name,
            'color': tag.color
        } for tag in tags]
    })

@main_bp.route('/api/tags', methods=['POST'])
@login_required
def api_create_tag():
    """Create a new tag - accessible to all users"""
    
    data = request.get_json()
    name = data.get('name', '').strip()
    color = data.get('color', '#2563eb')
    
    if not name:
        return jsonify({'success': False, 'message': 'El nombre es requerido'}), 400
    
    # Check if tag already exists
    existing = Tag.query.filter_by(name=name).first()
    if existing:
        return jsonify({'success': False, 'message': 'Este tag ya existe'}), 400
    
    new_tag = Tag(
        name=name,
        color=color,
        created_by_id=current_user.id
    )
    
    db.session.add(new_tag)
    db.session.commit()
    
    return jsonify({
        'success': True,
        'tag': {
            'id': new_tag.id,
            'name': new_tag.name,
            'color': new_tag.color
        }
    })

@main_bp.route('/api/tags/<int:tag_id>', methods=['PUT'])
@login_required
def api_update_tag(tag_id):
    """Update a tag - accessible to all users"""
    
    tag = Tag.query.get_or_404(tag_id)
    data = request.get_json()
    
    name = data.get('name', '').strip()
    color = data.get('color')
    
    if name:
        # Check if new name conflicts with another tag
        existing = Tag.query.filter(Tag.name == name, Tag.id != tag_id).first()
        if existing:
            return jsonify({'success': False, 'message': 'Este nombre ya está en uso'}), 400
        tag.name = name
    
    if color:
        tag.color = color
    
    db.session.commit()
    
    return jsonify({
        'success': True,
        'tag': {
            'id': tag.id,
            'name': tag.name,
            'color': tag.color
        }
    })

@main_bp.route('/api/tags/<int:tag_id>', methods=['DELETE'])
@login_required
def api_delete_tag(tag_id):
    """Delete a tag - accessible to all users"""
    
    tag = Tag.query.get_or_404(tag_id)
    
    db.session.delete(tag)
    db.session.commit()
    
    return jsonify({'success': True})

# --- Reports Routes ---
@main_bp.route('/reports')
@login_required
def reports():
    users = User.query.all()
    tags = Tag.query.order_by(Tag.name).all()
    return render_template('reports.html', users=users, tags=tags)

@main_bp.route('/api/reports/data', methods=['POST'])
@login_required
def reports_data():
    data = request.get_json()
    user_ids = data.get('user_ids', [])
    tag_ids = data.get('tag_ids', []) # New filter
    status_filter = data.get('status') # New filter
    start_date_str = data.get('start_date')
    end_date_str = data.get('end_date')
    
    # Base query - ALWAYS exclude 'Anulado' tasks from reports
    query = Task.query.options(joinedload(Task.assignees), joinedload(Task.tags)).filter(Task.status != 'Anulado')
    
    # Filter by users if provided
    if user_ids:
        query = query.filter(Task.assignees.any(User.id.in_(user_ids)))
        
    # Filter by tags if provided
    if tag_ids:
        query = query.filter(Task.tags.any(Tag.id.in_(tag_ids)))
        
    # Filter by status if provided
    if status_filter and status_filter != 'All':
        query = query.filter(Task.status == status_filter)
    
    # Filter by date range
    if start_date_str and end_date_str:
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d')
        end_date = end_date.replace(hour=23, minute=59, second=59)
        query = query.filter(Task.due_date >= start_date, Task.due_date <= end_date)
        
    tasks = query.all()
    
    # --- Aggregation ---
    
    # 1. Stats per User
    user_stats = []
    target_users = User.query.filter(User.id.in_(user_ids)).all() if user_ids else User.query.all()
    
    for user in target_users:
        user_tasks = [t for t in tasks if user in t.assignees]
        # Only skip if we are filtering by specific users and this user has no tasks
        # But if we are showing all users, we might want to show 0s? 
        # Let's keep existing logic: show all target_users
        
        completed = sum(1 for t in user_tasks if t.status == 'Completed')
        pending = len(user_tasks) - completed
        user_stats.append({
            'name': user.full_name,
            'completed': completed,
            'pending': pending
        })
        
    # 2. Global Status
    global_completed = sum(1 for t in tasks if t.status == 'Completed')
    global_pending = len(tasks) - global_completed
    
    # --- Trends (Time-based) ---
    # We need a date range for the X-axis
    t_start = datetime.strptime(start_date_str, '%Y-%m-%d') if start_date_str else datetime.now() - timedelta(days=30)
    
    if end_date_str:
        t_end = datetime.strptime(end_date_str, '%Y-%m-%d').replace(hour=23, minute=59, second=59)
    else:
        t_end = datetime.now()
    
    # Generate list of dates
    date_labels = []
    current = t_start
    while current <= t_end:
        date_labels.append(current.strftime('%Y-%m-%d'))
        current += timedelta(days=1)
        
    # 3. Global Trend (Completed tasks over time)
    # Base trend query needs to respect the same filters as above? 
    # Usually "Trend" implies "History", so we look at completed_at.
    # But we should respect the User/Tag filters.
    
    trend_query = Task.query.filter(Task.status == 'Completed', Task.completed_at.isnot(None))
    
    if user_ids:
        trend_query = trend_query.filter(Task.assignees.any(User.id.in_(user_ids)))
    if tag_ids:
        trend_query = trend_query.filter(Task.tags.any(Tag.id.in_(tag_ids)))
        
    trend_query = trend_query.filter(Task.completed_at >= t_start, Task.completed_at <= t_end)
    completed_tasks_trend = trend_query.all()
    
    # Group global completed by date
    global_date_counts = {d: 0 for d in date_labels}
    for t in completed_tasks_trend:
        d_str = t.completed_at.strftime('%Y-%m-%d')
        if d_str in global_date_counts:
            global_date_counts[d_str] += 1
            
    global_trend_data = {
        'dates': date_labels,
        'completed_counts': [global_date_counts[d] for d in date_labels]
    }

    # 4. Employee Trend (Line chart per employee)
    # We reuse 'completed_tasks_trend' but group by user
    employee_trend_datasets = []
    # If too many users, chart gets messy. Maybe limit to top 5 or selected?
    # For now, do all selected users (or all if none selected)
    
    for user in target_users:
        # Get tasks for this user from the trend set
        user_trend_tasks = [t for t in completed_tasks_trend if user in t.assignees]
        
        # If user has 0 completed tasks in this period, maybe skip? Or show flat line?
        # Let's show flat line if they are in the filter list.
        
        u_date_counts = {d: 0 for d in date_labels}
        for t in user_trend_tasks:
            d_str = t.completed_at.strftime('%Y-%m-%d')
            if d_str in u_date_counts:
                u_date_counts[d_str] += 1
        
        # Only add dataset if there's at least one task or if explicitly filtered?
        # Let's add all to be safe, frontend can hide if needed.
        # Optimization: if sum is 0, maybe skip to keep chart clean?
        if sum(u_date_counts.values()) > 0 or user_ids:
             employee_trend_datasets.append({
                'label': user.full_name,
                'data': [u_date_counts[d] for d in date_labels],
                'fill': False
             })

    # 5. Tag Trend (Line chart per tag)
    # We need to query tags. If tag_ids filter is on, use those. Else all tags?
    # If all tags, that might be too many lines. Let's use top 5 active tags or just the filtered ones.
    
    tag_trend_datasets = []
    target_tags = Tag.query.filter(Tag.id.in_(tag_ids)).all() if tag_ids else Tag.query.all()
    
    # If no tag filter, maybe we only show tags that actually have data in this period to avoid clutter?
    # Or just all tags. Let's try all tags but skip empty ones.
    
    for tag in target_tags:
        # Filter trend tasks that have this tag
        tag_trend_tasks = [t for t in completed_tasks_trend if tag in t.tags]
        
        t_date_counts = {d: 0 for d in date_labels}
        for t in tag_trend_tasks:
            d_str = t.completed_at.strftime('%Y-%m-%d')
            if d_str in t_date_counts:
                t_date_counts[d_str] += 1
                
        if sum(t_date_counts.values()) > 0 or tag_ids:
            tag_trend_datasets.append({
                'label': tag.name,
                'borderColor': tag.color, # Use tag color!
                'data': [t_date_counts[d] for d in date_labels],
                'fill': False
            })

    # 6. Detailed KPIs
    kpis = calculate_kpis(tasks, global_completed)

    return jsonify({
        'user_stats': user_stats,
        'global_stats': {'completed': global_completed, 'pending': global_pending},
        'trend': global_trend_data,
        'employee_trend': employee_trend_datasets,
        'tag_trend': tag_trend_datasets,
        'kpis': kpis
    })

@main_bp.route('/api/reports/calculate_difference', methods=['POST'])
@login_required
def api_calculate_difference():
    data = request.get_json()
    tag_a_ids = data.get('tag_a_ids', [])
    tag_b_ids = data.get('tag_b_ids', [])
    
    # Fallback for old single ID calls
    if not tag_a_ids and 'tag_a_id' in data:
        tag_a_ids = [data['tag_a_id']]
    if not tag_b_ids and 'tag_b_id' in data:
        tag_b_ids = [data['tag_b_id']]
        
    start_date_str = data.get('start_date')
    end_date_str = data.get('end_date')
    
    def get_group_time(t_ids):
        if not t_ids: return 0
        q = Task.query.filter(Task.status != 'Anulado')
        # Filter tasks that have ANY of the tags in t_ids
        q = q.filter(Task.tags.any(Tag.id.in_(t_ids)))
        
        if start_date_str and end_date_str:
            try:
                s_date = datetime.strptime(start_date_str, '%Y-%m-%d')
                e_date = datetime.strptime(end_date_str, '%Y-%m-%d').replace(hour=23, minute=59, second=59)
                q = q.filter(Task.due_date >= s_date, Task.due_date <= e_date)
            except ValueError:
                pass
                
        tasks = q.all()
        # Sum time_spent (Task objects are unique due to SQLAlchemys identity map in this query context)
        total = sum(t.time_spent for t in tasks if t.time_spent)
        return total

    time_a = get_group_time(tag_a_ids)
    time_b = get_group_time(tag_b_ids)
    
    diff = time_a - time_b
    
    abs_diff = abs(diff)
    hours = int(abs_diff / 60)
    minutes = int(abs_diff % 60)
    formatted = f"{hours}h {minutes}m"
    if diff < 0:
        formatted = f"- {formatted}"
    
    return jsonify({
        'time_a': time_a,
        'time_b': time_b,
        'diff': diff,
        'formatted': formatted
    })

@main_bp.route('/reports/export', methods=['POST'])
@login_required
def export_report():
    # Get filters from form data
    user_ids_str = request.form.get('user_ids')
    tag_ids_str = request.form.get('tag_ids') # New
    status_filter = request.form.get('status') # New
    start_date_str = request.form.get('start_date')
    end_date_str = request.form.get('end_date')
    include_kpis_str = request.form.get('include_kpis')
    include_kpis = include_kpis_str == 'true'
    
    import json
    user_ids = json.loads(user_ids_str) if user_ids_str else []
    tag_ids = json.loads(tag_ids_str) if tag_ids_str else [] # New
    
    # Fetch data
    query = Task.query
    if user_ids:
        query = query.filter(Task.assignees.any(User.id.in_(user_ids)))
        
    if tag_ids: # New
        query = query.filter(Task.tags.any(Tag.id.in_(tag_ids)))
        
    if status_filter and status_filter != 'All': # New
        query = query.filter(Task.status == status_filter)
        
    if start_date_str and end_date_str:
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d').replace(hour=23, minute=59, second=59)
        query = query.filter(Task.due_date >= start_date, Task.due_date <= end_date)
        
    tasks = query.order_by(Task.due_date).all()
    
    # Prepare data for charts
    
    # Generate PDF
    from pdf_utils import generate_report_pdf
    
    # Stats calculation:
    target_users = User.query.filter(User.id.in_(user_ids)).all() if user_ids else User.query.all()
    user_stats = []
    for user in target_users:
        u_tasks = [t for t in tasks if user in t.assignees]
        # If filtering by users, only show those users. If not, show all.
        # Logic: if user_ids is set, we only iterate those. If not, we iterate all.
        # But if we filter by tag, a user might have 0 tasks with that tag.
        # Should we show them? Yes, with 0.
        
        completed = sum(1 for t in u_tasks if t.status == 'Completed')
        user_stats.append({'name': user.full_name, 'completed': completed, 'pending': len(u_tasks)-completed})
        
    # Global Stats
    global_completed = sum(1 for t in tasks if t.status == 'Completed')
    global_pending = len(tasks) - global_completed
    
    # Trend Data
    t_start = datetime.strptime(start_date_str, '%Y-%m-%d') if start_date_str else datetime.now() - timedelta(days=30)
    
    if end_date_str:
        t_end = datetime.strptime(end_date_str, '%Y-%m-%d').replace(hour=23, minute=59, second=59)
    else:
        t_end = datetime.now()
    
    # Filter completed tasks for trend (respecting all filters)
    # We can just filter 'tasks' list since it already has all filters applied
    completed_tasks_trend = [t for t in tasks if t.status == 'Completed' and t.completed_at and t_start <= t.completed_at <= t_end]
    
    date_counts = {}
    current = t_start
    while current <= t_end:
        date_str = current.strftime('%Y-%m-%d')
        date_counts[date_str] = 0
        current += timedelta(days=1)
        
    for t in completed_tasks_trend:
        d_str = t.completed_at.strftime('%Y-%m-%d')
        if d_str in date_counts:
            date_counts[d_str] += 1
            
    trend_data = {
        'dates': list(date_counts.keys()),
        'completed_counts': list(date_counts.values())
    }
    
    # --- Employee Trend (for PDF) ---
    employee_trend_datasets = []
    for user in target_users:
        user_trend_tasks = [t for t in completed_tasks_trend if user in t.assignees]
        u_date_counts = {d: 0 for d in date_counts.keys()}
        for t in user_trend_tasks:
            d_str = t.completed_at.strftime('%Y-%m-%d')
            if d_str in u_date_counts:
                u_date_counts[d_str] += 1
        
        if sum(u_date_counts.values()) > 0 or user_ids:
             employee_trend_datasets.append({
                'label': user.full_name,
                'data': [u_date_counts[d] for d in date_counts.keys()]
             })

    # --- Tag Trend (for PDF) ---
    tag_trend_datasets = []
    target_tags = Tag.query.filter(Tag.id.in_(tag_ids)).all() if tag_ids else Tag.query.all()
    
    for tag in target_tags:
        tag_trend_tasks = [t for t in completed_tasks_trend if tag in t.tags]
        t_date_counts = {d: 0 for d in date_counts.keys()}
        for t in tag_trend_tasks:
            d_str = t.completed_at.strftime('%Y-%m-%d')
            if d_str in t_date_counts:
                t_date_counts[d_str] += 1
                
        if sum(t_date_counts.values()) > 0 or tag_ids:
            tag_trend_datasets.append({
                'label': tag.name,
                'color': tag.color,
                'data': [t_date_counts[d] for d in date_counts.keys()]
            })
    
    # Filter Info for PDF
    filter_info = {
        'users': [u.full_name for u in target_users] if user_ids else ['Todos'],
        'tags': [t.name for t in Tag.query.filter(Tag.id.in_(tag_ids)).all()] if tag_ids else ['Todas'],
        'status': status_filter if status_filter and status_filter != 'All' else 'Todos'
    }
        
    report_data = {
        'tasks': tasks,
        'user_stats': user_stats,
        'global_stats': {'completed': global_completed, 'pending': global_pending},
        'trend': trend_data,
        'employee_trend': employee_trend_datasets, # New
        'tag_trend': tag_trend_datasets, # New
        'start_date': start_date_str,
        'end_date': end_date_str,
        'filters': filter_info
    }
    
    if include_kpis:
        report_data['kpis'] = calculate_kpis(tasks, global_completed)
        
    # Calculate difference if tags provided
    # Input names are 'diff_tag_a' and 'diff_tag_b' which now contain JSON lists
    import json
    diff_tag_a_json = request.form.get('diff_tag_a')
    diff_tag_b_json = request.form.get('diff_tag_b')
    
    if diff_tag_a_json and diff_tag_b_json:
        try:
            tag_a_ids = json.loads(diff_tag_a_json)
            tag_b_ids = json.loads(diff_tag_b_json)
            
            # Helper to calculate group time (duplicated logic, should be refactored)
            def get_group_time_export(t_ids):
                if not t_ids: return 0, "0h 0m"
                q = Task.query.filter(Task.status != 'Anulado')
                q = q.filter(Task.tags.any(Tag.id.in_(t_ids)))
                if start_date_str and end_date_str:
                    s_date = datetime.strptime(start_date_str, '%Y-%m-%d')
                    e_date = datetime.strptime(end_date_str, '%Y-%m-%d').replace(hour=23, minute=59, second=59)
                    q = q.filter(Task.due_date >= s_date, Task.due_date <= e_date)
                ts = q.all()
                total_min = sum(t.time_spent for t in ts if t.time_spent)
                
                h = int(total_min / 60)
                m = int(total_min % 60)
                return total_min, f"{h}h {m}m"

            # Get objects for names
            tags_a = Tag.query.filter(Tag.id.in_(tag_a_ids)).all()
            tags_b = Tag.query.filter(Tag.id.in_(tag_b_ids)).all()
            
            # Format names (e.g. "TagA, TagB")
            name_a = ", ".join([t.name for t in tags_a])
            name_b = ", ".join([t.name for t in tags_b])
            
            if tags_a and tags_b:
                time_a, str_a = get_group_time_export(tag_a_ids)
                time_b, str_b = get_group_time_export(tag_b_ids)
                
                diff = time_a - time_b
                abs_diff = abs(diff)
                d_h = int(abs_diff / 60)
                d_m = int(abs_diff % 60)
                diff_str = f"{d_h}h {d_m}m"
                if diff < 0: diff_str = "- " + diff_str
                
                report_data['diff_calc'] = {
                    'tag_a': {'name': name_a, 'time': str_a},
                    'tag_b': {'name': name_b, 'time': str_b},
                    'result': diff_str
                }
        except Exception as e:
            print(f"Error calculating diff for export: {e}")
    
    pdf = generate_report_pdf(report_data)
    
    response = make_response(pdf.output(dest='S').encode('latin-1'))
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = f'attachment; filename=reporte_avanzado_{date.today()}.pdf'
    
    return response

def calculate_kpis(tasks, global_completed):
    # Total Tasks
    kpi_total = len(tasks)
    
    # Completion Rate
    kpi_completion_rate = round((global_completed / kpi_total * 100), 1) if kpi_total > 0 else 0
    
    # Overdue Tasks (Pending and due_date < now)
    now = datetime.now()
    kpi_overdue = sum(1 for t in tasks if t.status == 'Pending' and t.due_date < now)
    
    # Time calculations (using time_spent field in minutes)
    tasks_with_time = [t for t in tasks if t.time_spent and t.time_spent > 0]
    
    if tasks_with_time:
        total_minutes = sum(t.time_spent for t in tasks_with_time)
        avg_minutes = total_minutes / len(tasks_with_time)
        
        # Format avg_time: show hours if >= 60 min, otherwise minutes
        if avg_minutes >= 60:
            hours = avg_minutes / 60
            kpi_avg_time = f"{round(hours, 1)} horas"
        else:
            kpi_avg_time = f"{round(avg_minutes)} min"
        
        # Format total_time: show both minutes and hours
        total_hours = total_minutes / 60
        kpi_total_time = f"{int(total_minutes)} min ({round(total_hours, 1)} hs)"
    else:
        kpi_avg_time = "N/A"
        kpi_total_time = "0 min"

    return {
        'total': kpi_total,
        'completion_rate': kpi_completion_rate,
        'overdue': kpi_overdue,
        'avg_time': kpi_avg_time,
        'total_time': kpi_total_time
    }

# --- Excel Import Routes ---
@main_bp.route('/import/template')
@login_required
def download_import_template():
    """Download the Excel template for importing tasks"""
    import os
    template_path = os.path.join(os.path.dirname(__file__), 'static', 'plantilla_tareas.xlsx')
    
    if not os.path.exists(template_path):
        flash('Plantilla no encontrada. Contacte al administrador.', 'danger')
        return redirect(url_for('main.dashboard'))
    
    with open(template_path, 'rb') as f:
        data = f.read()
    
    response = make_response(data)
    response.headers['Content-Type'] = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    response.headers['Content-Disposition'] = 'attachment; filename=plantilla_tareas.xlsx'
    return response

@main_bp.route('/import/tasks', methods=['POST'])
@login_required
def import_tasks():
    """Import tasks from an uploaded Excel file"""
    from openpyxl import load_workbook
    
    if 'file' not in request.files:
        flash('No se seleccionó ningún archivo.', 'danger')
        return redirect(url_for('main.dashboard'))
    
    file = request.files['file']
    
    if file.filename == '':
        flash('No se seleccionó ningún archivo.', 'danger')
        return redirect(url_for('main.dashboard'))
    
    if not file.filename.endswith(('.xlsx', '.xls')):
        flash('El archivo debe ser un Excel (.xlsx o .xls).', 'danger')
        return redirect(url_for('main.dashboard'))
    
    try:
        wb = load_workbook(file)
        ws = wb.active
        
        # Skip header row
        rows = list(ws.iter_rows(min_row=2, values_only=True))
        
        created_count = 0
        errors = []
        
        for row_num, row in enumerate(rows, start=2):
            if not row or not row[0]:  # Skip empty rows
                continue
            
            titulo = row[0] if len(row) > 0 else None
            descripcion = row[1] if len(row) > 1 else ''
            prioridad = row[2] if len(row) > 2 else 'Normal'
            fecha_str = row[3] if len(row) > 3 else None
            asignados_str = row[4] if len(row) > 4 else ''
            etiquetas_str = row[5] if len(row) > 5 else ''
            tiempo_str = row[6] if len(row) > 6 else ''
            estado_str = row[7] if len(row) > 7 else 'Pendiente'
            
            # Validate required fields
            if not titulo:
                errors.append(f'Fila {row_num}: Título requerido')
                continue
            
            if not fecha_str:
                errors.append(f'Fila {row_num}: Fecha de vencimiento requerida')
                continue
            
            # Parse date
            try:
                if isinstance(fecha_str, str):
                    due_date = datetime.strptime(fecha_str, '%Y-%m-%d')
                else:
                    # Excel may return datetime object
                    due_date = fecha_str if isinstance(fecha_str, datetime) else datetime.strptime(str(fecha_str), '%Y-%m-%d')
            except (ValueError, TypeError):
                errors.append(f'Fila {row_num}: Formato de fecha inválido (use AAAA-MM-DD)')
                continue
            
            # Validate priority
            if prioridad not in ['Normal', 'Media', 'Urgente']:
                prioridad = 'Normal'
            
            # Parse time_spent (optional, in minutes)
            time_spent = None
            if tiempo_str:
                try:
                    time_spent = int(tiempo_str)
                except (ValueError, TypeError):
                    pass  # Ignore invalid time values
            
            # Parse status
            status = 'Pending'  # Default
            if estado_str:
                estado_lower = str(estado_str).strip().lower()
                if estado_lower in ['completada', 'completed', 'completado', 'c']:
                    status = 'Completed'
                elif estado_lower in ['pendiente', 'pending', 'p']:
                    status = 'Pending'
            
            # Parse assignees
            assignee_usernames = [u.strip() for u in str(asignados_str).split(',') if u.strip()]
            assignees = []
            for username in assignee_usernames:
                user = User.query.filter_by(username=username).first()
                if user:
                    assignees.append(user)
                else:
                    errors.append(f'Fila {row_num}: Usuario "{username}" no encontrado')
            
            if not assignees:
                errors.append(f'Fila {row_num}: Ningún usuario válido asignado')
                continue
            
            # Parse tags (optional)
            tag_names = [t.strip() for t in str(etiquetas_str).split(',') if t.strip()]
            tags = []
            for tag_name in tag_names:
                tag = Tag.query.filter_by(name=tag_name).first()
                if tag:
                    tags.append(tag)
                # Silently ignore non-existing tags (they're optional)
            
            # Create task
            new_task = Task(
                title=str(titulo),
                description=str(descripcion) if descripcion else '',
                priority=prioridad,
                due_date=due_date,
                creator_id=current_user.id,
                time_spent=time_spent,
                status=status
            )
            
            # Set completed info if status is Completed
            if status == 'Completed':
                new_task.completed_by_id = current_user.id
                new_task.completed_at = datetime.now()
            
            for user in assignees:
                new_task.assignees.append(user)
            
            for tag in tags:
                new_task.tags.append(tag)
            
            db.session.add(new_task)
            created_count += 1
        
        db.session.commit()
        
        if created_count > 0:
            flash(f'Se importaron {created_count} tareas exitosamente.', 'success')
        
        if errors:
            error_msg = 'Errores encontrados: ' + '; '.join(errors[:5])
            if len(errors) > 5:
                error_msg += f' ... y {len(errors) - 5} más.'
            flash(error_msg, 'warning')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error al procesar el archivo: {str(e)}', 'danger')
    
    return redirect(url_for('main.dashboard'))

# --- Task Template Routes ---
@main_bp.route('/templates', methods=['GET', 'POST'])
@login_required
def manage_templates():
    """View and create task templates"""
    if request.method == 'POST':
        name = request.form.get('name')
        title = request.form.get('title')
        description = request.form.get('description', '')
        priority = request.form.get('priority', 'Normal')
        default_days = int(request.form.get('default_days', 0))
        tag_ids = request.form.getlist('tags')
        
        # Parse time_spent
        time_spent_str = request.form.get('time_spent', '0')
        try:
            time_spent = int(time_spent_str) if time_spent_str else 0
        except ValueError:
            time_spent = 0
        
        # Check if template name already exists
        if TaskTemplate.query.filter_by(name=name).first():
            flash('Ya existe una plantilla con ese nombre.', 'danger')
            return redirect(url_for('main.manage_templates'))
        
        template = TaskTemplate(
            name=name,
            title=title,
            description=description,
            priority=priority,
            default_days=default_days,
            created_by_id=current_user.id,
            time_spent=time_spent
        )
        
        # Add tags
        for tag_id in tag_ids:
            tag = Tag.query.get(int(tag_id))
            if tag:
                template.tags.append(tag)
        
        db.session.add(template)
        db.session.commit()
        
        flash(f'Plantilla "{name}" creada exitosamente.', 'success')
        return redirect(url_for('main.manage_templates'))
    
    templates = TaskTemplate.query.order_by(TaskTemplate.name).all()
    available_tags = Tag.query.order_by(Tag.name).all()
    return render_template('manage_templates.html', templates=templates, available_tags=available_tags)

@main_bp.route('/templates/<int:template_id>/delete', methods=['POST'])
@login_required
def delete_template(template_id):
    """Delete a task template"""
    template = TaskTemplate.query.get_or_404(template_id)
    
    # Only creator or admin can delete
    if template.created_by_id != current_user.id and not current_user.is_admin:
        flash('No tienes permiso para eliminar esta plantilla.', 'danger')
        return redirect(url_for('main.manage_templates'))
    
    name = template.name
    db.session.delete(template)
    db.session.commit()
    
    flash(f'Plantilla "{name}" eliminada.', 'success')
    return redirect(url_for('main.manage_templates'))

@main_bp.route('/api/templates/<int:template_id>')
@login_required
def get_template_data(template_id):
    """API to get template data for form autofill"""
    template = TaskTemplate.query.get_or_404(template_id)
    
    # Calculate due date based on default_days
    due_date = date.today() + timedelta(days=template.default_days)
    
    return jsonify({
        'title': template.title,
        'description': template.description or '',
        'priority': template.priority,
        'due_date': due_date.strftime('%Y-%m-%d'),
        'tag_ids': [tag.id for tag in template.tags],
        'time_spent': template.time_spent or 0
    })
