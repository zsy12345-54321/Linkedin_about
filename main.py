# main.py
import os
import requests
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address

# Initialize FastAPI app
app = FastAPI()


# Enable CORS for all origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Jinja2 templates directory
templates = Jinja2Templates(directory="templates")

# Rate limiter: in-memory store (per-instance)
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_middleware(SlowAPIMiddleware)

# Gemini REST endpoint & API key
API_KEY = os.environ["GEMINI_API_KEY"]
GEMINI_URL = (
    "https://generativelanguage.googleapis.com/v1beta/"
    "models/gemini-2.0-flash:generateContent"
)


def generate_linkedin_about(what: str, audience: str, diff: str) -> str:
    prompt = (
        f"You are a professional LinkedIn copywriter. Write exactly one concise “About” section in first person "
        f"(3–5 short paragraphs, no more than 200 tokens total, no less than 100 tokens), ready to copy-and-paste directly "
        f"into LinkedIn. Use an engaging hook, then introduce the user (“I am…”), explain what they do and who benefits, "
        f"highlight their unique differentiator, and close with a friendly call-to-action.\n"
        f"Do not include multiple versions—only the “About” text itself.\n"
        f"Use ONLY these facts—no invented details:\n"
        f"- What I do: {what}\n"
        f"- Target audience: {audience}\n"
        f"- Differentiator: {diff}\n\n"
        "Be professional yet personable, vary phrasing and structure, avoid generic buzzwords, and stay 100% truthful."
    )

    payload = {
        "contents": [{
            "parts": [{"text": prompt}]
        }],
        "generationConfig": {"maxOutputTokens": 250}
    }
    resp = requests.post(f"{GEMINI_URL}?key={API_KEY}", json=payload)
    resp.raise_for_status()
    data = resp.json()
    return data["candidates"][0]["content"]["parts"][0]["text"].strip()


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.post("/generate")
@limiter.limit("10/day")
async def generate(request: Request):
    body = await request.json()
    what = body.get("what")
    audience = body.get("audience")
    diff = body.get("diff")
    if not all([what, audience, diff]):
        raise HTTPException(
            status_code=400,
            detail="Missing one of 'what', 'audience', or 'diff'"
        )
    try:
        about = generate_linkedin_about(what, audience, diff)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    return {"result": about}


# To run locally:
# uvicorn main:app --host 0.0.0.0 --port 8080
