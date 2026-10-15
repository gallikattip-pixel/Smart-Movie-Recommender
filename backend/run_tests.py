import subprocess
import os

os.chdir(r'C:\Users\galli\OneDrive\Desktop\Movie Recommendation\backend')
result = subprocess.run(
    [r'C:\Users\galli\AppData\Local\Temp\opencode\.venv\Scripts\python.exe', '-m', 'pytest', 'tests/test_recommend.py', 'tests/test_search.py', 'tests/test_details.py', '-v', '--tb=short'],
    capture_output=True, text=True, timeout=180
)
print('Return code:', result.returncode)
if result.stdout:
    print('STDOUT:')
    print(result.stdout[-3000:])
if result.stderr:
    print('STDERR:')
    print(result.stderr[-2000:])