import subprocess
import sys

try:
    result = subprocess.run([sys.executable, "check_schema.py"], capture_output=True, text=True)
    print(result.stdout)
    print(result.stderr)
except Exception as e:
    print(e)