import os
import requests
from flask import Flask, request, jsonify, render_template
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_cors import CORS

app = Flask(__name__, template_folder="templates")
CORS(app)  # allow AJAX from same Repl URL

# Rate limiter: max 5 requests per day per IP
limiter = Limiter(app=app,
                  key_func=get_remote_address,
                  default_limits=["5 per day"])

# Gemini REST endpoint & API key
API_KEY = os.environ["GEMINI_API_KEY"]
GEMINI_URL = ("https://generativelanguage.googleapis.com/v1beta/"
              "models/gemini-2.5-flash:generateContent")


def generate_linkedin_about(what, audience, diff):
    prompt = (
        f"You’re a creative LinkedIn copywriter. Write a concise, 3–5-paragraph “About” section (≤200 tokens) in first person, suitable for LinkedIn. Use an engaging hook, then introduce the user (“I am…”), explain what they do and who benefits, highlight their unique differentiator, and close with a friendly call-to-action.\n\n"
        f"Use ONLY these facts—no invented details:\n"
        f"- What I do: {what}\n"
        f"- Target audience: {audience}\n"
        f"- Differentiator: {diff}\n\n"
        "Be professional yet personable, vary phrasing and structure across runs, avoid generic buzzwords, and ensure each output feels fresh while staying 100% truthful."
    )

    payload = {
        "contents": [{
            "parts": [{
                "text": prompt
            }]
        }],
        "generationConfig": {
            "maxOutputTokens": 250
        }
    }
    resp = requests.post(f"{GEMINI_URL}?key={API_KEY}", json=payload)
    resp.raise_for_status()
    data = resp.json()
    return data["candidates"][0]["content"]["parts"][0]["text"].strip()


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/generate", methods=["POST"])
@limiter.limit("5 per day")
def generate():
    data = request.get_json()
    what = data.get("what")
    aud = data.get("audience")
    diff = data.get("diff")
    if not (what and aud and diff):
        return jsonify(
            {"error": "Missing one of 'what', 'audience', or 'diff'"}), 400

    try:
        about = generate_linkedin_about(what, aud, diff)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    return jsonify({"result": about})


# if __name__ == "__main__":
#     # Replit uses port 81 by default
#     app.run(host="0.0.0.0", port=81)
