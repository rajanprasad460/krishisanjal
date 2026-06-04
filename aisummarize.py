import os
import json
import time
from dotenv import load_dotenv
from google import genai
from google.genai import types

NOTICES_FILE = "notices.json"
MODEL_NAME = "gemini-2.5-flash"

load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    raise RuntimeError("GEMINI_API_KEY is missing. Add it to .env locally or GitHub Actions Secrets.")

client = genai.Client(api_key=api_key)


def fallback_summary(title, deadline):
    return {
        "summary": f"This notice is about {title}.",
        "eligibility": [],
        "required_documents": [],
        "benefits": [],
        "application_process": [],
        "deadline": deadline or "",
        "contact_information": [],
        "important_points": [],
        "plain_explanation": "Text could not be extracted clearly from this notice file."
    }


def summarize_with_gemini(title, published_date, deadline, text):
    text = text[:50000]
    prompt = f"""
You are analyzing a Nepal government agriculture notice.
Return ONLY valid JSON. Use simple English.
If the notice is in Nepali, understand it and summarize it in English.

Return this exact JSON structure:
{{
  "summary": "",
  "eligibility": [],
  "required_documents": [],
  "benefits": [],
  "application_process": [],
  "deadline": "",
  "contact_information": [],
  "important_points": [],
  "plain_explanation": ""
}}

Rules:
- Do not invent information.
- If something is not mentioned, use an empty list or empty string.
- Keep summary short and clear.
- In plain_explanation, explain what the notice means for farmers/applicants.
- Use the deadline from the notice text if available.
- If the notice text deadline is unclear, use the website deadline.

Title: {title}
Published date from website: {published_date}
Deadline from website: {deadline}
Notice text:
{text}
"""
    response = client.models.generate_content(
        model=MODEL_NAME,
        contents=prompt,
        config=types.GenerateContentConfig(response_mime_type="application/json")
    )
    return json.loads(response.text)


with open(NOTICES_FILE, "r", encoding="utf-8") as f:
    notices = json.load(f)

processed = 0
skipped = 0
failed = 0
updated_json = False

for index, notice in enumerate(notices, start=1):
    title = notice.get("title", "")

    # New-notice-only behavior: skip all already summarized notices.
    if notice.get("ai_processed"):
        skipped += 1
        print(f"SKIP AI: {title}")
        continue

    txt_path = notice.get("text_file_path")
    if not txt_path or not os.path.exists(txt_path):
        failed += 1
        print(f"MISSING TEXT: {txt_path}")
        continue

    try:
        with open(txt_path, "r", encoding="utf-8") as f:
            text = f.read().strip()

        if not text:
            ai = fallback_summary(title, notice.get("deadline", ""))
        else:
            print(f"GEMINI SUMMARY: {title}")
            ai = summarize_with_gemini(
                title=title,
                published_date=notice.get("published_date", ""),
                deadline=notice.get("deadline", ""),
                text=text
            )
            time.sleep(1)

        notice["summary"] = ai.get("summary", "")
        notice["eligibility"] = ai.get("eligibility", [])
        notice["required_documents"] = ai.get("required_documents", [])
        notice["benefits"] = ai.get("benefits", [])
        notice["application_process"] = ai.get("application_process", [])
        notice["deadline_ai"] = ai.get("deadline", "")
        notice["contact_information"] = ai.get("contact_information", [])
        notice["important_points"] = ai.get("important_points", [])
        notice["plain_explanation"] = ai.get("plain_explanation", "")
        notice["ai_processed"] = True
        notice["is_new"] = False

        processed += 1
        updated_json = True
        print(f"DONE {index}: {title}")

    except Exception as e:
        failed += 1
        print(f"FAILED AI: {title}")
        print(e)

    # Save after every item so progress is not lost.
    if updated_json:
        with open(NOTICES_FILE, "w", encoding="utf-8") as f:
            json.dump(notices, f, ensure_ascii=False, indent=2)

print("\n------------------------")
print(f"AI processed : {processed}")
print(f"Skipped      : {skipped}")
print(f"Failed       : {failed}")
print("------------------------")
