import json, mimetypes
from pathlib import Path
from google import genai
from google.genai import types
from core.storage import get_api_key
from core.config import MODEL_NAME

SYSTEM = """You are ATIQ AI AGENT, a careful personal coding assistant.
Return ONLY valid JSON with this shape:
{"reply":"short Bengali progress/result message","operations":[{"path":"relative/path.ext","content":"complete new file content","action":"write"}]}
You may only create or replace ordinary text source/config/document files inside the uploaded project.
Never request or create secrets, credentials, malware, spyware, destructive code, or code intended to harm systems.
Do not use absolute paths, '..', hidden paths, symlinks, or files outside the project.
For each changed file provide its COMPLETE final content, not a diff.
Do not change binary files. If the task is unclear, return no operations and ask a concise question in reply.
Keep changes focused. Do not claim tests/builds were run; this app does not execute uploaded code.
"""

def _client():
    key = get_api_key()
    if not key:
        raise RuntimeError("Gemini API key নেই। /setkey YOUR_KEY দিয়ে সেট করো।")
    return genai.Client(api_key=key)

def ask_text(prompt: str) -> str:
    response = _client().models.generate_content(
        model=MODEL_NAME,
        contents=SYSTEM + "\nUSER TASK:\n" + prompt,
        config=types.GenerateContentConfig(temperature=0.2),
    )
    return response.text or "দুঃখিত, কোনো উত্তর পাওয়া যায়নি।"

def inspect_image(prompt: str, image_bytes: bytes, mime_type: str) -> str:
    part = types.Part.from_bytes(data=image_bytes, mime_type=mime_type)
    response = _client().models.generate_content(
        model=MODEL_NAME,
        contents=[SYSTEM, "Analyze this screenshot/image and follow the user request. " + prompt, part],
        config=types.GenerateContentConfig(temperature=0.2),
    )
    return response.text or "ছবিটি বিশ্লেষণ করা যায়নি।"

def transcribe_audio(audio_bytes: bytes, mime_type: str) -> str:
    response = _client().models.generate_content(
        model=MODEL_NAME,
        contents=[
            "Transcribe this audio accurately. Return only the spoken words, preserving Bengali or English.",
            types.Part.from_bytes(data=audio_bytes, mime_type=mime_type),
        ],
    )
    return response.text or ""

def parse_agent_json(raw: str):
    text = raw.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1].rsplit("```", 1)[0]
    start, end = text.find("{"), text.rfind("}")
    if start < 0 or end < start:
        raise ValueError("AI returned no valid JSON object")
    data = json.loads(text[start:end+1])
    if not isinstance(data, dict) or not isinstance(data.get("operations", []), list):
        raise ValueError("Invalid agent response format")
    return data
