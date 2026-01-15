"""
Scheduler for generating recurring tasks daily.
Uses APScheduler to run at 00:05 Buenos Aires time.
"""
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime, date, time, timedelta
import holidays
import pytz

BUENOS_AIRES_TZ = pytz.timezone('America/Argentina/Buenos_Aires')

# Argentine holidays
AR_HOLIDAYS = holidays.Argentina()


def is_business_day(check_date):
    """Check if a date is a business day (Mon-Fri, not a holiday)."""
    if check_date.weekday() >= 5:  # Saturday (5) or Sunday (6)
        return False
    if check_date in AR_HOLIDAYS:
        return False
    return True


def should_generate_today(recurring_task, today):
    """Determine if a recurring task should generate a task for today."""
    # Check if task is active
    if not recurring_task.is_active:
        return False
    
    # Check date range
    if recurring_task.start_date > today:
        return False
    if recurring_task.end_date and recurring_task.end_date < today:
        return False
    
    # Prevent duplicate generation on same day
    if recurring_task.last_generated_date == today:
        return False
    
    recurrence_type = recurring_task.recurrence_type
    
    if recurrence_type == 'weekdays':
        # Monday to Friday, excluding holidays
        return is_business_day(today)
    
    elif recurrence_type == 'weekly':
        # days_of_week: "1,3,5" means Mon, Wed, Fri (1=Monday, 7=Sunday)
        if not recurring_task.days_of_week:
            return False
        allowed_days = [int(d) for d in recurring_task.days_of_week.split(',')]
        weekday = today.isoweekday()  # 1=Monday, 7=Sunday
        # Check if it's an allowed day and not a holiday
        return weekday in allowed_days and today not in AR_HOLIDAYS
    
    elif recurrence_type == 'monthly':
        # day_of_month: 1-31
        if not recurring_task.day_of_month:
            return False
        # Check if it's the right day and not a holiday
        return today.day == recurring_task.day_of_month and today not in AR_HOLIDAYS
    
    elif recurrence_type == 'custom':
        # custom_dates: JSON array of ISO date strings
        if not recurring_task.custom_dates:
            return False
        import json
        try:
            custom_dates = json.loads(recurring_task.custom_dates)
            return today.isoformat() in custom_dates
        except (json.JSONDecodeError, TypeError):
            return False
    
    return False


def generate_daily_tasks(app):
    """Job that runs daily to create tasks from recurring definitions."""
    with app.app_context():
        from models import RecurringTask, Task
        from extensions import db
        
        today = date.today()
        generated_count = 0
        
        recurring_tasks = RecurringTask.query.filter_by(is_active=True).all()
        
        for rt in recurring_tasks:
            if should_generate_today(rt, today):
                # Create the due datetime
                due_datetime = datetime.combine(today, rt.due_time)
                
                # Determine task properties - use template if available, otherwise use inline values
                if rt.template_id and rt.template:
                    template = rt.template
                    task_title = template.title
                    task_description = template.description
                    task_priority = template.priority
                    task_area_id = template.area_id or rt.area_id
                else:
                    task_title = rt.title
                    task_description = rt.description
                    task_priority = rt.priority
                    task_area_id = rt.area_id
                
                # Create new task
                task = Task(
                    title=task_title,
                    description=task_description,
                    priority=task_priority,
                    due_date=due_datetime,
                    creator_id=rt.creator_id,
                    area_id=task_area_id,
                    time_spent=rt.time_spent,
                    recurring_task_id=rt.id,
                    status='Pending',
                    enabled=True
                )
                
                # Copy assignees
                for user in rt.assignees:
                    task.assignees.append(user)
                
                # Copy tags - from template if available, otherwise from recurring task
                if rt.template_id and rt.template:
                    for tag in rt.template.tags:
                        task.tags.append(tag)
                else:
                    for tag in rt.tags:
                        task.tags.append(tag)
                
                db.session.add(task)
                db.session.flush()  # Get task ID for subtask creation
                
                # Create subtasks from template if template exists
                if rt.template_id and rt.template:
                    from routes import create_subtasks_from_template
                    from models import User
                    creator = User.query.get(rt.creator_id)
                    create_subtasks_from_template(
                        template=rt.template,
                        parent_task=task,
                        assignees=list(rt.assignees),
                        creator=creator,
                        area_id=task_area_id
                    )
                
                # Update last generated date
                rt.last_generated_date = today
                generated_count += 1
        
        db.session.commit()
        
        # Log the result
        now = datetime.now(BUENOS_AIRES_TZ)
        print(f"[Scheduler] {now.strftime('%Y-%m-%d %H:%M:%S')} - Generated {generated_count} tasks for {today}")


def init_scheduler(app):
    """Initialize and start the scheduler."""
    scheduler = BackgroundScheduler(timezone=BUENOS_AIRES_TZ)
    
    # Run daily at 00:05 Buenos Aires time
    trigger = CronTrigger(hour=0, minute=5, timezone=BUENOS_AIRES_TZ)
    scheduler.add_job(
        generate_daily_tasks,
        trigger=trigger,
        args=[app],
        id='generate_recurring_tasks',
        name='Generate Recurring Tasks Daily',
        replace_existing=True
    )
    
    # Run daily at 00:10 to activate scheduled tasks whose start date has arrived
    trigger_activate = CronTrigger(hour=0, minute=10, timezone=BUENOS_AIRES_TZ)
    scheduler.add_job(
        activate_scheduled_tasks,
        trigger=trigger_activate,
        args=[app],
        id='activate_scheduled_tasks',
        name='Activate Scheduled Tasks',
        replace_existing=True
    )
    
    scheduler.start()
    print(f"[Scheduler] Started - Daily task generation at 00:05, scheduled task activation at 00:10 (Buenos Aires)")
    
    return scheduler


def activate_scheduled_tasks(app):
    """
    Activate tasks whose planned_start_date has arrived.
    Changes status from 'Scheduled' to 'Pending'.
    """
    with app.app_context():
        from models import Task
        from extensions import db
        
        today = date.today()
        
        # Find scheduled tasks whose planned_start_date <= today
        scheduled_tasks = Task.query.filter(
            Task.status == 'Scheduled',
            db.func.date(Task.planned_start_date) <= today
        ).all()
        
        activated_count = 0
        for task in scheduled_tasks:
            task.status = 'Pending'
            activated_count += 1
        
        db.session.commit()
        
        now = datetime.now(BUENOS_AIRES_TZ)
        print(f"[Scheduler] {now.strftime('%Y-%m-%d %H:%M:%S')} - Activated {activated_count} scheduled tasks")

