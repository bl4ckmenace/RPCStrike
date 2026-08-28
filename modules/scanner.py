import httpx
from urllib.parse import urlunparse
from .detect import check_methods
from .rpc import (
    call,
    parse_response,
    parse_methods,
    parse_capabilities,
    parse_fault
)
from .waf import detect_waf


def categorize_methods(methods):
    categories = {
        "System": [],
        "WordPress": [],
        "Pingback": [],
        "MetaWeblog": [],
        "Blogger": [],
        "MovableType": [],
        "Other": []
    }

    for method in methods:
        if method.startswith("system."):
            categories["System"].append(method)

        elif method.startswith("wp."):
            categories["WordPress"].append(method)

        elif method.startswith("pingback."):
            categories["Pingback"].append(method)

        elif method.startswith("metaWeblog."):
            categories["MetaWeblog"].append(method)

        elif method.startswith("blogger."):
            categories["Blogger"].append(method)

        elif method.startswith("mt."):
            categories["MovableType"].append(method)

        else:
            categories["Other"].append(method)

    return categories


def scan(parsed, path):
    if path.endswith("xmlrpc.php"):
        endpoint = urlunparse((
            parsed.scheme,
            parsed.netloc,
            path,
            "",
            "",
            ""
        ))
    else:
        endpoint = urlunparse((
            parsed.scheme,
            parsed.netloc,
            path + "xmlrpc.php",
            "",
            "",
            ""
        ))

    try:
        response = call(
            endpoint,
            "system.listMethods"
        )
    except httpx.RequestError as exc:
        return {
            "endpoint": endpoint,
            "status": None,
            "xmlrpc": False,
            "waf": [],
            "error": f"Connection failed: {exc}"
        }

    waf_results = detect_waf(response)

    result = parse_response(response)


    if result is None:
        return {
            "endpoint": endpoint,
            "status": response.status_code,
            "xmlrpc": False,
            "waf": waf_results,
            "error": "Response is not XML-RPC"
        }


    if result["type"] == "fault":
        fault = parse_fault(result["root"])

        return {
            "endpoint": endpoint,
            "status": response.status_code,
            "xmlrpc": True,
            "waf": waf_results,
            "fault": fault
        }

    root = result["root"]


    methods = parse_methods(root)

    categories = categorize_methods(methods)


    findings = check_methods(methods)


    capabilities = []

    try:
        capability_response = call(
            endpoint,
            "system.getCapabilities"
        )

        capability_result = parse_response(
            capability_response
        )

        if (
            capability_result is not None
            and capability_result["type"] == "success"
        ):
            capabilities = parse_capabilities(
                capability_result["root"]
            )
    except httpx.RequestError:
        pass

    return {
        "endpoint": endpoint,
        "status": response.status_code,
        "xmlrpc": True,
        "methods": methods,
        "categories": categories,
        "findings": findings,
        "capabilities": capabilities,
        "waf": waf_results
    }