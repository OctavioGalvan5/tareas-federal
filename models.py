from datetime import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from extensions import db, login_manager

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Association table for Many-to-Many relationship between Users and Areas
user_areas = db.Table('user_areas',
    db.Column('user_id', db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), primary_key=True),
    db.Column('area_id', db.Integer, db.ForeignKey('area.id', ondelete='CASCADE'), primary_key=True)
)

class Area(db.Model):
    """
    Áreas de la organización: Federal, Contable, Legajos, Provincial, etc.
    Los usuarios pertenecen a una o más áreas y solo ven tareas de sus áreas.
    Los gerentes pueden ver todas las áreas.
    """
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    description = db.Column(db.Text, nullable=True)
    color = db.Column(db.String(7), nullable=False, default='#6366f1')  # Hex color
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<Area {self.name}>'

# Association table for Many-to-Many relationship between Users and Tasks
task_assignments = db.Table('task_assignments',
    db.Column('user_id', db.Integer, db.ForeignKey('user.id'), primary_key=True),
    db.Column('task_id', db.Integer, db.ForeignKey('task.id'), primary_key=True)
)

# Association table for Many-to-Many relationship between Tasks and Tags
task_tags = db.Table('task_tags',
    db.Column('task_id', db.Integer, db.ForeignKey('task.id', ondelete='CASCADE'), primary_key=True),
    db.Column('tag_id', db.Integer, db.ForeignKey('tag.id', ondelete='CASCADE'), primary_key=True)
)

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    full_name = db.Column(db.String(100), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    notifications_enabled = db.Column(db.Boolean, default=True)
    
    # Role: 'usuario' (default), 'usuario_plus', 'supervisor', 'gerente'
    # usuario: can only see own tasks (assigned or created), cannot create tasks, cannot see reports
    # usuario_plus: can create tasks but cannot see reports, can only see own tasks
    # supervisor: can see all tasks in their area, can create tasks, can see reports
    # gerente: can see ALL tasks from ALL areas
    role = db.Column(db.String(20), nullable=False, default='usuario')
    
    # Relationships - specify foreign_keys to avoid ambiguity
    created_tasks = db.relationship('Task', foreign_keys='Task.creator_id', backref='creator', lazy=True)
    assigned_tasks = db.relationship('Task', secondary=task_assignments, backref=db.backref('assignees', lazy=True))
    
    # Many-to-Many relationship with Areas
    areas = db.relationship('Area', secondary=user_areas, backref=db.backref('users', lazy='dynamic'))

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def can_see_all_areas(self):
        """Check if user can see tasks from all areas (gerente role)"""
        return self.role == 'gerente' or self.is_admin
    
    def can_see_all_area_tasks(self):
        """Check if user can see all tasks from their areas (not just assigned)"""
        return self.role in ['supervisor', 'gerente'] or self.is_admin
    
    def can_only_see_own_tasks(self):
        """Check if user can only see tasks assigned to them or created by them"""
        return self.role in ['usuario', 'usuario_plus']
    
    def can_create_tasks(self):
        """Check if user can create tasks"""
        return self.role in ['usuario_plus', 'supervisor', 'gerente'] or self.is_admin
    
    def can_see_reports(self):
        """Check if user can see reports - only supervisor, gerente, and admin"""
        return self.role in ['supervisor', 'gerente'] or self.is_admin

class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    priority = db.Column(db.String(20), nullable=False, default='Normal') # Normal, Media, Urgente
    status = db.Column(db.String(20), nullable=False, default='Pending') # Pending, In Progress, In Review, Completed, Anulado
    planned_start_date = db.Column(db.DateTime, nullable=True)  # Planned start date/time (default 8:00 AM)
    due_date = db.Column(db.DateTime, nullable=False)  # Due date/time (default 2:00 PM)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    creator_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    # Area assignment - nullable for backward compatibility during migration
    area_id = db.Column(db.Integer, db.ForeignKey('area.id'), nullable=True)
    area = db.relationship('Area', backref=db.backref('tasks', lazy='dynamic'))
    
    # Tracking "In Progress" status
    started_at = db.Column(db.DateTime, nullable=True)  # When moved to "In Progress"
    started_by_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    started_by = db.relationship('User', foreign_keys=[started_by_id])
    
    # Tracking "In Review" status
    in_review_at = db.Column(db.DateTime, nullable=True)  # When moved to "In Review"
    in_review_by_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    in_review_by = db.relationship('User', foreign_keys=[in_review_by_id])
    
    # Tracking completion
    completed_by_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    completed_at = db.Column(db.DateTime, nullable=True)
    
    # Tracking edits
    last_edited_by_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    last_edited_at = db.Column(db.DateTime, nullable=True)
    
    # Relationship for completed_by
    completed_by = db.relationship('User', foreign_keys=[completed_by_id])
    
    # Relationship for last_edited_by
    last_edited_by = db.relationship('User', foreign_keys=[last_edited_by_id])
    
    # Relationship for tags
    tags = db.relationship('Tag', secondary=task_tags, backref=db.backref('tasks', lazy='dynamic'))
    
    # Time tracking (in minutes)
    time_spent = db.Column(db.Integer, nullable=True)  # Time spent in minutes
    
    # Parent-Child Task Relationship
    parent_id = db.Column(db.Integer, db.ForeignKey('task.id'), nullable=True)
    parent = db.relationship('Task', remote_side=[id], backref='children', foreign_keys=[parent_id])
    
    # Task Dependency/Blocking - tasks with a parent start as disabled
    enabled = db.Column(db.Boolean, default=True)  # Is task enabled/unblocked?
    enabled_at = db.Column(db.DateTime, nullable=True)  # When was it enabled?
    enabled_by_task_id = db.Column(db.Integer, db.ForeignKey('task.id'), nullable=True)  # Which task enabled it?
    enabled_by_task = db.relationship('Task', foreign_keys=[enabled_by_task_id], remote_side=[id])
    original_due_date = db.Column(db.DateTime, nullable=True)  # Original due_date before auto-adjustment
    
    # Recurring task origin
    recurring_task_id = db.Column(db.Integer, db.ForeignKey('recurring_task.id'), nullable=True)
    recurring_task = db.relationship('RecurringTask', backref='generated_tasks')

    # Comment added on completion
    completion_comment = db.Column(db.Text, nullable=True)

    def __repr__(self):
        return f'<Task {self.title}>'

class Tag(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    color = db.Column(db.String(7), nullable=False)  # Hex color code (#RRGGBB)
    created_by_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Area assignment - nullable for backward compatibility
    area_id = db.Column(db.Integer, db.ForeignKey('area.id'), nullable=True)
    area = db.relationship('Area', backref=db.backref('tags', lazy='dynamic'))
    
    # Relationship for creator
    created_by = db.relationship('User', backref='created_tags')
    
    def __repr__(self):
        return f'<Tag {self.name}>'

# Association table for Many-to-Many relationship between TaskTemplates and Tags
template_tags = db.Table('template_tags',
    db.Column('template_id', db.Integer, db.ForeignKey('task_template.id', ondelete='CASCADE'), primary_key=True),
    db.Column('tag_id', db.Integer, db.ForeignKey('tag.id', ondelete='CASCADE'), primary_key=True)
)

class TaskTemplate(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)  # Template name for selection
    title = db.Column(db.String(200), nullable=False)  # Default task title
    description = db.Column(db.Text, nullable=True)  # Default description
    priority = db.Column(db.String(20), nullable=False, default='Normal')  # Normal, Media, Urgente
    default_days = db.Column(db.Integer, nullable=False, default=0)  # Days from today for due date (0 = today)
    created_by_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    time_spent = db.Column(db.Integer, nullable=True, default=0)  # Default time spent in minutes
    
    # Area assignment - nullable for backward compatibility
    area_id = db.Column(db.Integer, db.ForeignKey('area.id'), nullable=True)
    area = db.relationship('Area', backref=db.backref('templates', lazy='dynamic'))
    
    # Relationships
    created_by = db.relationship('User', backref='created_templates')
    tags = db.relationship('Tag', secondary=template_tags, backref=db.backref('templates', lazy='dynamic'))
    
    def __repr__(self):
        return f'<TaskTemplate {self.name}>'

# Association table for Many-to-Many relationship between Expirations and Tags
expiration_tags = db.Table('expiration_tags',
    db.Column('expiration_id', db.Integer, db.ForeignKey('expiration.id', ondelete='CASCADE'), primary_key=True),
    db.Column('tag_id', db.Integer, db.ForeignKey('tag.id', ondelete='CASCADE'), primary_key=True)
)

class Expiration(db.Model):
    """
    Vencimientos: entradas de calendario visibles para todos los usuarios.
    A diferencia de las tareas, cualquier usuario puede crear vencimientos.
    No se incluyen en reportes.
    """
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    due_date = db.Column(db.DateTime, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    creator_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    completed = db.Column(db.Boolean, default=False)
    completed_at = db.Column(db.DateTime, nullable=True)
    
    # Area assignment - nullable for backward compatibility
    area_id = db.Column(db.Integer, db.ForeignKey('area.id'), nullable=True)
    area = db.relationship('Area', backref=db.backref('expirations', lazy='dynamic'))
    
    # Relationships
    creator = db.relationship('User', backref='expirations')
    tags = db.relationship('Tag', secondary=expiration_tags, backref=db.backref('expirations', lazy='dynamic'))
    
    def __repr__(self):
        return f'<Expiration {self.title}>'

# Association table for Many-to-Many relationship between RecurringTasks and Users (assignees)
recurring_task_assignments = db.Table('recurring_task_assignments',
    db.Column('recurring_task_id', db.Integer, db.ForeignKey('recurring_task.id', ondelete='CASCADE'), primary_key=True),
    db.Column('user_id', db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), primary_key=True)
)

# Association table for Many-to-Many relationship between RecurringTasks and Tags
recurring_task_tags = db.Table('recurring_task_tags',
    db.Column('recurring_task_id', db.Integer, db.ForeignKey('recurring_task.id', ondelete='CASCADE'), primary_key=True),
    db.Column('tag_id', db.Integer, db.ForeignKey('tag.id', ondelete='CASCADE'), primary_key=True)
)

class RecurringTask(db.Model):
    """
    Tareas Recurrentes: define tareas que se crean automáticamente
    según una programación (días hábiles, días específicos, etc.)
    Solo los administradores pueden crear/editar tareas recurrentes.
    """
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    priority = db.Column(db.String(20), nullable=False, default='Normal')  # Normal, Media, Urgente
    
    # Area assignment - nullable for backward compatibility
    area_id = db.Column(db.Integer, db.ForeignKey('area.id'), nullable=True)
    area = db.relationship('Area', backref=db.backref('recurring_tasks', lazy='dynamic'))
    
    # Recurrence configuration
    recurrence_type = db.Column(db.String(20), nullable=False)  # 'weekdays', 'weekly', 'monthly', 'custom'
    days_of_week = db.Column(db.String(20), nullable=True)  # "1,2,3,4,5" for Mon-Fri, "1,3,5" for specific days
    day_of_month = db.Column(db.Integer, nullable=True)  # For monthly: 1-31
    custom_dates = db.Column(db.Text, nullable=True)  # JSON array: ["2026-01-15", "2026-02-20", ...]
    
    # Schedule
    due_time = db.Column(db.Time, nullable=False)  # When the task is due (e.g., 18:00)
    start_date = db.Column(db.Date, nullable=False)  # When to start creating tasks
    end_date = db.Column(db.Date, nullable=True)  # When to stop (NULL = forever)
    
    # Time tracking default
    time_spent = db.Column(db.Integer, nullable=True, default=0)  # Default time spent in minutes
    
    # Status
    is_active = db.Column(db.Boolean, default=True)  # Pause/Resume
    
    # Metadata
    creator_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_generated_date = db.Column(db.Date, nullable=True)  # Track last generation
    
    # Relationships
    creator = db.relationship('User', foreign_keys=[creator_id], backref='created_recurring_tasks')
    assignees = db.relationship('User', secondary=recurring_task_assignments,
                                backref=db.backref('assigned_recurring_tasks', lazy='dynamic'))
    tags = db.relationship('Tag', secondary=recurring_task_tags,
                           backref=db.backref('recurring_tasks', lazy='dynamic'))
    
    def __repr__(self):
        return f'<RecurringTask {self.title}>'


class ActivityLog(db.Model):
    """
    Registro de actividades para auditoría.
    Solo visible para administradores (todas las áreas) y supervisores (solo su área).
    """
    __tablename__ = 'activity_log'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Quién realizó la acción
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    user = db.relationship('User', backref=db.backref('activity_logs', lazy='dynamic'))
    
    # Tipo de acción
    action = db.Column(db.String(50), nullable=False)  # 'task_created', 'task_completed', etc.
    
    # Descripción legible
    description = db.Column(db.String(500), nullable=False)  # "creó la tarea #123"
    
    # Objeto afectado (opcional)
    target_type = db.Column(db.String(50), nullable=True)  # 'task', 'expiration', etc.
    target_id = db.Column(db.Integer, nullable=True)
    
    # Área asociada (para filtrado de supervisores)
    area_id = db.Column(db.Integer, db.ForeignKey('area.id'), nullable=True)
    area = db.relationship('Area', backref=db.backref('activity_logs', lazy='dynamic'))

    # Detalles adicionales (JSON format)
    details = db.Column(db.Text, nullable=True)
    
    # Timestamp (se convierte a hora de Buenos Aires en la vista)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<ActivityLog {self.action} by {self.user_id}>'


class StatusTransition(db.Model):
    """Registro de transiciones de estado de tareas"""
    id = db.Column(db.Integer, primary_key=True)
    task_id = db.Column(db.Integer, db.ForeignKey('task.id'), nullable=False)
    
    # Estados: from -> to
    from_status = db.Column(db.String(50), nullable=False)
    to_status = db.Column(db.String(50), nullable=False)
    
    # Usuario que realizó el cambio
    changed_by_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    changed_by = db.relationship('User', backref='status_transitions')
    
    # Optional comment
    comment = db.Column(db.Text)
    
    # Timestamp
    changed_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relación con la tarea
    # Relación con la tarea
    task = db.relationship('Task', backref=db.backref('status_history', order_by='StatusTransition.changed_at'))
    
    def __repr__(self):
        return f'<StatusTransition {self.from_status} -> {self.to_status}>'
