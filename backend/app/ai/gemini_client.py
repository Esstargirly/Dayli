import json
from flask import current_app
from google import genai
from google.genai import types

_client = None


def get_client():
    """Lazily creates the Gemini client using the app's configured API key."""
    global _client
    if _client is None:
        _client = genai.Client(api_key=current_app.config["GEMINI_API_KEY"])
    return _client


MODEL_NAME = "gemini-3.6-flash" 

# ---- Schema for a generated day plan ----
PLAN_SCHEMA = {
    "type": "object",
    "properties": {
        "tasks": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "category": {
                        "type": "string",
                        "enum": ["sleep", "movement", "hydration", "mental_wellbeing"],
                    },
                    "scheduled_time": {"type": "string", "description": "24hr HH:MM"},
                    "duration_minutes": {"type": "integer"},
                },
                "required": ["title", "category", "scheduled_time", "duration_minutes"],
            },
        },
        "summary": {
            "type": "string",
            "description": "One warm, encouraging sentence introducing today's plan.",
        },
    },
    "required": ["tasks", "summary"],
}

# ---- Schema for an adjustment response ----
ADJUSTMENT_SCHEMA = {
    "type": "object",
    "properties": {
        "message": {
            "type": "string",
            "description": "Warm, conversational reply to the user explaining what changed.",
        },
        "updated_tasks": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "task_id": {"type": "integer"},
                    "new_scheduled_time": {"type": "string", "description": "24hr HH:MM"},
                    "new_duration_minutes": {"type": "integer"},
                    "new_status": {
                        "type": "string",
                        "enum": ["pending", "rescheduled", "skipped"],
                    },
                },
                "required": ["task_id"],
            },
        },
    },
    "required": ["message", "updated_tasks"],
}


def generate_daily_plan(user):
    """Calls Gemini to generate a fresh day plan based on the user's onboarding profile."""
    prompt = f"""
You are Dayli, a warm and encouraging wellness assistant. Create a realistic, personalized
day plan for this user. Do not overload their day — respect their available time and energy.

User profile:
- Goals: {user.goals}
- Current habits: {user.current_habits}
- Habits they want to build: {user.target_habits}
- Schedule: {user.schedule}
- What usually derails their consistency: {user.struggles}
- Preferred activities: {user.preferred_activities}
- Additional notes from the user: {user.extra_notes}

Generate a balanced set of tasks covering sleep, movement, hydration, and mental wellbeing
where relevant to their goals. Keep the tone warm and non-clinical in the summary.
"""
    client = get_client()
    response = client.models.generate_content(
        model=MODEL_NAME,
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=PLAN_SCHEMA,
        ),
    )
    return json.loads(response.text)


def adjust_plan(user, today_tasks, user_message, chat_history=None):
    """
    Calls Gemini with the current plan + a user-reported disruption
    (e.g. "I have a social event tonight") and gets back adjustments.
    """
    tasks_context = [
        {
            "task_id": t.id,
            "title": t.title,
            "category": t.category,
            "scheduled_time": t.scheduled_time.strftime("%H:%M") if t.scheduled_time else None,
            "duration_minutes": t.duration_minutes,
            "status": t.status,
        }
        for t in today_tasks
    ]

    history_text = ""
    if chat_history:
        history_text = "\n".join(f"{c.role}: {c.message}" for c in chat_history)

    prompt = f"""
You are Dayli, a warm wellness assistant. The user is reporting something that's changed
about their day. Adjust their existing plan around it — don't just cancel tasks, find a
realistic way to fit them in differently, or shorten/reschedule them. Never make the user
feel guilty about the disruption.

User profile struggles: {user.struggles}
Today's current tasks: {json.dumps(tasks_context)}

Recent conversation:
{history_text}

User just said: "{user_message}"

Respond with a short, warm message explaining the change, and the specific task updates.
Only include tasks that actually need to change in updated_tasks.
"""
    client = get_client()
    response = client.models.generate_content(
        model=MODEL_NAME,
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=ADJUSTMENT_SCHEMA,
        ),
    )
    return json.loads(response.text)