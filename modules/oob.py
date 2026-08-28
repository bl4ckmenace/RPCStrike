import platform
import shutil
import subprocess
import threading
import queue
import re


PAYLOAD_RE = re.compile(
    r"([a-zA-Z0-9.-]+\.(?:oast\.pro|oast\.live|oast\.site|oast\.online|oast\.fun|oast\.me))"
)

INTERACTION_RE = re.compile(
    r"received.*(dns|http|https)",
    re.IGNORECASE
)

GO_INSTALL_COMMANDS = {
    "dnf": "sudo dnf install golang",
    "apt-get": "sudo apt-get install golang-go",
    "pacman": "sudo pacman -S go",
    "zypper": "sudo zypper install go",
    "apk": "sudo apk add go",
    "brew": "brew install go",
}


def available():
    return shutil.which("interactsh-client") is not None


def detect_package_manager():
    system = platform.system()

    if system == "Darwin":
        return "brew"

    if system == "Linux":
        for pm in ("dnf", "apt-get", "pacman", "zypper", "apk"):
            if shutil.which(pm):
                return pm

    return None


def print_install_instructions():
    system = platform.system()

    print("\nInstall interactsh-client:")

    if shutil.which("go") is None:
        pm = detect_package_manager()

        if pm:
            print(f"  {GO_INSTALL_COMMANDS[pm]}")
        elif system == "Windows":
            print("  Download Go from https://go.dev/dl/ and run the installer")
        else:
            print("  Install Go from https://go.dev/dl/")

    print("  go install -v github.com/projectdiscovery/interactsh/cmd/interactsh-client@latest")

    if system == "Windows":
        print(r'  setx PATH "%PATH%;%USERPROFILE%\go\bin"')
        print("  (restart your terminal after this)")
    else:
        print('  export PATH="$PATH:$(go env GOPATH)/bin"')


def _reader(process, output):
    for line in iter(process.stdout.readline, ""):
        output.put(line)

    process.stdout.close()


def start():
    if not available():
        return None, "interactsh-client not found"

    process = subprocess.Popen(
        [
            "interactsh-client",
            "-n", "1"
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1
    )

    output = queue.Queue()

    thread = threading.Thread(
        target=_reader,
        args=(process, output),
        daemon=True
    )

    thread.start()

    payload = None

    for _ in range(30):
        try:
            line = output.get(timeout=0.5)
        except queue.Empty:
            continue

        match = PAYLOAD_RE.search(line)

        if match:
            payload = match.group(1)
            break

    if payload is None:
        stop(process)
        return None, "Failed to obtain OOB payload"

    process._rpcstrike_queue = output

    return process, payload


def drain(process):
    output = getattr(process, "_rpcstrike_queue", None)

    if output is None:
        return

    while True:
        try:
            output.get_nowait()
        except queue.Empty:
            break


def wait_for_interaction(process, timeout=15):
    output = getattr(process, "_rpcstrike_queue", None)

    if output is None:
        return None

    for _ in range(timeout * 2):
        try:
            line = output.get(timeout=0.5)
        except queue.Empty:
            continue

        if INTERACTION_RE.search(line):
            return line.strip()

    return None


def stop(process):
    if process is None:
        return

    if process.poll() is None:
        process.terminate()

        try:
            process.wait(timeout=3)
        except subprocess.TimeoutExpired:
            process.kill()