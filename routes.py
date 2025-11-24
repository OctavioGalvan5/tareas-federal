from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, make_response
from flask_login import login_user, logout_user, login_required, current_user
from extensions import db
from models import User, Task
from datetime import datetime, date, timedelta
from pdf_utils import generate_task_pdf

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
    
    query = Task.query
    
    if filter_assignee:
        query = query.filter(Task.assignees.any(id=filter_assignee))
    else:
        # Default: Show tasks assigned to current user
        pass 
    
    tasks_query = Task.query.filter(Task.assignees.any(id=current_user.id))
    
    if filter_creator:
        tasks_query = tasks_query.filter(Task.creator_id == filter_creator)
        
    if filter_status and filter_status in ['Pending', 'Completed']:
        tasks_query = tasks_query.filter(Task.status == filter_status)
        
    # Sort by due_date ascending
    tasks = tasks_query.order_by(Task.due_date.asc()).all()
    
    # Check for tasks due today for highlighting
    today = date.today()
    
    users = User.query.all() # For filters
    
    return render_template('dashboard.html', tasks=tasks, today=today, users=users)

@main_bp.route('/task/new', methods=['GET', 'POST'])
@login_required
def create_task():
    users = User.query.all()
    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description')
        priority = request.form.get('priority')
        due_date_str = request.form.get('due_date')
        assignee_ids = request.form.getlist('assignees')
        
        due_date = datetime.strptime(due_date_str, '%Y-%m-%d')
        
        new_task = Task(
            title=title,
            description=description,
            priority=priority,
            due_date=due_date,
            creator_id=current_user.id
        )
        
        # Add assignees
        for user_id in assignee_ids:
            user = User.query.get(int(user_id))
            if user:
                new_task.assignees.append(user)
                
        db.session.add(new_task)
        db.session.commit()
        flash('Tarea creada exitosamente.', 'success')
        return redirect(url_for('main.dashboard'))
        
    return render_template('create_task.html', users=users)

@main_bp.route('/calendar')
@login_required
def calendar():
    # Get filter parameters
    period = request.args.get('period', 'all')  # today, week, month, all
    start_date_str = request.args.get('start_date')
    end_date_str = request.args.get('end_date')
    filter_creator = request.args.get('creator')
    
    # Base query: tasks assigned to current user
    query = Task.query.filter(Task.assignees.any(id=current_user.id))
    
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
    
    # Toggle status
    if task.status == 'Pending':
        task.status = 'Completed'
    else:
        task.status = 'Pending'
    
    db.session.commit()
    
    return jsonify({
        'success': True,
        'task_id': task.id,
        'new_status': task.status
    })

@main_bp.route('/export_pdf')
@login_required
def export_pdf():
    # Re-use filter logic
    filter_creator = request.args.get('creator')
    filter_status = request.args.get('status')
    
    # Calendar specific filters
    period = request.args.get('period')
    start_date_str = request.args.get('start_date')
    end_date_str = request.args.get('end_date')
    
    query = Task.query.filter(Task.assignees.any(id=current_user.id))
    
    filters = {}
    
    # Apply Creator Filter
    if filter_creator:
        query = query.filter(Task.creator_id == filter_creator)
        creator = User.query.get(filter_creator)
        filters['creator_name'] = creator.full_name if creator else 'Desconocido'
        filters['creator'] = filter_creator
        
    # Apply Status Filter
    if filter_status and filter_status in ['Pending', 'Completed']:
        query = query.filter(Task.status == filter_status)
        filters['status'] = filter_status

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
        
    tasks = query.order_by(Task.due_date.asc()).all()
    
    pdf = generate_task_pdf(tasks, filters)
    
    response = make_response(pdf.output(dest='S').encode('latin-1'))
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = f'attachment; filename=reporte_tareas_{date.today()}.pdf'
    
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
