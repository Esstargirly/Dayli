from flask import Blueprint, render_template, redirect, url_for, request
from flask_login import login_required, current_user

from app.extensions import db

onboarding_bp = Blueprint("onboarding", __name__, url_prefix="/onboarding")

STEPS = ["goals", "current_routine", "struggles", "activities"]


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
    if step_name == "goals":
        current_user.goals = form.getlist("goals")
        current_user.target_habits = form.getlist("target_habits")
    elif step_name == "current_routine":
        current_user.current_habits = form.getlist("current_habits")
        current_user.schedule = {
            "wake_time": form.get("wake_time", ""),
            "sleep_time": form.get("sleep_time", ""),
        }
    elif step_name == "struggles":
        current_user.struggles = form.getlist("derailment")
        current_user.extra_notes = form.get("extra_notes", "").strip()
    elif step_name == "activities":
        current_user.preferred_activities = form.getlist("preferred_activities")


@onboarding_bp.route("/generating")
@login_required
def generating():
    return render_template("onboarding/generating.html")