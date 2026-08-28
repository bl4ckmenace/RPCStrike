#!/usr/bin/env python3

import argparse
from urllib.parse import urlparse
from modules.scanner import scan
from modules.menu import start_menu
from modules.output import (
    banner,
    print_target,
    print_status,
    print_findings,
    print_methods,
    print_capabilities,
    print_verbose,
    print_waf,
    colorize,
    RED,
    GREEN
)


def main():

    parser = argparse.ArgumentParser(
        description="WordPress XML-RPC security scanner"
    )

    parser.add_argument(
        "url",
        help="Target URL"
    )

    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Show detailed method list"
    )

    args = parser.parse_args()

    banner()

    url = args.url

    parsed = urlparse(url)

    if parsed.scheme not in ("http", "https"):
        print(colorize("Error: URL must include http:// or https://", RED))
        return

    path = parsed.path

    if not path:
        path = "/"
    elif not path.endswith("xmlrpc.php") and not path.endswith("/"):
        path += "/"

    result = scan(parsed, path)

    print_target(result["endpoint"])
    print_status(result["status"])

    print_waf(result)

    if not result.get("xmlrpc"):
        print(colorize("\n[-] XML-RPC not detected", RED))

        if "error" in result:
            print(f"    {result['error']}")

        return

    if "fault" in result:
        print(colorize("\n[-] XML-RPC fault", RED))
        print(f"    Code: {result['fault'].get('faultCode')}")
        print(f"    Message: {result['fault'].get('faultString')}")
        return

    print(colorize("\n[+] XML-RPC endpoint detected", GREEN))

    print_findings(result["findings"])

    print_methods(
        result["categories"],
        len(result["methods"])
    )

    print_capabilities(result["capabilities"])

    if args.verbose:
        print_verbose(result["categories"])

    start_menu(result)

if __name__ == "__main__":
    main()