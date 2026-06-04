import subprocess
import sys

steps = [
    "scrapper.py",
    "downloader.py",
    "extract.py",
    "aisummarize.py",
]

for step in steps:
    print("\n" + "=" * 60)
    print(f"RUNNING: {step}")
    print("=" * 60)
    result = subprocess.run([sys.executable, step])
    if result.returncode != 0:
        raise SystemExit(f"Step failed: {step}")

print("\nAll steps completed.")
