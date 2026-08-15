from datetime import datetime, date
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

from app.extensions import db


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)

    # Onboarding profile — kept as JSON so we don't need a rigid schema
    # for hackathon-speed iteration. Populated after the onboarding flow.
    goals = db.Column(db.JSON, default=list)              # e.g. ["better sleep", "lose weight"]
    current_habits = db.Column(db.JSON, default=list)
    target_habits = db.Column(db.JSON, default=list)
    schedule = db.Column(db.JSON, default=dict)            # e.g. {"wake": "07:00", "free_hours": [...]}
    struggles = db.Column(db.JSON, default=list)           # e.g. ["low energy evenings", "inconsistent sleep"]
    preferred_activities = db.Column(db.JSON, default=list)  # e.g. ["gym", "meditation", "walking"]
    extra_notes = db.Column(db.Text, default="")            # free-text "anything else Dayli should know"
    onboarding_complete = db.Column(db.Boolean, default=False)

    # Gamification
    xp_total = db.Column(db.Integer, default=0)
    current_streak = db.Column(db.Integer, default=0)
    longest_streak = db.Column(db.Integer, default=0)
    last_active_date = db.Column(db.Date, nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    plans = db.relationship("Plan", backref="user", lazy=True, cascade="all, delete-orphan")
    xp_events = db.relationship("XPEvent", backref="user", lazy=True, cascade="all, delete-orphan")
    chat_logs = db.relationship("ChatLog", backref="user", lazy=True, cascade="all, delete-orphan")

    def set_password(self, raw_password):
        self.password_hash = generate_password_hash(raw_password)

    def check_password(self, raw_password):
        return check_password_hash(self.password_hash, raw_password)

    def __repr__(self):
        return f"<User {self.email}>"


class Plan(db.Model):
    """One day's wellness plan for a user."""
    __tablename__ = "plans"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    plan_date = db.Column(db.Date, default=date.today, nullable=False)

    # Raw AI generation context, kept for debugging/regeneration
    ai_raw_response = db.Column(db.Text, nullable=True)
    generated_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_adjusted_at = db.Column(db.DateTime, nullable=True)

    tasks = db.relationship("Task", backref="plan", lazy=True, cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Plan {self.plan_date} user={self.user_id}>"


class Task(db.Model):
    """A single scheduled item within a day's plan (e.g. workout, hydration check-in)."""
    __tablename__ = "tasks"

    CATEGORIES = ("sleep", "movement", "hydration", "mental_wellbeing")
    STATUSES = ("pending", "completed", "rescheduled", "skipped")

    id = db.Column(db.Integer, primary_key=True)
    plan_id = db.Column(db.Integer, db.ForeignKey("plans.id"), nullable=False)

    title = db.Column(db.String(200), nullable=False)
    category = db.Column(db.String(30), nullable=False)
    scheduled_time = db.Column(db.Time, nullable=True)
    original_time = db.Column(db.Time, nullable=True)   # set when rescheduled, for showing before/after
    duration_minutes = db.Column(db.Integer, nullable=True)
    status = db.Column(db.String(20), default="pending")
    xp_value = db.Column(db.Integer, default=10)

    completed_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<Task {self.title} ({self.status})>"


class XPEvent(db.Model):
    """Log of every XP award, so streaks/history can be reconstructed and displayed."""
    __tablename__ = "xp_events"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    task_id = db.Column(db.Integer, db.ForeignKey("tasks.id"), nullable=True)

    amount = db.Column(db.Integer, nullable=False)
    reason = db.Column(db.String(120), nullable=False)  # e.g. "task_completed", "streak_bonus", "early_completion"
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<XPEvent +{self.amount} {self.reason}>"


class ChatLog(db.Model):
    """Conversation history with the AI assistant, for context + demo replay."""
    __tablename__ = "chat_logs"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    plan_id = db.Column(db.Integer, db.ForeignKey("plans.id"), nullable=True)

    role = db.Column(db.String(10), nullable=False)  # "user" or "ai"
    message = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<ChatLog {self.role}: {self.message[:30]}>"