import httpx
from getpass import getpass
from .rpc import call, parse_response, parse_fault, parse_struct_array
from .output import colorize, RED, GREEN, YELLOW


AUTH_METHODS = {
    "wp.getUsersBlogs": lambda username, password: [username, password],
    "blogger.getUsersBlogs": lambda username, password: ["", username, password],
}


def try_auth(endpoint, auth_method, username, password):
    param_builder = AUTH_METHODS[auth_method]

    try:
        response = call(
            endpoint,
            auth_method,
            param_builder(username, password)
        )
    except httpx.RequestError as exc:
        return {"success": False, "network_error": True, "error": str(exc)}

    parsed = parse_response(response)

    if parsed is None:
        return {
            "success": False,
            "status": response.status_code,
            "invalid": True
        }

    if parsed["type"] == "fault":
        return {
            "success": False,
            "status": response.status_code,
            "fault": parse_fault(parsed["root"])
        }

    return {
        "success": True,
        "status": response.status_code,
        "blogs": parse_struct_array(parsed["root"])
    }


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

    print("\n[*] WordPress authentication test")
    print(f"[*] Auth method: {auth_method}")

    username = input("Username: ").strip()
    password = getpass("Password: ")

    if not username or not password:
        print(colorize("[-] Username and password are required", RED))
        return

    outcome = try_auth(endpoint, auth_method, username, password)

    if (
        not outcome["success"]
        and outcome.get("status") == 403
        and auth_method == "wp.getUsersBlogs"
        and "blogger.getUsersBlogs" in methods
    ):
        print(colorize(
            "\n[!] wp.getUsersBlogs blocked (HTTP 403) - "
            "falling back to blogger.getUsersBlogs",
            YELLOW
        ))
        auth_method = "blogger.getUsersBlogs"
        outcome = try_auth(endpoint, auth_method, username, password)

    if outcome.get("network_error"):
        print(colorize(f"\n[-] Network error: {outcome.get('error')}", RED))
        return

    if outcome.get("invalid"):
        print(colorize("\n[-] Invalid XML-RPC response", RED))
        return

    if not outcome["success"]:
        fault = outcome.get("fault", {})

        message = (
            fault.get("faultString")
            or fault.get("message")
            or "Authentication failed"
        )

        print(colorize("\n[-] Authentication failed", RED))
        print(f"    {message}")
        return

    blogs = outcome["blogs"]

    if not blogs:
        print(colorize(
            "\n[!] No fault returned, but no blog data found either - "
            "response may be non-standard, verify manually",
            YELLOW
        ))
        return

    print(colorize(f"\n[+] Authentication successful ({auth_method})", GREEN))
    print(colorize(f"[+] Accessible blogs: {len(blogs)}", GREEN))

    for blog in blogs:
        name = blog.get("blogName", "unknown")
        url = blog.get("url", "unknown")
        is_admin = blog.get("isAdmin", "unknown")
        print(f"    - {name} ({url}) - isAdmin: {is_admin}")