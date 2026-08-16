from datetime import date, datetime, timedelta
from flask import Blueprint, render_template, redirect, url_for, jsonify
from flask_login import login_required, current_user

from app.extensions import db
from app.models import Plan, Task, XPEvent
from app.xp_rules import BONUS_XP, level_for_xp

dashboard_bp = Blueprint("dashboard", __name__, url_prefix="/dashboard")


@dashboard_bp.route("/")
@login_required
def home():
    if not current_user.onboarding_complete:
        return redirect(url_for("onboarding.start"))

    today_plan = (
        Plan.query
        .filter_by(user_id=current_user.id, plan_date=date.today())
        .first()
    )

    if today_plan is None:
        # No plan yet for today — send them to generate one.
        return redirect(url_for("onboarding.generating"))

    tasks_by_category = {"sleep": [], "movement": [], "hydration": [], "mental_wellbeing": []}
    for task in today_plan.tasks:
        tasks_by_category.setdefault(task.category, []).append(task)

    category_stats = {}
    for category, tasks in tasks_by_category.items():
        completed = sum(1 for t in tasks if t.status == "completed")
        category_stats[category] = {"completed": completed, "total": len(tasks)}

    hour = datetime.now().hour
    if hour < 12:
        greeting = "Good morning"
    elif hour < 18:
        greeting = "Good afternoon"
    else:
        greeting = "Good evening"

    today_xp_possible = sum(t.xp_value for t in today_plan.tasks)
    today_xp_earned = sum(t.xp_value for t in today_plan.tasks if t.status == "completed")
    today_progress_pct = int((today_xp_earned / today_xp_possible) * 100) if today_xp_possible else 0

    return render_template(
        "dashboard/home.html",
        plan=today_plan,
        tasks_by_category=tasks_by_category,
        category_stats=category_stats,
        xp_total=current_user.xp_total,
        current_streak=current_user.current_streak,
        greeting=greeting,
        today_progress_pct=today_progress_pct,
    )


@dashboard_bp.route("/task/<int:task_id>/complete", methods=["POST"])
@login_required
def complete_task(task_id):
    task = Task.query.get_or_404(task_id)

    # Make sure this task actually belongs to the logged-in user.
    if task.plan.user_id != current_user.id:
        return jsonify({"error": "not found"}), 404

    if task.status == "completed":
        return jsonify({"error": "already completed"}), 400

    task.status = "completed"
    task.completed_at = datetime.utcnow()

    xp_awarded = task.xp_value
    db.session.add(XPEvent(
        user_id=current_user.id,
        task_id=task.id,
        amount=xp_awarded,
        reason="task_completed",
    ))

    # Bonus: completed all tasks in today's plan
    all_tasks = task.plan.tasks
    if all(t.status == "completed" for t in all_tasks):
        bonus = BONUS_XP["full_day_complete"]
        xp_awarded += bonus
        db.session.add(XPEvent(
            user_id=current_user.id,
            task_id=None,
            amount=bonus,
            reason="full_day_complete",
        ))

    current_user.xp_total += xp_awarded
    db.session.commit()

    return jsonify({
        "status": "completed",
        "xp_awarded": xp_awarded,
        "xp_total": current_user.xp_total,
    })


@dashboard_bp.route("/task/<int:task_id>/skip", methods=["POST"])
@login_required
def skip_task(task_id):
    task = Task.query.get_or_404(task_id)
    if task.plan.user_id != current_user.id:
        return jsonify({"error": "not found"}), 404

    task.status = "skipped"
    db.session.commit()
    return jsonify({"status": "skipped"})


@dashboard_bp.route("/progress")
@login_required
def progress():
    xp_events = (
        XPEvent.query
        .filter_by(user_id=current_user.id)
        .order_by(XPEvent.created_at.desc())
        .limit(30)
        .all()
    )

    level_info = level_for_xp(current_user.xp_total)

    today = date.today()
    monday = today - timedelta(days=today.weekday())
    week_days = []
    for i in range(7):
        day = monday + timedelta(days=i)
        plan_for_day = Plan.query.filter_by(user_id=current_user.id, plan_date=day).first()
        completed_any = bool(plan_for_day and any(t.status == "completed" for t in plan_for_day.tasks))
        week_days.append({
            "label": day.strftime("%a")[0],
            "completed": completed_any,
            "is_today": day == today,
            "is_future": day > today,
        })
    days_logged_this_week = sum(1 for d in week_days if d["completed"])

    has_bounced_back = XPEvent.query.filter_by(user_id=current_user.id, reason="recovery_bonus").first() is not None
    has_perfect_day = XPEvent.query.filter_by(user_id=current_user.id, reason="full_day_complete").first() is not None
    completed_tasks = (
        Task.query.join(Plan)
        .filter(Plan.user_id == current_user.id, Task.status == "completed", Task.completed_at.isnot(None))
        .all()
    )
    has_early_bird = any(t.completed_at.hour < 8 for t in completed_tasks)

    return render_template(
        "dashboard/progress.html",
        xp_total=current_user.xp_total,
        current_streak=current_user.current_streak,
        longest_streak=current_user.longest_streak,
        xp_events=xp_events,
        level_info=level_info,
        week_days=week_days,
        days_logged_this_week=days_logged_this_week,
        has_bounced_back=has_bounced_back,
        has_perfect_day=has_perfect_day,
        has_early_bird=has_early_bird,
    )


@dashboard_bp.route("/updated")
@login_required
def updated():
    today_plan = Plan.query.filter_by(user_id=current_user.id, plan_date=date.today()).first()
    if today_plan is None:
        return redirect(url_for("dashboard.home"))

    rescheduled_tasks = [
        t for t in today_plan.tasks
        if t.status == "rescheduled" and t.original_time is not None
    ]
    rescheduled_tasks.sort(key=lambda t: t.scheduled_time or t.original_time)

    return render_template("dashboard/updated.html", rescheduled_tasks=rescheduled_tasks)

@dashboard_bp.route("/profile")
@login_required
def profile():
    return render_template("dashboard/profile.html")