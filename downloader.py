import os
import re
import json
import requests
from urllib.parse import urlparse

NOTICES_FILE = "notices.json"
DOWNLOAD_DIR = "downloads"

os.makedirs(DOWNLOAD_DIR, exist_ok=True)

headers = {
    "User-Agent": "Mozilla/5.0"
}

MIME_EXTENSIONS = {
    "application/pdf": ".pdf",
    "image/jpeg": ".jpg",
    "image/jpg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "application/msword": ".doc",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
    "application/vnd.ms-excel": ".xls",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": ".xlsx",
}

def clean_title(title):
    name = "".join(c if c.isalnum() else "_" for c in title)
    name = re.sub(r"_+", "_", name)
    name = name.strip("_")
    name = name[:120]
    return name or "notice"

def get_extension_from_url(url):
    path = urlparse(url).path
    ext = os.path.splitext(path)[1].lower()

    if ext in [".pdf", ".jpg", ".jpeg", ".png", ".webp", ".doc", ".docx", ".xls", ".xlsx"]:
        return ".jpg" if ext == ".jpeg" else ext

    return ""

def get_extension_from_response(response):
    content_type = response.headers.get("Content-Type", "").split(";")[0].lower().strip()
    return MIME_EXTENSIONS.get(content_type, "")

def make_unique_filename(title, extension, used_names):
    base = clean_title(title)
    filename = f"{base}{extension}"

    counter = 1
    while filename in used_names:
        filename = f"{base}_{counter}{extension}"
        counter += 1

    used_names.add(filename)
    return filename

with open(NOTICES_FILE, "r", encoding="utf-8") as f:
    notices = json.load(f)

used_names = set()

for notice in notices:
    existing_name = notice.get("local_file") or notice.get("local_pdf")
    if existing_name:
        used_names.add(existing_name)

downloaded = 0
skipped = 0
failed = 0
updated_json = False

for notice in notices:
    file_url = notice.get("pdf_url")

    if not file_url:
        continue

    try:
        existing_file = notice.get("local_file") or notice.get("local_pdf")

        if existing_file:
            filepath = os.path.join(DOWNLOAD_DIR, existing_file)

            if os.path.exists(filepath):
                skipped += 1
                print(f"SKIP: {existing_file}")
                continue

        print(f"CHECK: {file_url}")

        response = requests.get(
            file_url,
            headers=headers,
            timeout=60,
            stream=True
        )
        response.raise_for_status()

        extension = get_extension_from_response(response)

        if not extension:
            extension = get_extension_from_url(file_url)

        if not extension:
            extension = ".bin"

        if existing_file:
            old_ext = os.path.splitext(existing_file)[1].lower()
            if old_ext == extension:
                filename = existing_file
            else:
                filename = make_unique_filename(
                    notice.get("title", "notice"),
                    extension,
                    used_names
                )
        else:
            filename = make_unique_filename(
                notice.get("title", "notice"),
                extension,
                used_names
            )

        filepath = os.path.join(DOWNLOAD_DIR, filename)

        if os.path.exists(filepath):
            skipped += 1
            print(f"SKIP: {filename}")
        else:
            print(f"DOWNLOAD: {filename}")

            with open(filepath, "wb") as f:
                for chunk in response.iter_content(8192):
                    if chunk:
                        f.write(chunk)

            downloaded += 1

        notice["local_file"] = filename
        notice["local_file_path"] = f"{DOWNLOAD_DIR}/{filename}"
        notice["file_type"] = extension.replace(".", "")
        updated_json = True

        if "local_pdf" in notice:
            del notice["local_pdf"]

        if "local_pdf_path" in notice:
            del notice["local_pdf_path"]

    except Exception as e:
        failed += 1
        print(f"FAILED: {file_url}")
        print(e)

if updated_json:
    with open(NOTICES_FILE, "w", encoding="utf-8") as f:
        json.dump(notices, f, ensure_ascii=False, indent=2)

print("\n------------------------")
print(f"Downloaded : {downloaded}")
print(f"Skipped    : {skipped}")
print(f"Failed     : {failed}")
print("------------------------")