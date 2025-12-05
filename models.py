from datetime import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from extensions import db, login_manager

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

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
    
    # Relationships - specify foreign_keys to avoid ambiguity
    created_tasks = db.relationship('Task', foreign_keys='Task.creator_id', backref='creator', lazy=True)
    assigned_tasks = db.relationship('Task', secondary=task_assignments, backref=db.backref('assignees', lazy=True))

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    priority = db.Column(db.String(20), nullable=False, default='Normal') # Normal, Media, Urgente
    status = db.Column(db.String(20), nullable=False, default='Pending') # Pending, Completed
    due_date = db.Column(db.DateTime, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    creator_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
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

    def __repr__(self):
        return f'<Task {self.title}>'

class Tag(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    color = db.Column(db.String(7), nullable=False)  # Hex color code (#RRGGBB)
    created_by_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
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
    
    # Relationships
    created_by = db.relationship('User', backref='created_templates')
    tags = db.relationship('Tag', secondary=template_tags, backref=db.backref('templates', lazy='dynamic'))
    
    def __repr__(self):
        return f'<TaskTemplate {self.name}>'
