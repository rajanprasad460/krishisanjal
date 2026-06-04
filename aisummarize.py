import os
import re
import json
import time
from pypdf import PdfReader
from PIL import Image
import pytesseract
from pdf2image import convert_from_path
from google import genai
from google.genai import types
from dotenv import load_dotenv



NOTICES_FILE = "notices.json"
TEXT_DIR = "texts"

MODEL_NAME = "gemini-2.5-flash"

os.makedirs(TEXT_DIR, exist_ok=True)

# client = genai.Client(
#     api_key=""
# )



load_dotenv()

client = genai.Client(
    api_key=os.getenv("GEMINI_API_KEY")
)

IMAGE_TYPES = ["jpg", "jpeg", "png", "webp"]
PDF_TYPES = ["pdf"]


def clean_text(text):
    text = text.replace("CamScanner", "")
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]+", " ", text)
    return text.strip()


def extract_pdf_text_with_pypdf(path):
    text = ""

    try:
        reader = PdfReader(path)

        for i, page in enumerate(reader.pages, start=1):
            page_text = page.extract_text() or ""
            text += f"\n\n--- Page {i} ---\n\n{page_text}"

    except Exception as e:
        print(f"PDF text extraction failed: {path}")
        print(e)

    return clean_text(text)


def extract_scanned_pdf_with_ocr(path):
    text = ""

    try:
        print("PDF appears scanned. Running OCR...")

        images = convert_from_path(
            path,
            dpi=300
        )

        for i, image in enumerate(images, start=1):
            page_text = pytesseract.image_to_string(
                image,
                lang="nep+eng"
            )

            text += f"\n\n--- OCR Page {i} ---\n\n{page_text}"

    except Exception as e:
        print(f"Scanned PDF OCR failed: {path}")
        print(e)

    return clean_text(text)


def extract_pdf_text(path):
    text = extract_pdf_text_with_pypdf(path)

    # If only CamScanner or very little text is found, OCR the PDF pages
    if len(text) < 100:
        text = extract_scanned_pdf_with_ocr(path)

    return clean_text(text)


def extract_image_text(path):
    text = ""

    try:
        image = Image.open(path)

        text = pytesseract.image_to_string(
            image,
            lang="nep+eng"
        )

    except Exception as e:
        print(f"Image OCR failed: {path}")
        print(e)

    return clean_text(text)


def text_filename(local_file):
    base = os.path.splitext(os.path.basename(local_file))[0]
    return f"{base}.txt"


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

Return ONLY valid JSON.

Use simple English.

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

Title:
{title}

Published date from website:
{published_date}

Deadline from website:
{deadline}

Notice text:
{text}
"""

    response = client.models.generate_content(
        model=MODEL_NAME,
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json"
        )
    )

    return json.loads(response.text)


with open(NOTICES_FILE, "r", encoding="utf-8") as f:
    notices = json.load(f)

processed = 0
skipped = 0
failed = 0

for index, notice in enumerate(notices, start=1):
    title = notice.get("title", "")

    if notice.get("ai_processed"):
        skipped += 1
        print(f"SKIP AI: {title}")
        continue

    local_path = notice.get("local_file_path")
    file_type = notice.get("file_type", "").lower()

    if not local_path or not os.path.exists(local_path):
        failed += 1
        print(f"MISSING FILE: {local_path}")
        continue

    try:
        txt_name = text_filename(local_path)
        txt_path = os.path.join(TEXT_DIR, txt_name)

        if os.path.exists(txt_path):
            with open(txt_path, "r", encoding="utf-8") as f:
                text = f.read()

            text = clean_text(text)
            print(f"READ TXT: {txt_name}")

            # Re-OCR bad old text files that only contain CamScanner or tiny text
            if len(text) < 100:
                print("Existing text is too short. Re-extracting...")

                if file_type in PDF_TYPES:
                    text = extract_pdf_text(local_path)
                elif file_type in IMAGE_TYPES:
                    text = extract_image_text(local_path)

                with open(txt_path, "w", encoding="utf-8") as f:
                    f.write(text)

        else:
            print(f"OCR/EXTRACT: {local_path}")

            if file_type in PDF_TYPES:
                text = extract_pdf_text(local_path)
            elif file_type in IMAGE_TYPES:
                text = extract_image_text(local_path)
            else:
                print(f"UNSUPPORTED FILE TYPE: {file_type}")
                failed += 1
                continue

            with open(txt_path, "w", encoding="utf-8") as f:
                f.write(text)

        notice["text_file"] = txt_name
        notice["text_file_path"] = txt_path

        if not text.strip():
            ai = fallback_summary(
                title,
                notice.get("deadline", "")
            )
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

        processed += 1
        print(f"DONE {index}: {title}")

    except Exception as e:
        failed += 1
        print(f"FAILED: {title}")
        print(e)

    with open(NOTICES_FILE, "w", encoding="utf-8") as f:
        json.dump(notices, f, ensure_ascii=False, indent=2)

print("\n------------------------")
print(f"Processed : {processed}")
print(f"Skipped   : {skipped}")
print(f"Failed    : {failed}")
print("------------------------")