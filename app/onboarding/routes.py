from flask import Blueprint, render_template, redirect, url_for, request
from flask_login import login_required, current_user

from app.extensions import db

onboarding_bp = Blueprint("onboarding", __name__, url_prefix="/onboarding")

# Order matters — this drives which question shows on which step.
STEPS = [
    "goals",
    "current_habits",
    "target_habits",
    "schedule",
    "struggles",
    "preferred_activities",
    "extra_notes",
]


@onboarding_bp.route("/")
@login_required
def start():
    if current_user.onboarding_complete:
        return redirect(url_for("dashboard.home"))
    return redirect(url_for("onboarding.step", step_name=STEPS[0]))


@onboarding_bp.route("/step/<step_name>", methods=["GET", "POST"])
@login_required
def step(step_name):
    if step_name not in STEPS:
        return redirect(url_for("onboarding.start"))

    step_index = STEPS.index(step_name)

    if request.method == "POST":
        _save_step(step_name, request.form)
        db.session.commit()

        if step_index + 1 < len(STEPS):
            next_step = STEPS[step_index + 1]
            return redirect(url_for("onboarding.step", step_name=next_step))
        else:
            current_user.onboarding_complete = True
            db.session.commit()
            return redirect(url_for("onboarding.generating"))

    return render_template(
        f"onboarding/{step_name}.html",
        step_index=step_index,
        total_steps=len(STEPS),
    )


def _save_step(step_name, form):
    """Maps each onboarding step's form data onto the User model."""
    if step_name == "goals":
        current_user.goals = form.getlist("goals")
    elif step_name == "current_habits":
        current_user.current_habits = form.getlist("current_habits")
    elif step_name == "target_habits":
        current_user.target_habits = form.getlist("target_habits")
    elif step_name == "schedule":
        current_user.schedule = {
            "wake_time": form.get("wake_time", ""),
            "sleep_time": form.get("sleep_time", ""),
            "free_hours": form.get("free_hours", ""),
        }
    elif step_name == "struggles":
        current_user.struggles = form.getlist("struggles")
    elif step_name == "preferred_activities":
        current_user.preferred_activities = form.getlist("preferred_activities")
    elif step_name == "extra_notes":
        current_user.extra_notes = form.get("extra_notes", "").strip()


@onboarding_bp.route("/generating")
@login_required
def generating():
    # Renders a short "creating your day..." screen, then the frontend JS
    # calls the AI plan-generation endpoint (built in app/ai/routes.py)
    # and redirects to the dashboard once the plan is ready.
    return render_template("onboarding/generating.html")