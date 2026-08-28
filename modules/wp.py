import httpx

from .rpc import call, parse_response, parse_fault
from .output import colorize, RED, GREEN


FAKE_USERNAME = "rpcstrike_nonexistent_user_9f3a"
INVALID_PASSWORD = "rpcstrike_invalid_password"


def run(result):
    endpoint = result["endpoint"]

    print("\n[*] WordPress user enumeration")

    usernames = discover_users(endpoint)

    if usernames:
        print("[i] Users found via REST API:")

        for username in usernames:
            print(f"    {username}")

        test_enumeration(endpoint, usernames[0])
        return

    print("[i] REST API did not expose users")

    for username in ("admin", "administrator"):
        if test_enumeration(endpoint, username):
            return

    print(colorize("[-] No differential response detected", RED))


def discover_users(endpoint):
    base = endpoint.rsplit("/xmlrpc.php", 1)[0]
    url = f"{base}/wp-json/wp/v2/users"

    try:
        response = httpx.get(
            url,
            timeout=10,
            follow_redirects=True
        )
    except httpx.RequestError:
        return []

    if response.status_code != 200:
        return []

    try:
        data = response.json()
    except ValueError:
        return []

    if not isinstance(data, list):
        return []

    usernames = []

    for user in data:
        if not isinstance(user, dict):
            continue

        username = user.get("slug")

        if username:
            usernames.append(username)

    return usernames


def test_enumeration(endpoint, username):
    print(f"[*] Testing: {username} vs {FAKE_USERNAME}")

    try:
        known_response = call(
            endpoint,
            "wp.getUsers",
            [
                1,
                username,
                INVALID_PASSWORD
            ]
        )

        fake_response = call(
            endpoint,
            "wp.getUsers",
            [
                1,
                FAKE_USERNAME,
                INVALID_PASSWORD
            ]
        )
    except httpx.RequestError as exc:
        print(colorize(f"[-] Network error, unable to compare responses: {exc}", RED))
        return False

    known_result = parse_response(known_response)
    fake_result = parse_response(fake_response)

    if known_result is None or fake_result is None:
        print(colorize("[-] Unable to compare responses", RED))
        return False

    known_signature = get_fault_signature(known_result)
    fake_signature = get_fault_signature(fake_result)

    if known_signature != fake_signature:
        print(colorize("[+] Potential username enumeration", GREEN))
        return True

    print(colorize("[-] No differential response", RED))

    return False


def get_fault_signature(result):
    if result["type"] != "fault":
        return ("success",)

    fault = parse_fault(result["root"])

    return (
        str(fault.get("faultCode")),
        str(fault.get("faultString"))
    )