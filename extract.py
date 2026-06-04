import os
import re
import json
import hashlib
from pypdf import PdfReader
from PIL import Image, ImageFilter, ImageOps
import pytesseract
from pdf2image import convert_from_path

# Windows local path. Safe to keep; GitHub Actions will use PATH.
if os.name == "nt":
    pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOCAL_POPPLER = os.path.join(BASE_DIR, "poppler", "Library", "bin")
POPPLER_PATH = LOCAL_POPPLER if os.path.exists(LOCAL_POPPLER) else None

NOTICES_FILE = "notices.json"
TEXT_DIR = "texts"
os.makedirs(TEXT_DIR, exist_ok=True)

IMAGE_TYPES = ["jpg", "jpeg", "png", "webp"]
PDF_TYPES = ["pdf"]


def get_notice_id(notice):
    source = notice.get("pdf_url", "") or (notice.get("title", "") + notice.get("published_date", ""))
    return "akc_" + hashlib.md5(source.encode("utf-8")).hexdigest()[:8]


def clean_text(text):
    text = text.replace("CamScanner", "")
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]+", " ", text)
    return text.strip()


def is_bad_text(text):
    cleaned = clean_text(text)
    if len(cleaned) < 150:
        return True
    nepali_chars = len(re.findall(r"[\u0900-\u097F]", cleaned))
    english_chars = len(re.findall(r"[A-Za-z]", cleaned))
    return (nepali_chars + english_chars) < 80


def preprocess_image(image):
    image = image.convert("L")
    image = ImageOps.autocontrast(image)
    image = image.filter(ImageFilter.SHARPEN)
    width, height = image.size
    if width < 2000:
        image = image.resize((width * 2, height * 2))
    return image


def ocr_image_object(image):
    image = preprocess_image(image)
    return pytesseract.image_to_string(
        image,
        lang="nep+eng",
        config="--oem 3 --psm 4 -c preserve_interword_spaces=1"
    ).strip()


def extract_text_from_image(file_path):
    try:
        return clean_text(ocr_image_object(Image.open(file_path)))
    except Exception as e:
        print(f"Image OCR failed: {file_path} | {e}")
        return ""


def extract_pdf_with_pypdf(file_path):
    text = ""
    try:
        reader = PdfReader(file_path)
        for i, page in enumerate(reader.pages, start=1):
            page_text = page.extract_text() or ""
            text += f"\n\n--- Page {i} ---\n\n{page_text}"
    except Exception as e:
        print(f"PDF extraction failed: {file_path} | {e}")
    return clean_text(text)


def extract_scanned_pdf(file_path):
    text = ""
    try:
        print("Running OCR on scanned PDF...")
        kwargs = {"dpi": 500}
        if POPPLER_PATH:
            kwargs["poppler_path"] = POPPLER_PATH
        images = convert_from_path(file_path, **kwargs)
        for i, image in enumerate(images, start=1):
            page_text = ocr_image_object(image)
            text += f"\n\n--- OCR Page {i} ---\n\n{page_text}"
    except Exception as e:
        print(f"Scanned PDF OCR failed: {file_path} | {e}")
    return clean_text(text)


def extract_text_from_pdf(file_path):
    text = extract_pdf_with_pypdf(file_path)
    if is_bad_text(text):
        text = extract_scanned_pdf(file_path)
    return clean_text(text)


with open(NOTICES_FILE, "r", encoding="utf-8") as f:
    notices = json.load(f)

processed = 0
skipped = 0
failed = 0
updated_json = False

for notice in notices:
    notice_id = notice.get("notice_id") or get_notice_id(notice)
    notice["notice_id"] = notice_id

    local_path = notice.get("local_file_path")
    file_type = notice.get("file_type", "").lower()

    if not local_path or not os.path.exists(local_path):
        # Only warn for notices that were supposed to be downloaded.
        if notice.get("downloaded"):
            failed += 1
            print(f"MISSING FILE: {local_path}")
        continue

    txt_filename = f"{notice_id}.txt"
    txt_path = os.path.join(TEXT_DIR, txt_filename)

    # New-notice-only behavior: if extracted and txt exists, skip.
    if notice.get("extracted") and os.path.exists(txt_path):
        skipped += 1
        print(f"SKIP EXTRACTED: {txt_filename}")
        continue

    if os.path.exists(txt_path):
        with open(txt_path, "r", encoding="utf-8") as f:
            text = clean_text(f.read())
        if not is_bad_text(text):
            notice["text_file"] = txt_filename
            notice["text_file_path"] = txt_path.replace("\\", "/")
            notice["extracted"] = True
            skipped += 1
            updated_json = True
            print(f"SKIP EXISTING TXT: {txt_filename}")
            continue

    print(f"EXTRACT: {local_path} -> {txt_filename}")
    try:
        if file_type in PDF_TYPES:
            text = extract_text_from_pdf(local_path)
        elif file_type in IMAGE_TYPES:
            text = extract_text_from_image(local_path)
        else:
            print(f"UNSUPPORTED FILE TYPE: {file_type}")
            failed += 1
            continue

        with open(txt_path, "w", encoding="utf-8") as f:
            f.write(text)

        notice["text_file"] = txt_filename
        notice["text_file_path"] = txt_path.replace("\\", "/")
        notice["extracted"] = True
        processed += 1
        updated_json = True
    except Exception as e:
        failed += 1
        print(f"FAILED EXTRACT: {local_path}")
        print(e)

if updated_json:
    with open(NOTICES_FILE, "w", encoding="utf-8") as f:
        json.dump(notices, f, ensure_ascii=False, indent=2)

print("\n------------------------")
print(f"Extracted : {processed}")
print(f"Skipped   : {skipped}")
print(f"Failed    : {failed}")
print("------------------------")
