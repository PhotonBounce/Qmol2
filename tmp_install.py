import subprocess
import sys

python = r"D:\qmol\.venv\Scripts\python.exe"

# Install aiosqlite
print("Installing aiosqlite...")
result = subprocess.run(
    [python, "-m", "pip", "install", "aiosqlite"],
    capture_output=True,
    text=True,
    timeout=120
)
print(f"RC: {result.returncode}")
print(f"STDOUT: {result.stdout[-500:]}")
print(f"STDERR: {result.stderr[-500:]}")

# Verify
print("\nVerifying...")
verify = subprocess.run(
    [python, "-c", "import aiosqlite; print('aiosqlite OK')"],
    capture_output=True,
    text=True,
    timeout=10
)
print(f"Verify: {verify.stdout.strip() or verify.stderr.strip()}")
