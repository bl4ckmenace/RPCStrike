from .wp import run as wp_run
from .login import run as login_run
from .multicall import run as multicall_run
from .pingback import run as pingback_run


def start_menu(result):
    methods = result.get("methods", [])

    options = {}

    if any(method.startswith("wp.") for method in methods):
        options["1"] = {
            "name": "WordPress user enumeration",
            "function": test_users
        }

    if "wp.getUsersBlogs" in methods or "blogger.getUsersBlogs" in methods:
        options["2"] = {
            "name": "WordPress login",
            "function": login_run
        }

    if "system.multicall" in methods and (
        "wp.getUsersBlogs" in methods
        or "blogger.getUsersBlogs" in methods
    ):
        options["3"] = {
            "name": "Brute-force amplification (multicall)",
            "function": multicall_run
        }

    if "pingback.ping" in methods:
        options["4"] = {
            "name": "Pingback test",
            "function": pingback_run
        }

    options["0"] = {
        "name": "Exit",
        "function": None
    }

    while True:
        print("\nTests:")

        for key, item in options.items():
            print(f"  [{key}] {item['name']}")

        choice = input("\nSelect: ").strip()

        if choice not in options:
            print("Invalid option")
            continue

        if choice == "0":
            break

        options[choice]["function"](result)


def test_users(result):
    wp_run(result)