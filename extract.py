import os
import re
import json
import hashlib
from pypdf import PdfReader
from PIL import Image, ImageFilter, ImageOps
import pytesseract
from pdf2image import convert_from_path

# Tesseract path
pytesseract.pytesseract.tesseract_cmd = (
    r"C:\Program Files\Tesseract-OCR\tesseract.exe"
)

# If Poppler is not in PATH, set this.
# Example:
# POPPLER_PATH = r"C:\poppler\Library\bin"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

POPPLER_PATH = os.path.join(
    BASE_DIR,
    "poppler",
    "Library",
    "bin"
)

NOTICES_FILE = "notices.json"
TEXT_DIR = "texts"

os.makedirs(TEXT_DIR, exist_ok=True)

SUPPORTED_IMAGE_TYPES = ["jpg", "jpeg", "png", "webp"]
SUPPORTED_PDF_TYPES = ["pdf"]


def get_notice_id(notice):
    source = (
        notice.get("pdf_url", "")
        or notice.get("title", "") + notice.get("published_date", "")
    )

    notice_hash = hashlib.md5(
        source.encode("utf-8")
    ).hexdigest()[:8]

    return f"akc_{notice_hash}"


def preprocess_image(image):
    image = image.convert("L")
    image = ImageOps.autocontrast(image)
    image = image.filter(ImageFilter.SHARPEN)

    width, height = image.size

    if width < 2000:
        image = image.resize(
            (width * 2, height * 2)
        )

    return image


def ocr_image_object(image):
    image = preprocess_image(image)

    text = pytesseract.image_to_string(
        image,
        lang="nep+eng",
        config="--oem 3 --psm 6"
    )

    return text.strip()


def extract_text_from_image(file_path):
    try:
        image = Image.open(file_path)
        return ocr_image_object(image)

    except Exception as e:
        print(f"Image OCR failed: {file_path} | {e}")
        return ""


def extract_text_from_pdf_with_pypdf(file_path):
    text = ""

    try:
        reader = PdfReader(file_path)

        for i, page in enumerate(reader.pages, start=1):
            page_text = page.extract_text() or ""
            text += f"\n\n--- Page {i} ---\n\n{page_text}"

    except Exception as e:
        print(f"PDF extraction failed: {file_path} | {e}")

    return clean_text(text)


def extract_text_from_scanned_pdf(file_path):
    text = ""

    try:
        print("Running OCR on scanned PDF...")

        if POPPLER_PATH:
            images = convert_from_path(
                file_path,
                dpi=400,
                poppler_path=POPPLER_PATH
            )
        else:
            images = convert_from_path(
                file_path,
                dpi=400
            )

        for i, image in enumerate(images, start=1):
            page_text = ocr_image_object(image)
            text += f"\n\n--- OCR Page {i} ---\n\n{page_text}"

    except Exception as e:
        print(f"Scanned PDF OCR failed: {file_path} | {e}")

    return clean_text(text)


def extract_text_from_pdf(file_path):
    text = extract_text_from_pdf_with_pypdf(file_path)

    # If pypdf gives only CamScanner or very little useful text, OCR the PDF
    if is_bad_text(text):
        text = extract_text_from_scanned_pdf(file_path)

    return clean_text(text)


def clean_text(text):
    text = text.replace("CamScanner", "")
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]+", " ", text)
    return text.strip()


def is_bad_text(text):
    cleaned = clean_text(text)

    if len(cleaned) < 150:
        return True

    # Detect mostly garbage OCR / extraction
    nepali_chars = len(re.findall(r"[\u0900-\u097F]", cleaned))
    english_chars = len(re.findall(r"[A-Za-z]", cleaned))
    total_letters = nepali_chars + english_chars

    if total_letters < 80:
        return True

    return False


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

    return {
        "summary": f"This notice is about {title}. Deadline/status: {deadline or 'Not mentioned'}.",
        "eligibility": find_lines(text, ["योग्यता", "कृषक", "समूह", "सहकारी", "फर्म"]),
        "required_documents": find_lines(text, ["कागजात", "नागरिकता", "दर्ता", "प्रमाणपत्र", "PAN", "VAT"]),
        "benefits": find_lines(text, ["अनुदान", "सहयोग", "रकम", "प्रतिशत", "लागत"]),
        "important_dates": find_lines(text, ["मिति", "अन्तिम", "समय", "deadline"]) or ([deadline] if deadline else []),
        "details": text[:1200]
    }


with open(NOTICES_FILE, "r", encoding="utf-8") as f:
    notices = json.load(f)

processed = 0
skipped = 0
reprocessed = 0
failed = 0

for notice in notices:
    notice_id = notice.get("notice_id") or get_notice_id(notice)
    notice["notice_id"] = notice_id

    local_path = notice.get("local_file_path")
    file_type = notice.get("file_type", "").lower()

    if not local_path or not os.path.exists(local_path):
        failed += 1
        print(f"MISSING FILE: {local_path}")
        continue

    txt_filename = f"{notice_id}.txt"
    txt_path = os.path.join(TEXT_DIR, txt_filename)

    if os.path.exists(txt_path):
        with open(txt_path, "r", encoding="utf-8") as f:
            text = f.read()

        text = clean_text(text)

        if is_bad_text(text):
            print(f"BAD TXT FOUND, REPROCESSING: {txt_filename}")

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

            reprocessed += 1

        else:
            skipped += 1
            print(f"READ EXISTING TXT: {txt_filename}")

    else:
        print(f"PROCESSING: {local_path} -> {txt_filename}")

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
print(f"Processed   : {processed}")
print(f"Skipped     : {skipped}")
print(f"Reprocessed : {reprocessed}")
print(f"Failed      : {failed}")
print("------------------------")