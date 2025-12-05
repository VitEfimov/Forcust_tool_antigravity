import subprocess

with open("test_output.txt", "w") as f:
    subprocess.run(["pytest", "-v", "-s", "tests/e2e/test_ui.py"], stdout=f, stderr=f)
