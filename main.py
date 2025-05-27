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
from openai import OpenAI
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

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
if not client.api_key:
    raise RuntimeError("Environment variable OPENAI_API_KEY must be set")


def generate_linkedin_about(what: str, audience: str, diff: str) -> str:
    # prompt = (
    #     f"You are a professional LinkedIn copywriter. Write exactly one concise “About” section in first person "
    #     f"(3–5 short paragraphs, no more than 200 tokens total, no less than 100 tokens), ready to copy-and-paste directly "
    #     f"into LinkedIn. Use an engaging hook, then introduce the user (“I am…”), explain what they do and who benefits, "
    #     f"highlight their unique differentiator, and close with a friendly call-to-action.\n"
    #     f"Do not include multiple versions—only the “About” text itself.\n"
    #     f"Use ONLY these facts—no invented details:\n"
    #     f"- What I do: {what}\n"
    #     f"- Target audience: {audience}\n"
    #     f"- Differentiator: {diff}\n\n"
    #     "Be professional yet personable, vary phrasing and structure, avoid generic buzzwords, and stay 100% truthful."
    # )
    system_msg = (
        "You are a professional LinkedIn copywriter. "
        "Your job is to write a single, concise “About” section in first person."
        "Write one About section (3–5 short paragraphs, 100–200 tokens total) ready for LinkedIn."
        "Be professional yet personable, avoid buzzwords, and stay 100% truthful."
    )

    user_msg = (
        f"Open with an engaging hook; then introduce yourself (“I am…”), explain what you do and who benefits, "
        f"highlight your unique differentiator, and close with a friendly call-to-action. "
        f"Do not include multiple versions—only the final About text. "
        f"Use ONLY these facts (no invented details):\n"
        f"- What I do: {what}\n"
        f"- Target audience: {audience}\n"
        f"- Unique differentiator: {diff}\n"
    )

    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system",  "content": system_msg},
            {"role": "user",    "content": user_msg},
        ],
        max_tokens=200,
        temperature=0.7,
    )

    if not response.choices or not hasattr(response.choices[0], "message"):
        raise RuntimeError("OpenAI returned an unexpected response format")

    return response.choices[0].message.content.strip()


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/generate")
@limiter.limit("5/day")
async def generate(request: Request):
    try:
        body = await request.json()
        what = body.get("what", "").strip()
        audience = body.get("audience", "").strip()
        diff = body.get("diff", "").strip()
        if not all([what, audience, diff]):
            raise HTTPException(
                status_code=400,
                detail="Missing one of 'what', 'audience', or 'diff'"
            )

        about_text = generate_linkedin_about(what, audience, diff)
        return {"result": about_text}

    except Exception as e:
        # Catch everything else (including RuntimeError from the OpenAI call)
        raise HTTPException(status_code=500, detail=str(e))


# To run locally:
# uvicorn main:app --host 0.0.0.0 --port 8080
