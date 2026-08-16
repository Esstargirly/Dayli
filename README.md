# Dayli 🌱

A wellness plan that adapts to your life, instead of asking you to adapt your life to it.

## What is Dayli?

Dayli is an AI wellness app. Most apps give you the same fixed routine every day and expect you to follow it no matter what happens in your life. Dayli does the opposite. It builds your day around your own goals, then if something changes, you just tell it, and it changes your plan for you.

## How it works

1. You sign up and answer a few questions about your goals, your habits, your schedule, and what usually makes you fall off track.
2. Dayli uses that to build your day.
3. If something comes up, like you have an event tonight or you woke up late, you tell Dayli and it adjusts your tasks.
4. You complete tasks and earn XP. You also build streaks and unlock badges.
5. You can edit your profile any time, and Dayli will update your plan to match.

## What we used to build it

- **Backend:** Python and Flask
- **Database:** PostgreSQL, hosted on Neon
- **AI:** Google Gemini (we used the Gemini Student Pro plan)
- **Design:** Google Stitch for the screens, built with Tailwind CSS
- **Hosting:** Render
- **Uptime:** UptimeRobot, so the server doesn't sleep

## Project folders

dayli/
├── backend/
│   ├── app/
│   │   ├── auth/          # sign up, log in, log out
│   │   ├── onboarding/     # the questions when you first join
│   │   ├── dashboard/      # home page, tasks, XP, profile
│   │   ├── ai/             # talks to Gemini
│   │   ├── models.py       # database tables
│   │   └── xp_rules.py     # how XP and levels work
│   ├── migrations/
│   ├── requirements.txt
│   └── run.py
└── frontend/
    └── templates/          # all the app screens


## What you need in your .env file

| Name | What it is |
|---|---|
| `FLASK_SECRET_KEY` | A random secret key |
| `DATABASE_URL` | Your Neon database link |
| `GEMINI_API_KEY` | Your Gemini API key |

## Who made this

Built by Team Dayli for CS Girlies Hackathon 2026 
([@Esstargirly](https://github.com/Esstargirly))