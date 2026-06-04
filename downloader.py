import os
import json
import hashlib
import requests
from urllib.parse import urlparse

NOTICES_FILE = "notices.json"
DOWNLOAD_DIR = "downloads"

os.makedirs(DOWNLOAD_DIR, exist_ok=True)

headers = {"User-Agent": "Mozilla/5.0"}

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


def get_notice_id(notice):
    source = notice.get("pdf_url", "") or (notice.get("title", "") + notice.get("published_date", ""))
    return "akc_" + hashlib.md5(source.encode("utf-8")).hexdigest()[:8]


def get_extension_from_url(url):
    path = urlparse(url).path
    ext = os.path.splitext(path)[1].lower()
    allowed = [".pdf", ".jpg", ".jpeg", ".png", ".webp", ".doc", ".docx", ".xls", ".xlsx"]
    if ext in allowed:
        return ".jpg" if ext == ".jpeg" else ext
    return ""


def get_extension_from_response(response):
    content_type = response.headers.get("Content-Type", "").split(";")[0].lower().strip()
    return MIME_EXTENSIONS.get(content_type, "")


def expected_existing_path(notice):
    local_file = notice.get("local_file") or notice.get("local_pdf")
    if not local_file:
        return None
    return os.path.join(DOWNLOAD_DIR, local_file)


with open(NOTICES_FILE, "r", encoding="utf-8") as f:
    notices = json.load(f)

downloaded = 0
skipped = 0
failed = 0
updated_json = False

for notice in notices:
    notice_id = notice.get("notice_id") or get_notice_id(notice)
    notice["notice_id"] = notice_id

    file_url = notice.get("pdf_url")
    if not file_url:
        continue

    # Important: do not hit the network for old notices already downloaded.
    old_path = expected_existing_path(notice)
    if notice.get("downloaded") and old_path and os.path.exists(old_path):
        skipped += 1
        print(f"SKIP EXISTING: {notice.get('local_file')}")
        continue

    # If the JSON already has a local file and it exists, mark downloaded and skip.
    if old_path and os.path.exists(old_path):
        notice["downloaded"] = True
        notice["local_file_path"] = old_path.replace("\\", "/")
        skipped += 1
        updated_json = True
        print(f"SKIP EXISTING: {notice.get('local_file')}")
        continue

    try:
        print(f"DOWNLOAD CHECK: {file_url}")
        response = requests.get(file_url, headers=headers, timeout=60, stream=True)
        response.raise_for_status()

        extension = get_extension_from_response(response) or get_extension_from_url(file_url) or ".bin"
        filename = f"{notice_id}{extension}"
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
        notice["local_file_path"] = filepath.replace("\\", "/")
        notice["file_type"] = extension.replace(".", "")
        notice["downloaded"] = True

        if "local_pdf" in notice:
            del notice["local_pdf"]
        if "local_pdf_path" in notice:
            del notice["local_pdf_path"]

        updated_json = True

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
