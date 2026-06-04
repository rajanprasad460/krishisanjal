import os
import re
import json
from pypdf import PdfReader
from PIL import Image
import pytesseract

NOTICES_FILE = "notices.json"
TEXT_DIR = "texts"

os.makedirs(TEXT_DIR, exist_ok=True)

SUPPORTED_IMAGE_TYPES = ["jpg", "jpeg", "png", "webp"]
SUPPORTED_PDF_TYPES = ["pdf"]

def safe_text_filename(local_file):
    name = os.path.splitext(os.path.basename(local_file))[0]
    return f"{name}.txt"

def extract_text_from_pdf(file_path):
    text = ""

    try:
        reader = PdfReader(file_path)

        for i, page in enumerate(reader.pages, start=1):
            page_text = page.extract_text() or ""
            text += f"\n\n--- Page {i} ---\n\n{page_text}"

    except Exception as e:
        print(f"PDF extraction failed: {file_path} | {e}")

    return text.strip()

def extract_text_from_image(file_path):
    try:
        image = Image.open(file_path)

        # Nepali + English OCR
        text = pytesseract.image_to_string(
            image,
            lang="nep+eng"
        )

        return text.strip()

    except Exception as e:
        print(f"Image OCR failed: {file_path} | {e}")
        return ""

def clean_text(text):
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]+", " ", text)
    return text.strip()

def simple_summary(title, deadline, text):
    if not text:
        return {
            "summary": f"This notice is about {title}.",
            "eligibility": [],
            "required_documents": [],
            "benefits": [],
            "important_dates": [deadline] if deadline else [],
            "details": "Text could not be extracted clearly from the notice file."
        }

    short_text = text[:1200]

    return {
        "summary": f"This notice is about {title}. Deadline/status: {deadline or 'Not mentioned'}.",
        "eligibility": find_lines(text, ["योग्यता", "कृषक", "समूह", "सहकारी", "फर्म"]),
        "required_documents": find_lines(text, ["कागजात", "नागरिकता", "दर्ता", "प्रमाणपत्र", "PAN", "VAT"]),
        "benefits": find_lines(text, ["अनुदान", "सहयोग", "रकम", "प्रतिशत", "लागत"]),
        "important_dates": find_lines(text, ["मिति", "अन्तिम", "समय", "deadline"]) or ([deadline] if deadline else []),
        "details": short_text
    }

def find_lines(text, keywords):
    results = []

    for line in text.splitlines():
        line = line.strip()

        if not line:
            continue

        if any(keyword.lower() in line.lower() for keyword in keywords):
            results.append(line)

        if len(results) >= 8:
            break

    return results

with open(NOTICES_FILE, "r", encoding="utf-8") as f:
    notices = json.load(f)

processed = 0
skipped = 0
failed = 0

for notice in notices:
    local_path = notice.get("local_file_path")
    file_type = notice.get("file_type", "").lower()

    if not local_path or not os.path.exists(local_path):
        failed += 1
        print(f"MISSING FILE: {local_path}")
        continue

    txt_filename = safe_text_filename(local_path)
    txt_path = os.path.join(TEXT_DIR, txt_filename)

    if os.path.exists(txt_path):
        with open(txt_path, "r", encoding="utf-8") as f:
            text = f.read()
        skipped += 1
        print(f"READ EXISTING TXT: {txt_filename}")
    else:
        print(f"PROCESSING: {local_path}")

        if file_type in SUPPORTED_PDF_TYPES:
            text = extract_text_from_pdf(local_path)
        elif file_type in SUPPORTED_IMAGE_TYPES:
            text = extract_text_from_image(local_path)
        else:
            print(f"UNSUPPORTED FILE TYPE: {file_type}")
            failed += 1
            continue

        text = clean_text(text)

        with open(txt_path, "w", encoding="utf-8") as f:
            f.write(text)

        processed += 1

    summary_data = simple_summary(
        notice.get("title", ""),
        notice.get("deadline", ""),
        text
    )

    notice["text_file"] = txt_filename
    notice["text_file_path"] = f"{TEXT_DIR}/{txt_filename}"
    notice["summary"] = summary_data["summary"]
    notice["eligibility"] = summary_data["eligibility"]
    notice["required_documents"] = summary_data["required_documents"]
    notice["benefits"] = summary_data["benefits"]
    notice["important_dates"] = summary_data["important_dates"]
    notice["details"] = summary_data["details"]

with open(NOTICES_FILE, "w", encoding="utf-8") as f:
    json.dump(notices, f, ensure_ascii=False, indent=2)

print("\n------------------------")
print(f"Processed : {processed}")
print(f"Skipped   : {skipped}")
print(f"Failed    : {failed}")
print("------------------------")