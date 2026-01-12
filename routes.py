from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, make_response
from flask_login import login_user, logout_user, login_required, current_user
from extensions import db
from models import User, Task, Tag, TaskTemplate, Expiration, RecurringTask
from datetime import datetime, date, timedelta
from pdf_utils import generate_task_pdf
from excel_utils import generate_task_excel
from io import BytesIO
from utils import calculate_business_days_until
from sqlalchemy.orm import joinedload
import pytz

# Buenos Aires timezone (for reference, conversion is done in templates)
BUENOS_AIRES_TZ = pytz.timezone('America/Argentina/Buenos_Aires')

def now_utc():
    """Get current datetime in UTC (consistent with other datetimes in the app)."""
    return datetime.utcnow()


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
    # Import Area model
    from models import Area
    
    # Filter logic
    filter_assignee = request.args.get('assignee')
    filter_creator = request.args.get('creator')
    filter_status = request.args.get('status')
    filter_tag = request.args.get('tag_filter')
    filter_area = request.args.get('area')  # NEW: Area filter
    sort_order = request.args.get('sort', 'asc')

    # Base query: Eager load assignees, tags, and area
    tasks_query = Task.query.options(
        joinedload(Task.assignees), 
        joinedload(Task.tags),
        joinedload(Task.area)  # NEW: Load area relationship
    ).filter(Task.enabled == True)
    
    # NEW: Role-based visibility filtering
    # - usuario/usuario_plus: only see tasks assigned to them OR created by them (within their areas)
    # - supervisor: see ALL tasks in their area
    # - gerente/admin: see ALL tasks
    if current_user.can_only_see_own_tasks():
        # Users can only see tasks they are assigned to OR tasks they created
        user_area_ids = [area.id for area in current_user.areas]
        if user_area_ids:
            tasks_query = tasks_query.filter(
                db.or_(
                    Task.assignees.any(id=current_user.id),
                    Task.creator_id == current_user.id
                )
            ).filter(Task.area_id.in_(user_area_ids))
        else:
            # User has no areas assigned - show no tasks
            tasks_query = tasks_query.filter(Task.area_id == -1)
    elif not current_user.can_see_all_areas():
        # Supervisors see all tasks in their area
        user_area_ids = [area.id for area in current_user.areas]
        if user_area_ids:
            tasks_query = tasks_query.filter(Task.area_id.in_(user_area_ids))
        else:
            tasks_query = tasks_query.filter(Task.area_id == -1)
    # Gerentes and admins see all tasks (no additional filter)
    
    # Additional area filter (for gerentes/supervisors filtering specific area)
    if filter_area:
        tasks_query = tasks_query.filter(Task.area_id == int(filter_area))
    
    if filter_assignee:
        tasks_query = tasks_query.filter(Task.assignees.any(id=filter_assignee))
    
    if filter_creator:
        tasks_query = tasks_query.filter(Task.creator_id == filter_creator)
        
    # Handle status filter - exclude 'Anulado' by default
    if filter_status:
        if filter_status == 'Overdue':
            today_date = date.today()
            tasks_query = tasks_query.filter(
                Task.status == 'Pending',
                db.func.date(Task.due_date) < today_date
            )
        elif filter_status in ['Pending', 'Completed', 'Anulado']:
            tasks_query = tasks_query.filter(Task.status == filter_status)
    else:
        tasks_query = tasks_query.filter(Task.status != 'Anulado')

    if filter_tag:
        tasks_query = tasks_query.filter(Task.tags.any(id=int(filter_tag)))

    # Search filter
    search_query = request.args.get('q')
    if search_query:
        search_term = f"%{search_query}%"
        tasks_query = tasks_query.filter(
            (Task.title.ilike(search_term)) | 
            (Task.description.ilike(search_term))
        )
        
    # Sort by status first, then by due_date
    status_order = db.case(
        (Task.status == 'Pending', 0),
        (Task.status == 'Completed', 1),
        else_=2
    )
    
    if sort_order == 'desc':
        tasks = tasks_query.order_by(status_order, Task.due_date.desc()).all()
    else:
        tasks = tasks_query.order_by(status_order, Task.due_date.asc()).all()
    
    today = date.today()
    
    # Filter users by area for non-admins
    if current_user.is_admin or current_user.can_see_all_areas():
        users = User.query.all()
        all_areas = Area.query.order_by(Area.name).all()
        all_tags = Tag.query.order_by(Tag.name).all()
    else:
        # Non-admins see only users and tags in their areas
        users = [u for u in User.query.all() if any(area in u.areas for area in current_user.areas)]
        all_areas = current_user.areas
        user_area_ids = [a.id for a in current_user.areas]
        if user_area_ids:
            # Strict area filter - only show tags from user's areas
            all_tags = Tag.query.filter(Tag.area_id.in_(user_area_ids)).order_by(Tag.name).all()
        else:
            all_tags = []
    
    return render_template('dashboard.html', 
        tasks=tasks, 
        today=today, 
        users=users, 
        all_tags=all_tags, 
        sort_order=sort_order,
        all_areas=all_areas,  # NEW: Pass areas to template
        current_user_is_gerente=current_user.can_see_all_areas()  # NEW
    )

@main_bp.route('/task/new', methods=['GET', 'POST'])
@login_required
def create_task():
    # Import Area model
    from models import Area
    
    # --- CHECK PERMISSION TO CREATE TASKS ---
    if not current_user.can_create_tasks():
        flash('No tienes permiso para crear tareas. Usa el calendario de vencimientos para crear recordatorios.', 'danger')
        return redirect(url_for('main.dashboard'))
    
    # Load available areas based on user role
    # Admins see all, others see only their area(s)
    if current_user.is_admin:
        available_areas = Area.query.order_by(Area.name).all()
        users = User.query.all()  # Admins see all users
        available_tags = Tag.query.order_by(Tag.name).all()
        templates = TaskTemplate.query.order_by(TaskTemplate.name).all()
    else:
        # Supervisor/usuario_plus: only their assigned area(s)
        available_areas = current_user.areas[:1] if current_user.areas else []
        # Only see users in their area
        if available_areas:
            users = [u for u in User.query.all() if any(area in u.areas for area in available_areas)]
            # Filter tags and templates by area
            user_area_ids = [a.id for a in available_areas]
            available_tags = Tag.query.filter(Tag.area_id.in_(user_area_ids)).order_by(Tag.name).all()
            templates = TaskTemplate.query.filter(TaskTemplate.area_id.in_(user_area_ids)).order_by(TaskTemplate.name).all()
        else:
            users = []
            available_tags = []

            templates = []

    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description')
        priority = request.form.get('priority')
        due_date_str = request.form.get('due_date')
        time_spent_str = request.form.get('time_spent')
        area_id_str = request.form.get('area_id')  # NEW: Get area from form
        
        due_date = datetime.strptime(due_date_str, '%Y-%m-%d')
        
        # Parse time_spent (in minutes)
        time_spent = None
        if time_spent_str and time_spent_str.strip():
            try:
                time_spent = int(time_spent_str)
            except ValueError:
                time_spent = None
        
        # Parse area_id
        area_id = None
        if area_id_str and area_id_str.strip():
            try:
                area_id = int(area_id_str)
            except ValueError:
                area_id = None
        
        # If no area selected and user has only one area, use that one
        if area_id is None and len(available_areas) == 1:
            area_id = available_areas[0].id
        
        # Process task creation
        assignee_ids = request.form.getlist('assignees')
        
        new_task = Task(
            title=title,
            description=description,
            priority=priority,
            due_date=due_date,
            creator_id=current_user.id,
            time_spent=time_spent,
            area_id=area_id  # NEW: Assign area
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
        
        # Handle parent task selection and dependency blocking
        parent_id_str = request.form.get('parent_id')
        if parent_id_str:
            try:
                parent_id = int(parent_id_str)
                parent_task = Task.query.get(parent_id)
                if parent_task:
                    new_task.parent_id = parent_id
                    # If parent is NOT completed, the child starts as blocked
                    if parent_task.status != 'Completed':
                        new_task.enabled = False
                        new_task.enabled_at = None
                    else:
                        # Parent is already completed, child starts enabled
                        new_task.enabled = True
                        new_task.enabled_at = now_utc()
                        new_task.enabled_by_task_id = parent_id
            except (ValueError, TypeError):
                pass  # Invalid parent_id, ignore it
                
        db.session.add(new_task)
        db.session.commit()
        flash('Tarea creada exitosamente.', 'success')
        return redirect(url_for('main.dashboard'))
        
    return render_template('create_task.html', users=users, available_tags=available_tags, templates=templates, available_areas=available_areas)

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

    if current_user.is_admin or current_user.role == 'gerente':
        users = User.query.all()
        available_tags = Tag.query.order_by(Tag.name).all()
    else:
        # Filter users by area (assignees)
        users = [u for u in User.query.all() if any(area in u.areas for area in current_user.areas)]
        
        # Filter tags by area
        user_area_ids = [a.id for a in current_user.areas]
        if user_area_ids:
             available_tags = Tag.query.filter(Tag.area_id.in_(user_area_ids)).order_by(Tag.name).all()
        else:
             available_tags = []

    if request.method == 'POST':
        task.title = request.form.get('title')
        task.description = request.form.get('description')
        
        # Update status - ONLY if user is admin or if status is actually provided in form
        new_status = request.form.get('status')
        if new_status:  # Only update if a value was provided (prevents None)
            task.status = new_status
        
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
        
        # Handle parent task selection (with circular reference prevention)
        parent_id_str = request.form.get('parent_id')
        if parent_id_str:
            try:
                parent_id = int(parent_id_str)
                # Prevent circular reference: task cannot be its own parent
                if parent_id != task.id:
                    # Prevent circular reference: parent cannot be a descendant
                    if not is_descendant(task.id, parent_id):
                        parent_task = Task.query.get(parent_id)
                        if parent_task:
                            task.parent_id = parent_id
            except (ValueError, TypeError):
                pass  # Invalid parent_id, ignore it
        else:
            # Clear parent if field is empty
            task.parent_id = None
        
        # Handle completion tracking if status changed to Completed
        if task.status == 'Completed' and not task.completed_at:
             task.completed_by_id = current_user.id
             task.completed_at = now_utc()
        elif task.status == 'Pending':
             task.completed_by_id = None
             task.completed_at = None

        # Track edit history
        task.last_edited_by_id = current_user.id
        task.last_edited_at = now_utc()
        
        # Handle child tasks assignment
        child_ids_str = request.form.get('child_ids', '')
        if child_ids_str:
            try:
                child_ids = [int(id.strip()) for id in child_ids_str.split(',') if id.strip()]
                # Get current children IDs
                current_child_ids = [c.id for c in task.children]
                
                # Update children - set parent_id for new children
                for child_id in child_ids:
                    if child_id != task.id and child_id not in current_child_ids:
                        child_task = Task.query.get(child_id)
                        if child_task and not is_descendant(child_id, task.id):
                            child_task.parent_id = task.id
                
                # Remove parent_id from children that were removed
                for current_child_id in current_child_ids:
                    if current_child_id not in child_ids:
                        child_task = Task.query.get(current_child_id)
                        if child_task:
                            child_task.parent_id = None
            except (ValueError, TypeError):
                pass  # Invalid child_ids, ignore
        else:
            # Clear all children if no child_ids provided
            for child in task.children:
                child.parent_id = None

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

@main_bp.route('/task-tree')
@login_required
def task_tree():
    """Display all tasks in a hierarchical tree view"""
    from models import Area
    
    # Get filter parameters (same as dashboard)
    filter_assignee = request.args.get('assignee')
    filter_creator = request.args.get('creator')
    filter_status = request.args.get('status', '')
    filter_tag = request.args.get('tag_filter')
    filter_area = request.args.get('area')
    sort_order = request.args.get('sort', 'asc')
    search_query = request.args.get('q', '')
    
    # Base query: get all root tasks (tasks without parent)
    query = Task.query.options(
        joinedload(Task.children),
        joinedload(Task.assignees),
        joinedload(Task.tags)
    ).filter(Task.parent_id == None)
    
    # --- ROLE-BASED VISIBILITY FILTERING ---
    user_area_ids = [a.id for a in current_user.areas]
    
    if current_user.can_only_see_own_tasks():
        # Users can only see tasks they are assigned to OR created
        if user_area_ids:
            query = query.filter(
                db.or_(
                    Task.assignees.any(id=current_user.id),
                    Task.creator_id == current_user.id
                )
            ).filter(Task.area_id.in_(user_area_ids))
        else:
            query = query.filter(Task.area_id == -1)
        available_areas = current_user.areas
        show_area_filter = False
    elif current_user.can_see_all_areas():
        # Gerentes/admins see all tasks
        if filter_area:
            query = query.filter(Task.area_id == int(filter_area))
        available_areas = Area.query.order_by(Area.name).all()
        show_area_filter = True
    else:
        # Supervisors see all tasks in their area
        if user_area_ids:
            query = query.filter(Task.area_id.in_(user_area_ids))
        else:
            query = query.filter(Task.area_id == -1)
        available_areas = current_user.areas
        show_area_filter = False
    
    # Apply assignee filter
    if filter_assignee:
        query = query.filter(Task.assignees.any(id=filter_assignee))
    
    # Apply creator filter
    if filter_creator:
        query = query.filter(Task.creator_id == filter_creator)
    
    # Apply status filter - exclude 'Anulado' by default
    if filter_status:
        if filter_status in ['Pending', 'Completed', 'Anulado']:
            query = query.filter(Task.status == filter_status)
    else:
        query = query.filter(Task.status != 'Anulado')
    
    # Apply tag filter
    if filter_tag:
        query = query.filter(Task.tags.any(id=int(filter_tag)))
    
    # Apply search filter
    if search_query:
        search_term = f"%{search_query}%"
        query = query.filter(
            (Task.title.ilike(search_term)) | 
            (Task.description.ilike(search_term))
        )
    
    # Sort by status first (Pending before Completed), then by due_date
    status_order = db.case(
        (Task.status == 'Pending', 0),
        (Task.status == 'Completed', 1),
        else_=2
    )
    
    if sort_order == 'desc':
        root_tasks = query.order_by(status_order, Task.due_date.desc()).all()
    else:
        root_tasks = query.order_by(status_order, Task.due_date.asc()).all()
    
    # Get counts for stats - FILTERED BY AREA
    stats_query_base = Task.query.filter(Task.status != 'Anulado')
    if not current_user.is_admin:
        if user_area_ids:
            stats_query_base = stats_query_base.filter(Task.area_id.in_(user_area_ids))
        else:
            stats_query_base = stats_query_base.filter(Task.area_id == -1)
    
    total_tasks = stats_query_base.count()
    tasks_with_children = stats_query_base.filter(Task.children.any()).count()
    tasks_with_parent = stats_query_base.filter(Task.parent_id != None).count()
    
    # Get users and tags for filter dropdowns - FILTERED BY AREA
    if current_user.is_admin:
        users = User.query.all()
        all_tags = Tag.query.order_by(Tag.name).all()
    else:
        users = [u for u in User.query.all() if any(area in u.areas for area in current_user.areas)]
        # Strict filter - only tags from user's areas
        if user_area_ids:
            all_tags = Tag.query.filter(Tag.area_id.in_(user_area_ids)).order_by(Tag.name).all()
        else:
            all_tags = []
    
    return render_template('task_tree.html', 
                           root_tasks=root_tasks,
                           filter_status=filter_status,
                           filter_assignee=filter_assignee,
                           filter_creator=filter_creator,
                           filter_tag=filter_tag,
                           filter_area=filter_area,
                           sort_order=sort_order,
                           search_query=search_query,
                           total_tasks=total_tasks,
                           tasks_with_children=tasks_with_children,
                           tasks_with_parent=tasks_with_parent,
                           users=users,
                           all_tags=all_tags,
                           all_areas=available_areas,
                           show_area_filter=show_area_filter)

@main_bp.route('/calendar')
@login_required
def calendar():
    from models import Area
    
    # Get filter parameters
    period = request.args.get('period', 'all')  # today, week, month, all
    start_date_str = request.args.get('start_date')
    end_date_str = request.args.get('end_date')
    filter_user = request.args.get('creator')  # Keep 'creator' param name for backward compatibility
    filter_area = request.args.get('area')
    
    # Base query: show ALL tasks by default (matching dashboard behavior)
    # Only show ENABLED tasks (not blocked by parent dependency)
    query = Task.query.options(joinedload(Task.assignees), joinedload(Task.tags)).filter(Task.enabled == True)
    
    # Exclude 'Anulado' tasks by default
    query = query.filter(Task.status != 'Anulado')
    
    # --- ROLE-BASED VISIBILITY FILTERING ---
    user_area_ids = [a.id for a in current_user.areas]
    
    if current_user.can_only_see_own_tasks():
        # Users can only see tasks they are assigned to OR created
        if user_area_ids:
            query = query.filter(
                db.or_(
                    Task.assignees.any(id=current_user.id),
                    Task.creator_id == current_user.id
                )
            ).filter(Task.area_id.in_(user_area_ids))
        else:
            query = query.filter(Task.area_id == -1)
        available_areas = current_user.areas
        show_area_filter = False
    elif current_user.can_see_all_areas():
        # Gerentes/admins see all tasks
        if filter_area:
            query = query.filter(Task.area_id == int(filter_area))
        available_areas = Area.query.order_by(Area.name).all()
        show_area_filter = True
    else:
        # Supervisors see all tasks in their area
        if user_area_ids:
            query = query.filter(Task.area_id.in_(user_area_ids))
        else:
            query = query.filter(Task.area_id == -1)
        available_areas = current_user.areas
        show_area_filter = False
    
    # Filter by user (assignee) if selected
    if filter_user:
        query = query.filter(Task.assignees.any(id=filter_user))
    
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
    
    # Filter users by area (same logic as dashboard)
    if current_user.can_see_all_areas():
        users = User.query.all()
    else:
        # Non-admins see only users in their areas
        users = [u for u in User.query.all() if any(area in u.areas for area in current_user.areas)]
    
    # Get event dates for calendar widget (dates with tasks the user can see)
    month_start = today.replace(day=1)
    if today.month == 12:
        month_end = today.replace(day=31)
    else:
        month_end = (today.replace(month=today.month + 1, day=1) - timedelta(days=1))
    
    # Build event_dates query with same visibility rules as main query
    event_dates_query = db.session.query(db.func.date(Task.due_date)).filter(
        Task.enabled == True,
        Task.status != 'Anulado',
        db.func.date(Task.due_date) >= month_start,
        db.func.date(Task.due_date) <= month_end
    )
    
    # Apply same visibility filtering to event_dates
    if current_user.can_only_see_own_tasks():
        if user_area_ids:
            event_dates_query = event_dates_query.filter(
                db.or_(
                    Task.assignees.any(id=current_user.id),
                    Task.creator_id == current_user.id
                )
            ).filter(Task.area_id.in_(user_area_ids))
        else:
            event_dates_query = event_dates_query.filter(Task.area_id == -1)
    elif not current_user.can_see_all_areas():
        # Supervisors see all tasks in their area
        if user_area_ids:
            event_dates_query = event_dates_query.filter(Task.area_id.in_(user_area_ids))
        else:
            event_dates_query = event_dates_query.filter(Task.area_id == -1)
    
    event_dates = [d[0].strftime('%Y-%m-%d') for d in event_dates_query.distinct().all() if d[0]]
    
    # --- CALENDAR GRID GENERATION ---
    import calendar as cal
    
    # Get month/year from query params or use current month
    view_year = int(request.args.get('year', today.year))
    view_month = int(request.args.get('month', today.month))
    
    # Calculate previous and next month for navigation
    if view_month == 1:
        prev_month, prev_year = 12, view_year - 1
    else:
        prev_month, prev_year = view_month - 1, view_year
    
    if view_month == 12:
        next_month, next_year = 1, view_year + 1
    else:
        next_month, next_year = view_month + 1, view_year
    
    # Generate calendar weeks (list of 7-day lists)
    cal_obj = cal.Calendar(firstweekday=0)  # Monday = 0
    month_days = cal_obj.monthdatescalendar(view_year, view_month)
    
    # Get tasks for the visible calendar range (includes prev/next month day spillover)
    if month_days:
        cal_start = month_days[0][0]
        cal_end = month_days[-1][-1]
        
        # Query tasks within calendar view range
        cal_tasks_query = Task.query.options(joinedload(Task.assignees), joinedload(Task.tags)).filter(
            Task.enabled == True,
            Task.status != 'Anulado',
            db.func.date(Task.due_date) >= cal_start,
            db.func.date(Task.due_date) <= cal_end
        )
        
        # Apply same visibility filters
        if current_user.can_only_see_own_tasks():
            if user_area_ids:
                cal_tasks_query = cal_tasks_query.filter(
                    db.or_(
                        Task.assignees.any(id=current_user.id),
                        Task.creator_id == current_user.id
                    )
                ).filter(Task.area_id.in_(user_area_ids))
            else:
                cal_tasks_query = cal_tasks_query.filter(Task.area_id == -1)
        elif not current_user.can_see_all_areas():
            if user_area_ids:
                cal_tasks_query = cal_tasks_query.filter(Task.area_id.in_(user_area_ids))
            else:
                cal_tasks_query = cal_tasks_query.filter(Task.area_id == -1)
        
        cal_tasks = cal_tasks_query.all()
    else:
        cal_tasks = []
    
    # Group tasks by date
    tasks_by_date = {}
    for task in cal_tasks:
        date_key = task.due_date.date().isoformat()
        if date_key not in tasks_by_date:
            tasks_by_date[date_key] = []
        tasks_by_date[date_key].append(task)
    
    # Month names in Spanish
    month_names = ['', 'Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio',
                   'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre']
    
    return render_template('calendar.html', 
                          tasks=tasks, 
                          current_period=period, 
                          today=today, 
                          users=users, 
                          event_dates=event_dates,
                          all_areas=available_areas,
                          show_area_filter=show_area_filter,
                          # New calendar grid data
                          calendar_weeks=month_days,
                          view_month=view_month,
                          view_year=view_year,
                          month_name=month_names[view_month],
                          prev_month=prev_month,
                          prev_year=prev_year,
                          next_month=next_month,
                          next_year=next_year,
                          tasks_by_date=tasks_by_date)


@main_bp.route('/task/<int:task_id>/toggle', methods=['POST'])
@login_required
def toggle_task_status(task_id):
    task = Task.query.get_or_404(task_id)
    
    # Verify user has access to this task (either creator or assignee)
    if task.creator_id != current_user.id and current_user not in task.assignees:
        return jsonify({'success': False, 'error': 'Acceso denegado'}), 403
    
    # Get optional completion comment from request body
    data = request.get_json() or {}
    completion_comment = data.get('comment', '').strip() if data else ''
    
    # Toggle status and track completion
    if task.status == 'Pending':
        task.status = 'Completed'
        task.completed_by_id = current_user.id
        task.completed_at = now_utc()
        task.completion_comment = completion_comment if completion_comment else None
        
        # Enable child tasks when parent is completed
        enabled_children_count = 0
        adjusted_dates_count = 0
        for child in task.children:
            if not child.enabled:
                child.enabled = True
                child.enabled_at = now_utc()
                child.enabled_by_task_id = task.id
                enabled_children_count += 1
                
                # If the child's due_date has already passed, adjust it to today
                if child.due_date.date() < date.today():
                    child.original_due_date = child.due_date  # Save original date before adjustment
                    child.due_date = now_utc()
                    adjusted_dates_count += 1
        
        if enabled_children_count > 0:
            msg = f'Se habilitaron {enabled_children_count} tarea(s) dependiente(s).'
            if adjusted_dates_count > 0:
                msg += f' Se ajustó la fecha de vencimiento de {adjusted_dates_count} tarea(s) que ya habían vencido.'
            flash(msg, 'info')
    else:
        # Note: We don't disable children when uncompleting - they stay enabled
        task.status = 'Pending'
        task.completed_by_id = None
        task.completed_at = None
        task.completion_comment = None  # Clear comment when reopening
    
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
    task.completed_at = now_utc()  # Track when
    
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
    
    filters = {}
    
    # Determine if this is from calendar (has period) or dashboard
    if period:
        # Calendar mode: show all tasks, filter by user (assignee) if selected
        query = Task.query.options(joinedload(Task.assignees), joinedload(Task.tags))
        
        # The calendar's 'creator' param is actually filtering by assignee now
        filter_user = request.args.get('creator')  # Calendar sends user filter as 'creator'
        if filter_user:
            query = query.filter(Task.assignees.any(id=filter_user))
            user = User.query.get(filter_user)
            filters['assignee_name'] = user.full_name if user else 'Desconocido'
        # If no user filter in calendar, show all tasks (no assignee_name filter shown)
    else:
        # Dashboard mode: start without user filter
        query = Task.query.options(joinedload(Task.assignees), joinedload(Task.tags))
        
        # Apply Assignee Filter (dashboard uses this)
        if filter_assignee:
            query = query.filter(Task.assignees.any(id=filter_assignee))
            assignee = User.query.get(filter_assignee)
            filters['assignee_name'] = assignee.full_name if assignee else 'Desconocido'
        
        # Apply Creator Filter (dashboard also has this)
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
    
    filters = {}
    
    # Determine if this is from calendar (has period) or dashboard
    if period:
        # Calendar mode: show all tasks, filter by user (assignee) if selected
        query = Task.query.options(joinedload(Task.assignees), joinedload(Task.tags))
        
        # The calendar's 'creator' param is actually filtering by assignee now
        filter_user = request.args.get('creator')  # Calendar sends user filter as 'creator'
        if filter_user:
            query = query.filter(Task.assignees.any(id=filter_user))
            user = User.query.get(filter_user)
            filters['assignee_name'] = user.full_name if user else 'Desconocido'
        # If no user filter in calendar, show all tasks (no assignee_name filter shown)
    else:
        # Dashboard mode: start without user filter
        query = Task.query.options(joinedload(Task.assignees), joinedload(Task.tags))
        
        # Apply Assignee Filter (dashboard uses this)
        if filter_assignee:
            query = query.filter(Task.assignees.any(id=filter_assignee))
            assignee = User.query.get(filter_assignee)
            filters['assignee_name'] = assignee.full_name if assignee else 'Desconocido'
        
        # Apply Creator Filter (dashboard also has this)
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
    from models import Area
    
    # Allow both admins and supervisors to manage users
    is_supervisor = current_user.role == 'supervisor'
    
    if not current_user.is_admin and not is_supervisor:
        flash('Acceso denegado.', 'danger')
        return redirect(url_for('main.dashboard'))
    
    # Supervisors can only see/manage their area
    if is_supervisor:
        supervisor_area = current_user.areas[0] if current_user.areas else None
        if not supervisor_area:
            flash('No tienes un área asignada. Contacta a un administrador.', 'danger')
            return redirect(url_for('main.dashboard'))
        all_areas = [supervisor_area]
    else:
        all_areas = Area.query.order_by(Area.name).all()
        
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        full_name = request.form.get('full_name')
        
        # Supervisors cannot create admins or other supervisors
        if is_supervisor:
            is_admin = False
            role = 'usuario'  # Supervisors can only create regular users
            area_ids = [str(supervisor_area.id)]  # Force to supervisor's area
        else:
            is_admin = 'is_admin' in request.form
            role = request.form.get('role', 'usuario')
            area_ids = request.form.getlist('areas')
        
        # Enforce: supervisors can only have 1 area
        if role == 'supervisor' and len(area_ids) > 1:
            area_ids = area_ids[:1]  # Keep only the first area
        
        if User.query.filter_by(username=username).first():
            flash('El nombre de usuario ya existe.', 'warning')
        else:
            new_user = User(
                username=username, 
                full_name=full_name, 
                is_admin=is_admin, 
                email=f"{username}@example.com",
                role=role
            )
            new_user.set_password(password)
            
            # Assign areas
            for area_id in area_ids:
                area = Area.query.get(int(area_id))
                if area:
                    new_user.areas.append(area)
            
            db.session.add(new_user)
            db.session.commit()
            flash('Usuario creado exitosamente.', 'success')
    
    # Get users to display
    if is_supervisor:
        # Supervisors only see users in their area
        users = [u for u in User.query.all() if supervisor_area in u.areas]
    else:
        users = User.query.all()
    
    return render_template('users.html', users=users, all_areas=all_areas, is_supervisor=is_supervisor)

# --- Area Management Routes ---
@admin_bp.route('/areas', methods=['GET', 'POST'])
@login_required
def manage_areas():
    """Manage areas (departments) - Admin only"""
    from models import Area
    
    if not current_user.is_admin:
        flash('Acceso denegado.', 'danger')
        return redirect(url_for('main.dashboard'))
    
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        description = request.form.get('description', '').strip()
        color = request.form.get('color', '#6366f1')
        
        if not name:
            flash('El nombre del área es requerido.', 'warning')
        elif Area.query.filter_by(name=name).first():
            flash('Ya existe un área con ese nombre.', 'warning')
        else:
            new_area = Area(
                name=name,
                description=description,
                color=color
            )
            db.session.add(new_area)
            db.session.commit()
            flash(f'Área "{name}" creada exitosamente.', 'success')
    
    areas = Area.query.order_by(Area.name).all()
    return render_template('manage_areas.html', areas=areas)

@admin_bp.route('/areas/<int:area_id>/delete', methods=['POST'])
@login_required
def delete_area(area_id):
    """Delete an area - Admin only"""
    from models import Area
    
    if not current_user.is_admin:
        flash('Acceso denegado.', 'danger')
        return redirect(url_for('main.dashboard'))
    
    area = Area.query.get_or_404(area_id)
    
    # Check if area has tasks
    task_count = area.tasks.count()
    if task_count > 0:
        flash(f'No se puede eliminar el área "{area.name}" porque tiene {task_count} tareas asignadas.', 'danger')
        return redirect(url_for('admin.manage_areas'))
    
    area_name = area.name
    db.session.delete(area)
    db.session.commit()
    flash(f'Área "{area_name}" eliminada.', 'success')
    return redirect(url_for('admin.manage_areas'))

@admin_bp.route('/users/<int:user_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_user(user_id):
    """Edit user - update role and areas - Admin only"""
    from models import Area
    
    if not current_user.is_admin:
        flash('Acceso denegado.', 'danger')
        return redirect(url_for('main.dashboard'))
    
    user = User.query.get_or_404(user_id)
    all_areas = Area.query.order_by(Area.name).all()
    
    if request.method == 'POST':
        user.full_name = request.form.get('full_name', user.full_name)
        user.is_admin = 'is_admin' in request.form
        user.role = request.form.get('role', 'usuario')
        
        # Update password if provided
        new_password = request.form.get('password', '').strip()
        if new_password:
            user.set_password(new_password)
        
        # Update areas
        area_ids = request.form.getlist('areas')
        
        # Enforce: supervisors can only have 1 area
        if user.role == 'supervisor' and len(area_ids) > 1:
            area_ids = area_ids[:1]  # Keep only the first area
            flash('Los supervisores solo pueden tener 1 área asignada. Se mantuvo la primera área seleccionada.', 'info')
        
        user.areas.clear()
        for area_id in area_ids:
            area = Area.query.get(int(area_id))
            if area:
                user.areas.append(area)
        
        db.session.commit()
        flash(f'Usuario "{user.username}" actualizado.', 'success')
        return redirect(url_for('admin.manage_users'))
    
    return render_template('edit_user.html', user=user, all_areas=all_areas)


# --- API Routes for Notifications ---
@main_bp.route('/api/tasks/due_soon')
@login_required
def api_tasks_due_soon():
    """
    Return tasks and expirations that are due soon or already overdue.
    Used for popup notifications.
    """
    if not current_user.notifications_enabled:
        return jsonify({'tasks': [], 'expirations': [], 'overdue_tasks': [], 'overdue_expirations': []})
    
    # Get all pending AND enabled tasks assigned to current user (exclude blocked tasks)
    pending_tasks = Task.query.filter(
        Task.assignees.any(id=current_user.id),
        Task.status == 'Pending',
        Task.enabled == True  # Only show enabled tasks (not blocked by parent)
    ).all()
    
    # Separate tasks into due soon and overdue
    due_soon_tasks = []
    overdue_tasks = []
    for task in pending_tasks:
        business_days = calculate_business_days_until(task.due_date)
        task_data = {
            'id': task.id,
            'title': task.title,
            'due_date': task.due_date.strftime('%d/%m/%Y'),
            'priority': task.priority,
            'description': task.description[:100] if task.description else '',
            'days_remaining': business_days,
            'type': 'task',
            'enabled_at': task.enabled_at.strftime('%d/%m/%Y') if task.enabled_at else None
        }
        if business_days < 0:  # Overdue
            task_data['days_overdue'] = abs(business_days)
            overdue_tasks.append(task_data)
        elif business_days <= 2:  # Due in 0, 1, or 2 business days
            due_soon_tasks.append(task_data)
    
    # Get all pending expirations (visible for everyone)
    pending_expirations = Expiration.query.filter(
        Expiration.completed == False
    ).all()
    
    # Separate expirations into due soon and overdue
    due_soon_expirations = []
    overdue_expirations = []
    for exp in pending_expirations:
        business_days = calculate_business_days_until(exp.due_date)
        exp_data = {
            'id': exp.id,
            'title': exp.title,
            'due_date': exp.due_date.strftime('%d/%m/%Y'),
            'description': exp.description[:100] if exp.description else '',
            'days_remaining': business_days,
            'type': 'expiration',
            'creator': exp.creator.full_name
        }
        if business_days < 0:  # Overdue
            exp_data['days_overdue'] = abs(business_days)
            overdue_expirations.append(exp_data)
        elif business_days <= 2:  # Due in 0, 1, or 2 business days
            due_soon_expirations.append(exp_data)
    
    return jsonify({
        'tasks': due_soon_tasks,
        'expirations': due_soon_expirations,
        'overdue_tasks': overdue_tasks,
        'overdue_expirations': overdue_expirations
    })

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
    """Tags management page - filtered by area"""
    if current_user.is_admin:
        all_tags = Tag.query.order_by(Tag.name).all()
    else:
        user_area_ids = [a.id for a in current_user.areas]
        if user_area_ids:
            all_tags = Tag.query.filter(Tag.area_id.in_(user_area_ids)).order_by(Tag.name).all()
        else:
            all_tags = []
    return render_template('tags.html', tags=all_tags)

@main_bp.route('/api/tags', methods=['GET'])
@login_required
def api_get_tags():
    """Get all tags - filtered by area"""
    if current_user.is_admin:
        tags = Tag.query.order_by(Tag.name).all()
    else:
        user_area_ids = [a.id for a in current_user.areas]
        if user_area_ids:
            tags = Tag.query.filter(Tag.area_id.in_(user_area_ids)).order_by(Tag.name).all()
        else:
            tags = []
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
    """Create a new tag - accessible to all users, assigns area automatically"""
    
    data = request.get_json()
    name = data.get('name', '').strip()
    color = data.get('color', '#2563eb')
    
    if not name:
        return jsonify({'success': False, 'message': 'El nombre es requerido'}), 400
    
    # Check if tag already exists
    existing = Tag.query.filter_by(name=name).first()
    if existing:
        return jsonify({'success': False, 'message': 'Este tag ya existe'}), 400
    
    # Determine area_id based on user
    # Non-admins get their first area automatically
    area_id = None
    if not current_user.is_admin and current_user.areas:
        area_id = current_user.areas[0].id
    
    new_tag = Tag(
        name=name,
        color=color,
        created_by_id=current_user.id,
        area_id=area_id
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
    from models import Area
    
    # --- CHECK PERMISSION TO VIEW REPORTS ---
    if not current_user.can_see_reports():
        flash('No tienes acceso a los reportes.', 'danger')
        return redirect(url_for('main.dashboard'))
    
    # Filter users by area for non-admins
    if current_user.is_admin:

        users = User.query.all()
        available_areas = Area.query.order_by(Area.name).all()
        show_area_filter = True
    else:
        # Non-admins see only users in their areas
        user_area_ids = [a.id for a in current_user.areas]
        if user_area_ids:
            users = [u for u in User.query.all() if any(area in u.areas for area in current_user.areas)]
        else:
            users = []
        available_areas = current_user.areas
        show_area_filter = False
    
    # Filter tags by area
    if current_user.is_admin:
        tags = Tag.query.order_by(Tag.name).all()
    else:
        user_area_ids = [a.id for a in current_user.areas]
        if user_area_ids:
            tags = Tag.query.filter(Tag.area_id.in_(user_area_ids)).order_by(Tag.name).all()
        else:
            tags = []
            
    return render_template('reports.html', 
                          users=users, 
                          tags=tags,
                          all_areas=available_areas,
                          show_area_filter=show_area_filter)

@main_bp.route('/api/reports/data', methods=['POST'])
@login_required
def reports_data():
    # --- CHECK PERMISSION TO VIEW REPORTS ---
    if not current_user.can_see_reports():
        return jsonify({'error': 'No tienes acceso a los reportes'}), 403
    
    data = request.get_json()

    user_ids = data.get('user_ids', [])
    tag_ids = data.get('tag_ids', []) # New filter
    status_filter = data.get('status') # New filter
    area_filter = data.get('area')  # Area filter (admin only)
    start_date_str = data.get('start_date')
    end_date_str = data.get('end_date')
    
    # Base query - ALWAYS exclude 'Anulado' and blocked tasks from reports
    query = Task.query.options(joinedload(Task.assignees), joinedload(Task.tags)).filter(
        Task.status != 'Anulado',
        Task.enabled == True  # Only include enabled tasks in reports
    )
    
    # --- FILTER BY AREA ---
    if current_user.is_admin:
        # Admin can filter by specific area
        if area_filter and area_filter != 'all':
            query = query.filter(Task.area_id == int(area_filter))
    else:
        # Non-admins see only tasks from their specific areas (NOT including NULL areas)
        user_area_ids = [a.id for a in current_user.areas]
        if user_area_ids:
            query = query.filter(Task.area_id.in_(user_area_ids))
        else:
            # User has no areas - show nothing
            query = query.filter(Task.area_id == -1)
    
    # Filter by users if provided
    if user_ids:
        query = query.filter(Task.assignees.any(User.id.in_(user_ids)))
        
    # Filter by tags if provided
    if tag_ids:
        query = query.filter(Task.tags.any(Tag.id.in_(tag_ids)))
        
    # Filter by status if provided
    if status_filter and status_filter != 'All':
        if status_filter == 'Overdue':
            # Overdue = Pending tasks with due_date < today
            today_date = date.today()
            query = query.filter(
                Task.status == 'Pending',
                db.func.date(Task.due_date) < today_date
            )
        else:
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
    
    # Fetch data - ALWAYS exclude 'Anulado' and blocked tasks from reports
    query = Task.query.filter(Task.status != 'Anulado', Task.enabled == True)
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
    if not current_user.can_create_tasks():
        flash('No tienes permiso para importar tareas.', 'danger')
        return redirect(url_for('main.dashboard'))
    
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
    # Check permission first
    if not current_user.can_create_tasks():
        flash('No tienes permiso para importar tareas.', 'danger')
        return redirect(url_for('main.dashboard'))
    
    # Determine user's area for automatic assignment (for non-admins)
    is_limited_creator = current_user.role in ['supervisor', 'usuario_plus']
    user_area_id = None
    
    if is_limited_creator:
        if current_user.areas:
            user_area_id = current_user.areas[0].id
        else:
            flash('No tienes un área asignada. Contacta a un administrador.', 'danger')
            return redirect(url_for('main.dashboard'))
    
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
            completado_por_str = row[8] if len(row) > 8 else ''
            
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
            
            # Parse completed_by user (optional)
            completed_by_user = None
            if completado_por_str:
                completed_by_username = str(completado_por_str).strip()
                if completed_by_username:
                    completed_by_user = User.query.filter_by(username=completed_by_username).first()
                    if not completed_by_user:
                        errors.append(f'Fila {row_num}: Usuario "{completed_by_username}" (Completado Por) no encontrado')
            
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
                status=status,
                area_id=user_area_id  # For non-admins, assigns to their area; for admins, None (inherits default)
            )
            
            # Set completed info if status is Completed
            if status == 'Completed':
                # Use specified user, or fallback to current user
                new_task.completed_by_id = completed_by_user.id if completed_by_user else current_user.id
                new_task.completed_at = now_utc()
            
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
    """View and create task templates - assigns area automatically"""
    # Check permission to create tasks (which includes templates)
    if not current_user.can_create_tasks():
        flash('No tienes permiso para gestionar plantillas de tareas.', 'danger')
        return redirect(url_for('main.dashboard'))
    
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
        
        # Determine area_id based on user
        area_id = None
        if not current_user.is_admin and current_user.areas:
            area_id = current_user.areas[0].id
        
        template = TaskTemplate(
            name=name,
            title=title,
            description=description,
            priority=priority,
            default_days=default_days,
            created_by_id=current_user.id,
            time_spent=time_spent,
            area_id=area_id
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
    
    # Filter templates and tags by area for non-admins
    if current_user.is_admin:
        templates = TaskTemplate.query.order_by(TaskTemplate.name).all()
        available_tags = Tag.query.order_by(Tag.name).all()
    else:
        user_area_ids = [a.id for a in current_user.areas]
        if user_area_ids:
            # Strict filter - only from user's areas
            templates = TaskTemplate.query.filter(TaskTemplate.area_id.in_(user_area_ids)).order_by(TaskTemplate.name).all()
            available_tags = Tag.query.filter(Tag.area_id.in_(user_area_ids)).order_by(Tag.name).all()
        else:
            templates = []
            available_tags = []
    
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


# --- Task Hierarchy Helper Functions ---
def is_descendant(parent_id, potential_child_id):
    """
    Check if potential_child_id is a descendant of parent_id.
    This prevents circular references in the task hierarchy.
    """
    if parent_id == potential_child_id:
        return True
    
    task = Task.query.get(potential_child_id)
    if not task or not task.parent_id:
        return False
    
    # Recursively check if parent_id is an ancestor
    return is_descendant(parent_id, task.parent_id)


# --- Task Hierarchy API Routes ---
@main_bp.route('/api/tasks/search')
@login_required
def api_search_tasks():
    """Search tasks for parent selection modal"""
    query = request.args.get('q', '').strip()
    exclude_id = request.args.get('exclude_id')
    
    if not query:
        return jsonify({'tasks': []})
    
    search_query = Task.query.filter(Task.status != 'Anulado')
    
    if query.isdigit():
        search_query = search_query.filter(
            (Task.id == int(query)) | (Task.title.ilike(f'%{query}%'))
        )
    else:
        search_query = search_query.filter(Task.title.ilike(f'%{query}%'))
    
    if exclude_id:
        try:
            search_query = search_query.filter(Task.id != int(exclude_id))
        except (ValueError, TypeError):
            pass
    
    tasks = search_query.order_by(Task.due_date.desc()).limit(20).all()
    
    result = []
    for task in tasks:
        result.append({
            'id': task.id,
            'title': task.title,
            'priority': task.priority,
            'status': task.status,
            'due_date': task.due_date.strftime('%d/%m/%Y'),
            'assignees': ', '.join([u.full_name for u in task.assignees])
        })
    
    return jsonify({'tasks': result})


@main_bp.route('/api/tasks/<int:task_id>/validate_parent/<int:parent_id>')
@login_required
def api_validate_parent(task_id, parent_id):
    """Validate that parent_id is not a descendant of task_id (prevent circular references)"""
    if task_id == parent_id:
        return jsonify({'valid': False, 'error': 'Una tarea no puede ser su propia tarea padre'})
    
    if is_descendant(task_id, parent_id):
        return jsonify({'valid': False, 'error': 'Referencia circular detectada'})
    
    return jsonify({'valid': True})


# --- Expiration Calendar Routes ---

@main_bp.route('/expirations')
@login_required
def expiration_calendar():
    """Calendario de vencimientos - filtrado por área"""
    from models import Area
    
    period = request.args.get('period', 'all')
    start_date_str = request.args.get('start_date')
    end_date_str = request.args.get('end_date')
    filter_tag = request.args.get('tag_filter')
    filter_area = request.args.get('area')
    
    # Query expirations with eager loading
    query = Expiration.query.options(joinedload(Expiration.tags), joinedload(Expiration.creator))
    
    # --- FILTER BY AREA ---
    # Admins can see all areas and use filter
    if current_user.is_admin:
        if filter_area:
            query = query.filter(Expiration.area_id == int(filter_area))
        available_areas = Area.query.order_by(Area.name).all()
        show_area_filter = True
    else:
        # Non-admins see only expirations from their specific areas (NOT including NULL areas)
        user_area_ids = [a.id for a in current_user.areas]
        if user_area_ids:
            query = query.filter(Expiration.area_id.in_(user_area_ids))
        else:
            # User has no areas - show nothing
            query = query.filter(Expiration.area_id == -1)
        available_areas = current_user.areas
        show_area_filter = False
    
    # Apply date filters
    today = date.today()
    
    if period == 'today':
        query = query.filter(db.func.date(Expiration.due_date) == today)
    elif period == 'week':
        week_start = today - timedelta(days=today.weekday())
        week_end = week_start + timedelta(days=6)
        query = query.filter(db.func.date(Expiration.due_date) >= week_start,
                           db.func.date(Expiration.due_date) <= week_end)
    elif period == 'month':
        month_start = today.replace(day=1)
        if today.month == 12:
            month_end = today.replace(day=31)
        else:
            month_end = (today.replace(month=today.month + 1, day=1) - timedelta(days=1))
        query = query.filter(db.func.date(Expiration.due_date) >= month_start,
                           db.func.date(Expiration.due_date) <= month_end)
    elif start_date_str and end_date_str:
        try:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
            query = query.filter(db.func.date(Expiration.due_date) >= start_date,
                               db.func.date(Expiration.due_date) <= end_date)
        except ValueError:
            pass
    
    # Apply tag filter
    if filter_tag:
        query = query.filter(Expiration.tags.any(id=int(filter_tag)))
    
    expirations = query.order_by(Expiration.due_date.asc()).all()
    available_tags = Tag.query.order_by(Tag.name).all()
    
    # Get event dates for calendar widget (all dates with expirations in current month)
    month_start = today.replace(day=1)
    if today.month == 12:
        month_end = today.replace(day=31)
    else:
        month_end = (today.replace(month=today.month + 1, day=1) - timedelta(days=1))
    
    event_dates_query = db.session.query(db.func.date(Expiration.due_date)).filter(
        db.func.date(Expiration.due_date) >= month_start,
        db.func.date(Expiration.due_date) <= month_end
    ).distinct().all()
    event_dates = [d[0].strftime('%Y-%m-%d') for d in event_dates_query if d[0]]
    
    # --- CALENDAR GRID GENERATION ---
    import calendar as cal
    
    # Get month/year from query params or use current month
    view_year = int(request.args.get('year', today.year))
    view_month = int(request.args.get('month', today.month))
    
    # Calculate previous and next month for navigation
    if view_month == 1:
        prev_month, prev_year = 12, view_year - 1
    else:
        prev_month, prev_year = view_month - 1, view_year
    
    if view_month == 12:
        next_month, next_year = 1, view_year + 1
    else:
        next_month, next_year = view_month + 1, view_year
    
    # Generate calendar weeks (list of 7-day lists)
    cal_obj = cal.Calendar(firstweekday=0)  # Monday = 0
    month_days = cal_obj.monthdatescalendar(view_year, view_month)
    
    # Get expirations for the visible calendar range
    if month_days:
        cal_start = month_days[0][0]
        cal_end = month_days[-1][-1]
        
        # Query expirations within calendar view range
        cal_exp_query = Expiration.query.options(joinedload(Expiration.tags)).filter(
            db.func.date(Expiration.due_date) >= cal_start,
            db.func.date(Expiration.due_date) <= cal_end
        )
        
        # Apply same visibility filters
        if not current_user.is_admin:
            user_area_ids = [a.id for a in current_user.areas]
            if user_area_ids:
                cal_exp_query = cal_exp_query.filter(Expiration.area_id.in_(user_area_ids))
            else:
                cal_exp_query = cal_exp_query.filter(Expiration.area_id == -1)
        
        cal_expirations = cal_exp_query.all()
    else:
        cal_expirations = []
    
    # Group expirations by date
    expirations_by_date = {}
    for exp in cal_expirations:
        date_key = exp.due_date.date().isoformat()
        if date_key not in expirations_by_date:
            expirations_by_date[date_key] = []
        expirations_by_date[date_key].append(exp)
    
    # Month names in Spanish
    month_names = ['', 'Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio',
                   'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre']
    
    return render_template('expiration_calendar.html', 
                          expirations=expirations, 
                          current_period=period, 
                          today=today,
                          available_tags=available_tags,
                          event_dates=event_dates,
                          all_areas=available_areas,
                          show_area_filter=show_area_filter,
                          # New calendar grid data
                          calendar_weeks=month_days,
                          view_month=view_month,
                          view_year=view_year,
                          month_name=month_names[view_month],
                          prev_month=prev_month,
                          prev_year=prev_year,
                          next_month=next_month,
                          next_year=next_year,
                          expirations_by_date=expirations_by_date)


@main_bp.route('/expirations/create', methods=['POST'])
@login_required
def create_expiration():
    """Crear un nuevo vencimiento - asigna área automáticamente"""
    title = request.form.get('title')
    description = request.form.get('description', '')
    due_date_str = request.form.get('due_date')
    
    if not title or not due_date_str:
        flash('Título y fecha de vencimiento son requeridos.', 'danger')
        return redirect(url_for('main.expiration_calendar'))
    
    try:
        due_date = datetime.strptime(due_date_str, '%Y-%m-%d')
    except ValueError:
        flash('Formato de fecha inválido.', 'danger')
        return redirect(url_for('main.expiration_calendar'))
    
    # Determine area_id based on user role
    # Non-admins get their first area automatically
    area_id = None
    if not current_user.is_admin and current_user.areas:
        area_id = current_user.areas[0].id
    
    new_expiration = Expiration(
        title=title,
        description=description,
        due_date=due_date,
        creator_id=current_user.id,
        area_id=area_id
    )
    
    # Add tags
    tag_ids = request.form.getlist('tags')
    for tag_id in tag_ids:
        tag = Tag.query.get(int(tag_id))
        if tag:
            new_expiration.tags.append(tag)
    
    db.session.add(new_expiration)
    db.session.commit()
    
    flash('Vencimiento creado exitosamente.', 'success')
    return redirect(url_for('main.expiration_calendar'))


@main_bp.route('/expirations/<int:expiration_id>/edit', methods=['POST'])
@login_required
def edit_expiration(expiration_id):
    """Editar un vencimiento existente"""
    expiration = Expiration.query.get_or_404(expiration_id)
    
    # Only creator or admin can edit
    if expiration.creator_id != current_user.id and not current_user.is_admin:
        flash('No tienes permiso para editar este vencimiento.', 'danger')
        return redirect(url_for('main.expiration_calendar'))
    
    title = request.form.get('title')
    description = request.form.get('description', '')
    due_date_str = request.form.get('due_date')
    
    if not title or not due_date_str:
        flash('Título y fecha de vencimiento son requeridos.', 'danger')
        return redirect(url_for('main.expiration_calendar'))
    
    try:
        due_date = datetime.strptime(due_date_str, '%Y-%m-%d')
    except ValueError:
        flash('Formato de fecha inválido.', 'danger')
        return redirect(url_for('main.expiration_calendar'))
    
    expiration.title = title
    expiration.description = description
    expiration.due_date = due_date
    
    # Update tags
    tag_ids = request.form.getlist('tags')
    expiration.tags = []
    for tag_id in tag_ids:
        tag = Tag.query.get(int(tag_id))
        if tag:
            expiration.tags.append(tag)
    
    db.session.commit()
    
    flash('Vencimiento actualizado exitosamente.', 'success')
    return redirect(url_for('main.expiration_calendar'))


@main_bp.route('/expirations/<int:expiration_id>/toggle', methods=['POST'])
@login_required
def toggle_expiration(expiration_id):
    """Marcar vencimiento como completado/pendiente"""
    expiration = Expiration.query.get_or_404(expiration_id)
    
    if expiration.completed:
        expiration.completed = False
        expiration.completed_at = None
    else:
        expiration.completed = True
        expiration.completed_at = now_utc()
    
    db.session.commit()
    
    return jsonify({
        'success': True,
        'expiration_id': expiration.id,
        'completed': expiration.completed
    })


@main_bp.route('/expirations/<int:expiration_id>/delete', methods=['POST'])
@login_required
def delete_expiration(expiration_id):
    """Eliminar un vencimiento"""
    expiration = Expiration.query.get_or_404(expiration_id)
    
    # Only creator or admin can delete
    if expiration.creator_id != current_user.id and not current_user.is_admin:
        return jsonify({'success': False, 'error': 'No tienes permiso para eliminar este vencimiento.'}), 403
    
    db.session.delete(expiration)
    db.session.commit()
    
    return jsonify({'success': True})


@main_bp.route('/api/expirations/<int:expiration_id>')
@login_required
def api_get_expiration(expiration_id):
    """API para obtener datos de un vencimiento para edición"""
    expiration = Expiration.query.get_or_404(expiration_id)
    
    return jsonify({
        'id': expiration.id,
        'title': expiration.title,
        'description': expiration.description or '',
        'due_date': expiration.due_date.strftime('%Y-%m-%d'),
        'tag_ids': [tag.id for tag in expiration.tags],
        'completed': expiration.completed
    })


# --- Recurring Tasks Routes (Admin Only) ---

@main_bp.route('/recurring-tasks')
@login_required
def manage_recurring_tasks():
    """Listar y gestionar tareas recurrentes"""
    # Check permission to create tasks
    if not current_user.can_create_tasks():
        flash('No tienes permiso para gestionar tareas recurrentes.', 'danger')
        return redirect(url_for('main.dashboard'))
    
    # Filter by area - admins/gerentes see all, others see only their area
    if current_user.can_see_all_areas():
        recurring_tasks = RecurringTask.query.order_by(RecurringTask.created_at.desc()).all()
        users = User.query.order_by(User.full_name).all()
        available_tags = Tag.query.order_by(Tag.name).all()
    else:
        # Supervisor/usuario_plus: only see recurring tasks from their area
        user_area_ids = [a.id for a in current_user.areas]
        if user_area_ids:
            # Strict filter - only from user's areas
            recurring_tasks = RecurringTask.query.filter(RecurringTask.area_id.in_(user_area_ids)).order_by(RecurringTask.created_at.desc()).all()
            # Only show users from their areas
            users = [u for u in User.query.order_by(User.full_name).all() if any(area in u.areas for area in current_user.areas)]
            available_tags = Tag.query.filter(Tag.area_id.in_(user_area_ids)).order_by(Tag.name).all()
        else:
            recurring_tasks = []
            users = []
            available_tags = []
    
    return render_template('manage_recurring_tasks.html',
                           recurring_tasks=recurring_tasks,
                           users=users,
                           available_tags=available_tags)


@main_bp.route('/recurring-tasks/create', methods=['POST'])
@login_required
def create_recurring_task():
    """Crear una nueva tarea recurrente"""
    # Check permission to create tasks
    if not current_user.can_create_tasks():
        flash('No tienes permiso para crear tareas recurrentes.', 'danger')
        return redirect(url_for('main.dashboard'))
    
    title = request.form.get('title')
    description = request.form.get('description', '')
    priority = request.form.get('priority', 'Normal')
    recurrence_type = request.form.get('recurrence_type')
    days_of_week = request.form.get('days_of_week', '')
    day_of_month_str = request.form.get('day_of_month', '')
    due_time_str = request.form.get('due_time')
    start_date_str = request.form.get('start_date')
    end_date_str = request.form.get('end_date', '')
    time_spent_str = request.form.get('time_spent', '0')
    assignee_ids = request.form.getlist('assignees')
    tag_ids = request.form.getlist('tags')
    
    # Validations
    if not title or not recurrence_type or not due_time_str or not start_date_str:
        flash('Título, tipo de recurrencia, hora y fecha de inicio son requeridos.', 'danger')
        return redirect(url_for('main.manage_recurring_tasks'))
    
    if not assignee_ids:
        flash('Debes asignar al menos un usuario.', 'danger')
        return redirect(url_for('main.manage_recurring_tasks'))
    
    # Parse time
    try:
        from datetime import time as dt_time
        hour, minute = map(int, due_time_str.split(':'))
        due_time = dt_time(hour, minute)
    except ValueError:
        flash('Formato de hora inválido.', 'danger')
        return redirect(url_for('main.manage_recurring_tasks'))
    
    # Parse dates
    try:
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date() if end_date_str else None
    except ValueError:
        flash('Formato de fecha inválido.', 'danger')
        return redirect(url_for('main.manage_recurring_tasks'))
    
    # Parse day_of_month for monthly recurrence
    day_of_month = None
    if recurrence_type == 'monthly' and day_of_month_str:
        try:
            day_of_month = int(day_of_month_str)
            if day_of_month < 1 or day_of_month > 31:
                raise ValueError()
        except ValueError:
            flash('Día del mes inválido (1-31).', 'danger')
            return redirect(url_for('main.manage_recurring_tasks'))
    
    # Parse time_spent
    try:
        time_spent = int(time_spent_str) if time_spent_str else 0
    except ValueError:
        time_spent = 0
    
    # Determine area_id based on user
    area_id = None
    if not current_user.is_admin and current_user.areas:
        area_id = current_user.areas[0].id
    
    # Parse custom_dates for custom recurrence
    custom_dates = None
    if recurrence_type == 'custom':
        custom_dates_str = request.form.get('custom_dates', '')
        if custom_dates_str:
            custom_dates = custom_dates_str  # Already JSON string from frontend
    
    # Create recurring task
    new_recurring = RecurringTask(
        title=title,
        description=description,
        priority=priority,
        recurrence_type=recurrence_type,
        days_of_week=days_of_week if recurrence_type == 'weekly' else None,
        day_of_month=day_of_month,
        custom_dates=custom_dates,
        due_time=due_time,
        start_date=start_date,
        end_date=end_date,
        time_spent=time_spent,
        creator_id=current_user.id,
        is_active=True,
        area_id=area_id
    )
    
    # Add assignees
    for uid in assignee_ids:
        user = User.query.get(int(uid))
        if user:
            new_recurring.assignees.append(user)
    
    # Add tags
    for tid in tag_ids:
        tag = Tag.query.get(int(tid))
        if tag:
            new_recurring.tags.append(tag)
    
    db.session.add(new_recurring)
    db.session.commit()
    
    flash(f'Tarea recurrente "{title}" creada exitosamente.', 'success')
    return redirect(url_for('main.manage_recurring_tasks'))


@main_bp.route('/recurring-tasks/<int:rt_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_recurring_task(rt_id):
    """Editar una tarea recurrente"""
    # Check permission to create tasks
    if not current_user.can_create_tasks():
        flash('No tienes permiso para editar tareas recurrentes.', 'danger')
        return redirect(url_for('main.dashboard'))
    
    rt = RecurringTask.query.get_or_404(rt_id)
    
    # Non-admins can only edit recurring tasks from their area
    if not current_user.can_see_all_areas():
        user_area_ids = [a.id for a in current_user.areas]
        if rt.area_id not in user_area_ids and rt.area_id is not None:
            flash('No tienes permiso para editar esta tarea recurrente.', 'danger')
            return redirect(url_for('main.manage_recurring_tasks'))
    
    if request.method == 'POST':
        rt.title = request.form.get('title', rt.title)
        rt.description = request.form.get('description', '')
        rt.priority = request.form.get('priority', 'Normal')
        rt.recurrence_type = request.form.get('recurrence_type', rt.recurrence_type)
        
        # Update days_of_week for weekly
        if rt.recurrence_type == 'weekly':
            rt.days_of_week = request.form.get('days_of_week', '')
        else:
            rt.days_of_week = None
        
        # Update day_of_month for monthly
        if rt.recurrence_type == 'monthly':
            day_str = request.form.get('day_of_month', '')
            rt.day_of_month = int(day_str) if day_str else None
        else:
            rt.day_of_month = None
        
        # Update custom_dates for custom recurrence
        if rt.recurrence_type == 'custom':
            rt.custom_dates = request.form.get('custom_dates', '')
        else:
            rt.custom_dates = None
        
        # Update time
        due_time_str = request.form.get('due_time')
        if due_time_str:
            from datetime import time as dt_time
            hour, minute = map(int, due_time_str.split(':'))
            rt.due_time = dt_time(hour, minute)
        
        # Update dates
        start_date_str = request.form.get('start_date')
        if start_date_str:
            rt.start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
        
        end_date_str = request.form.get('end_date', '')
        rt.end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date() if end_date_str else None
        
        # Update time_spent
        time_spent_str = request.form.get('time_spent', '0')
        rt.time_spent = int(time_spent_str) if time_spent_str else 0
        
        # Update assignees
        assignee_ids = request.form.getlist('assignees')
        rt.assignees = []
        for uid in assignee_ids:
            user = User.query.get(int(uid))
            if user:
                rt.assignees.append(user)
        
        # Update tags
        tag_ids = request.form.getlist('tags')
        rt.tags = []
        for tid in tag_ids:
            tag = Tag.query.get(int(tid))
            if tag:
                rt.tags.append(tag)
        
        db.session.commit()
        flash('Tarea recurrente actualizada.', 'success')
        return redirect(url_for('main.manage_recurring_tasks'))
    
    # GET - show edit form
    users = User.query.order_by(User.full_name).all()
    available_tags = Tag.query.order_by(Tag.name).all()
    return render_template('edit_recurring_task.html', rt=rt, users=users, available_tags=available_tags)


@main_bp.route('/recurring-tasks/<int:rt_id>/toggle', methods=['POST'])
@login_required
def toggle_recurring_task(rt_id):
    """Pausar/Reanudar una tarea recurrente"""
    # Check permission to create tasks
    if not current_user.can_create_tasks():
        return jsonify({'success': False, 'error': 'No autorizado'}), 403
    
    rt = RecurringTask.query.get_or_404(rt_id)
    
    # Non-admins can only toggle recurring tasks from their area
    if not current_user.can_see_all_areas():
        user_area_ids = [a.id for a in current_user.areas]
        if rt.area_id not in user_area_ids and rt.area_id is not None:
            return jsonify({'success': False, 'error': 'No autorizado para esta tarea'}), 403
    
    rt.is_active = not rt.is_active
    db.session.commit()
    
    status = 'activada' if rt.is_active else 'pausada'
    return jsonify({
        'success': True,
        'is_active': rt.is_active,
        'message': f'Tarea recurrente {status}'
    })


@main_bp.route('/recurring-tasks/<int:rt_id>/delete', methods=['POST'])
@login_required
def delete_recurring_task(rt_id):
    """Eliminar una tarea recurrente - Solo admin"""
    if not current_user.is_admin:
        return jsonify({'success': False, 'error': 'No autorizado'}), 403
    
    rt = RecurringTask.query.get_or_404(rt_id)
    title = rt.title
    db.session.delete(rt)
    db.session.commit()
    
    return jsonify({'success': True, 'message': f'Tarea recurrente "{title}" eliminada'})


@main_bp.route('/api/recurring-tasks/generate-now', methods=['POST'])
@login_required
def generate_recurring_tasks_now():
    """Forzar generación de tareas recurrentes ahora - Solo admin (para testing)"""
    if not current_user.is_admin:
        return jsonify({'success': False, 'error': 'No autorizado'}), 403
    
    from flask import current_app
    from scheduler import generate_daily_tasks
    
    try:
        generate_daily_tasks(current_app._get_current_object())
        return jsonify({'success': True, 'message': 'Tareas generadas exitosamente'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@main_bp.route('/api/recurring-tasks/<int:rt_id>')
@login_required
def api_get_recurring_task(rt_id):
    """API para obtener datos de una tarea recurrente"""
    if not current_user.is_admin:
        return jsonify({'error': 'No autorizado'}), 403
    
    rt = RecurringTask.query.get_or_404(rt_id)
    
    return jsonify({
        'id': rt.id,
        'title': rt.title,
        'description': rt.description or '',
        'priority': rt.priority,
        'recurrence_type': rt.recurrence_type,
        'days_of_week': rt.days_of_week or '',
        'day_of_month': rt.day_of_month,
        'custom_dates': rt.custom_dates or '',
        'due_time': rt.due_time.strftime('%H:%M') if rt.due_time else '',
        'start_date': rt.start_date.strftime('%Y-%m-%d') if rt.start_date else '',
        'end_date': rt.end_date.strftime('%Y-%m-%d') if rt.end_date else '',
        'time_spent': rt.time_spent or 0,
        'is_active': rt.is_active,
        'assignee_ids': [u.id for u in rt.assignees],
        'tag_ids': [t.id for t in rt.tags]
    })
