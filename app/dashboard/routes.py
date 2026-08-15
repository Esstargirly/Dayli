from datetime import date
from flask import Blueprint, render_template, redirect, url_for, jsonify
from flask_login import login_required, current_user

from app.extensions import db
from app.models import Plan, Task, XPEvent
from app.xp_rules import BONUS_XP

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

    return render_template(
        "dashboard/home.html",
        plan=today_plan,
        tasks_by_category=tasks_by_category,
        xp_total=current_user.xp_total,
        current_streak=current_user.current_streak,
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

    from datetime import datetime
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
    return render_template(
        "dashboard/progress.html",
        xp_total=current_user.xp_total,
        current_streak=current_user.current_streak,
        longest_streak=current_user.longest_streak,
        xp_events=xp_events,
    )