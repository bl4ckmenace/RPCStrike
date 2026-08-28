def check_methods(methods):
    findings = []

    if "system.multicall" in methods:
        findings.append({
            "title": "system.multicall exposed",
            "potential": [
                "Authentication rate-limit bypass",
                "Brute-force amplification"
            ]
        })

    if "pingback.ping" in methods:
        findings.append({
            "title": "pingback.ping exposed",
            "potential": [
                "SSRF",
                "XML-RPC abuse"
            ]
        })

    if any(method.startswith("wp.") for method in methods):
        findings.append({
            "title": "WordPress XML-RPC enabled",
            "potential": [
                "User enumeration",
                "Remote publishing abuse"
            ]
        })

    return findings