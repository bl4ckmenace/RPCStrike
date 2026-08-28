import sys


RED = "\033[31m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
RESET = "\033[0m"

COLOR_ENABLED = sys.stdout.isatty()


def colorize(text, color):
    if not COLOR_ENABLED:
        return text

    return f"{color}{text}{RESET}"


def banner():
    print("""

    ▄▄▄   ▄▄▄· ▄▄· .▄▄ · ▄▄▄▄▄▄▄▄  ▪  ▄ •▄ ▄▄▄ .
    ▀▄ █·▐█ ▄█▐█ ▌▪▐█ ▀. •██  ▀▄ █·██ █▌▄▌▪▀▄.▀·
    ▐▀▀▄  ██▀·██ ▄▄▄▀▀▀█▄ ▐█.▪▐▀▀▄ ▐█·▐▀▀▄·▐▀▀▪▄
    ▐█•█▌▐█▪·•▐███▌▐█▄▪▐█ ▐█▌·▐█•█▌▐█▌▐█.█▌▐█▄▄▌
    .▀  ▀.▀   ·▀▀▀  ▀▀▀▀  ▀▀▀ .▀  ▀▀▀▀·▀  ▀ ▀▀▀ 
    V0.1.0

   WordPress XML-RPC Security Scanner
   For research | Use with permission
   Made by bl4ckmenace
    """)


def print_target(url):
    print(f"\nTarget: {url}")


def print_status(status_code):
    if status_code is None:
        print(colorize("Status: [!] Connection failed", RED))

    elif status_code == 200:
        print(colorize("Status: [+] HTTP 200", GREEN))

    else:
        print(colorize(f"Status: [!] HTTP {status_code}", YELLOW))


def print_findings(findings):
    print("\nFindings:")

    for finding in findings:
        print(colorize(f"\n  [+] {finding['title']}", GREEN))

        print("      Potential:")
        for item in finding["potential"]:
            print(f"        - {item}")


def print_methods(categories, total):
    print("\nMethods:")
    print(f"  [+] {total} methods exposed")

    for category, methods in categories.items():
        if not methods:
            continue

        print(f"  ├── {category:<12} {len(methods)}")


def print_capabilities(capabilities):
    print("\nCapabilities:")

    for capability in capabilities:
        print(f"  [+] {capability}")

def print_waf(result):
    print("\nWAF:")

    wafs = result.get("waf", [])

    if not wafs:
        print("  [-] No known WAF detected")
        return

    for waf in wafs:
        print(colorize(f"  [+] {waf['name']}", YELLOW))

        for evidence in waf["evidence"]:
            print(f"      - {evidence}")

def print_verbose(categories):
    print("\n" + "─" * 50)
    print("Detailed Methods")
    print("─" * 50)

    for category, methods in categories.items():
        if not methods:
            continue

        print(f"\n[{category}]")

        for method in methods:
            print(f"  - {method}")