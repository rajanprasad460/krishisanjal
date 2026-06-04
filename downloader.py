import os
import json
import hashlib
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


def get_notice_id(notice):
    source = (
        notice.get("pdf_url", "")
        or notice.get("title", "") + notice.get("published_date", "")
    )

    notice_hash = hashlib.md5(
        source.encode("utf-8")
    ).hexdigest()[:8]

    return f"akc_{notice_hash}"


def get_extension_from_url(url):
    path = urlparse(url).path
    ext = os.path.splitext(path)[1].lower()

    allowed = [
        ".pdf", ".jpg", ".jpeg", ".png", ".webp",
        ".doc", ".docx", ".xls", ".xlsx"
    ]

    if ext in allowed:
        return ".jpg" if ext == ".jpeg" else ext

    return ""


def get_extension_from_response(response):
    content_type = response.headers.get(
        "Content-Type",
        ""
    ).split(";")[0].lower().strip()

    return MIME_EXTENSIONS.get(content_type, "")


def make_hash_filename(notice, extension):
    notice_id = notice.get("notice_id") or get_notice_id(notice)
    notice["notice_id"] = notice_id

    return f"{notice_id}{extension}"


with open(NOTICES_FILE, "r", encoding="utf-8") as f:
    notices = json.load(f)

downloaded = 0
skipped = 0
failed = 0
renamed = 0
updated_json = False

for notice in notices:
    file_url = notice.get("pdf_url")

    if not file_url:
        continue

    try:
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

        filename = make_hash_filename(notice, extension)
        filepath = os.path.join(DOWNLOAD_DIR, filename)

        old_file = notice.get("local_file") or notice.get("local_pdf")
        old_path = None

        if old_file:
            old_path = os.path.join(DOWNLOAD_DIR, old_file)

        # If old long-name file exists, rename it instead of downloading again
        if old_path and os.path.exists(old_path) and old_file != filename:
            print(f"RENAME: {old_file} -> {filename}")

            if not os.path.exists(filepath):
                os.rename(old_path, filepath)

            renamed += 1

        elif os.path.exists(filepath):
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
print(f"Renamed    : {renamed}")
print(f"Skipped    : {skipped}")
print(f"Failed     : {failed}")
import json
import hashlib
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


def get_notice_id(notice):
    source = (
        notice.get("pdf_url", "")
        or notice.get("title", "") + notice.get("published_date", "")
    )

    notice_hash = hashlib.md5(
        source.encode("utf-8")
    ).hexdigest()[:8]

    return f"akc_{notice_hash}"


def get_extension_from_url(url):
    path = urlparse(url).path
    ext = os.path.splitext(path)[1].lower()

    allowed = [
        ".pdf", ".jpg", ".jpeg", ".png", ".webp",
        ".doc", ".docx", ".xls", ".xlsx"
    ]

    if ext in allowed:
        return ".jpg" if ext == ".jpeg" else ext

    return ""


def get_extension_from_response(response):
    content_type = response.headers.get(
        "Content-Type",
        ""
    ).split(";")[0].lower().strip()

    return MIME_EXTENSIONS.get(content_type, "")


def make_hash_filename(notice, extension):
    notice_id = notice.get("notice_id") or get_notice_id(notice)
    notice["notice_id"] = notice_id

    return f"{notice_id}{extension}"


with open(NOTICES_FILE, "r", encoding="utf-8") as f:
    notices = json.load(f)

downloaded = 0
skipped = 0
failed = 0
renamed = 0
updated_json = False

for notice in notices:
    file_url = notice.get("pdf_url")

    if not file_url:
        continue

    try:
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

        filename = make_hash_filename(notice, extension)
        filepath = os.path.join(DOWNLOAD_DIR, filename)

        old_file = notice.get("local_file") or notice.get("local_pdf")
        old_path = None

        if old_file:
            old_path = os.path.join(DOWNLOAD_DIR, old_file)

        # If old long-name file exists, rename it instead of downloading again
        if old_path and os.path.exists(old_path) and old_file != filename:
            print(f"RENAME: {old_file} -> {filename}")

            if not os.path.exists(filepath):
                os.rename(old_path, filepath)

            renamed += 1

        elif os.path.exists(filepath):
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
print(f"Renamed    : {renamed}")
print(f"Skipped    : {skipped}")
print(f"Failed     : {failed}")
print("------------------------")