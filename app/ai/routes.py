from datetime import datetime, date, timedelta
from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user

from app.extensions import db
from app.models import Plan, Task, ChatLog
from app.xp_rules import base_xp_for_category
from app.ai.gemini_client import generate_daily_plan, adjust_plan

ai_bp = Blueprint("ai", __name__, url_prefix="/ai")


def _parse_time(time_str):
    """Converts 'HH:MM' string from Gemini into a datetime.time object."""
    if not time_str:
        return None
    try:
        return datetime.strptime(time_str, "%H:%M").time()
    except ValueError:
        return None


def _update_streak():
    """Call this whenever a user actively engages with a new day's plan."""
    today = date.today()
    if current_user.last_active_date == today:
        return  # already counted today
    elif current_user.last_active_date == today - timedelta(days=1):
        current_user.current_streak += 1
    else:
        current_user.current_streak = 1  # streak broken or first day

    current_user.longest_streak = max(current_user.longest_streak, current_user.current_streak)
    current_user.last_active_date = today


@ai_bp.route("/generate-plan", methods=["POST"])
@login_required
def generate_plan():
    existing = Plan.query.filter_by(user_id=current_user.id, plan_date=date.today()).first()
    if existing:
        return jsonify({"error": "plan already exists for today"}), 400

    try:
        result = generate_daily_plan(current_user)
    except Exception as e:
        return jsonify({"error": f"Dayli couldn't generate your plan right now: {e}"}), 502

    plan = Plan(user_id=current_user.id, plan_date=date.today())
    db.session.add(plan)
    db.session.flush()  # get plan.id before creating tasks

    for task_data in result.get("tasks", []):
        task = Task(
            plan_id=plan.id,
            title=task_data["title"],
            category=task_data["category"],
            scheduled_time=_parse_time(task_data.get("scheduled_time")),
            duration_minutes=task_data.get("duration_minutes"),
            xp_value=base_xp_for_category(task_data["category"]),
        )
        db.session.add(task)

    _update_streak()
    db.session.commit()

    return jsonify({
        "plan_id": plan.id,
        "summary": result.get("summary", ""),
        "redirect_url": "/dashboard/",
    })


@ai_bp.route("/chat", methods=["POST"])
@login_required
def chat():
    data = request.get_json(silent=True) or {}
    user_message = (data.get("message") or "").strip()
    if not user_message:
        return jsonify({"error": "message is required"}), 400

    today_plan = Plan.query.filter_by(user_id=current_user.id, plan_date=date.today()).first()
    if today_plan is None:
        return jsonify({"error": "no active plan for today"}), 400

    # Log the user's message before calling the AI
    db.session.add(ChatLog(
        user_id=current_user.id,
        plan_id=today_plan.id,
        role="user",
        message=user_message,
    ))
    db.session.commit()

    recent_history = (
        ChatLog.query
        .filter_by(user_id=current_user.id, plan_id=today_plan.id)
        .order_by(ChatLog.created_at.desc())
        .limit(10)
        .all()
    )
    recent_history.reverse()

    try:
        result = adjust_plan(current_user, today_plan.tasks, user_message, chat_history=recent_history)
    except Exception as e:
        return jsonify({"error": f"Dayli couldn't process that right now: {e}"}), 502

    # Apply updates onto real Task rows
    updated_task_summaries = []
    for update in result.get("updated_tasks", []):
        task = Task.query.get(update.get("task_id"))
        if task is None or task.plan_id != today_plan.id:
            continue  # ignore anything that doesn't belong to this plan

        if update.get("new_scheduled_time"):
            new_time = _parse_time(update["new_scheduled_time"])
            if new_time and task.scheduled_time != new_time:
                task.original_time = task.original_time or task.scheduled_time
                task.scheduled_time = new_time
                task.status = "rescheduled"

        if update.get("new_duration_minutes"):
            task.duration_minutes = update["new_duration_minutes"]

        if update.get("new_status") in Task.STATUSES:
            task.status = update["new_status"]

        updated_task_summaries.append({
            "task_id": task.id,
            "title": task.title,
            "scheduled_time": task.scheduled_time.strftime("%H:%M") if task.scheduled_time else None,
            "duration_minutes": task.duration_minutes,
            "status": task.status,
        })

    today_plan.last_adjusted_at = datetime.utcnow()

    ai_message = result.get("message", "")
    db.session.add(ChatLog(
        user_id=current_user.id,
        plan_id=today_plan.id,
        role="ai",
        message=ai_message,
    ))
    db.session.commit()

    return jsonify({
        "message": ai_message,
        "updated_tasks": updated_task_summaries,
    })