WAF_SIGNATURES = {
    "Cloudflare": {
        "headers": {
            "cf-ray",
            "cf-cache-status",
            "cf-request-id",
        },
        "values": {
            "cloudflare",
        },
    },

    "Akamai": {
        "headers": {
            "x-akamai-transformed",
            "x-akamai-request-id",
            "akamai-grn",
        },
        "values": {
            "akamai",
        },
    },

    "AWS WAF": {
        "headers": {
            "x-amzn-waf-action",
        },
        "values": {
            "awselb",
            "aws",
        },
    },

    "Imperva": {
        "headers": {
            "x-iinfo",
            "x-cdn",
        },
        "values": {
            "incap_ses",
            "visid_incap",
            "imperva",
            "incapsula",
        },
    },

    "Sucuri": {
        "headers": {
            "x-sucuri-id",
            "x-sucuri-cache",
        },
        "values": {
            "sucuri",
        },
    },

    "Fastly": {
        "headers": {
            "x-served-by",
            "x-cache",
            "x-timer",
        },
        "values": {
            "fastly",
        },
    },

    "F5 BIG-IP": {
        "headers": {
            "x-wa-info",
        },
        "values": {
            "bigip",
            "f5",
        },
    },
}


def detect_waf(response):
    headers = {
        key.lower(): value.lower()
        for key, value in response.headers.items()
    }

    detected = []

    for waf, signatures in WAF_SIGNATURES.items():
        evidence = []

        for header in headers:
            if header in signatures["headers"]:
                evidence.append(f"header: {header}")

        for header, value in headers.items():
            for signature in signatures["values"]:
                if signature in value:
                    evidence.append(
                        f"value: {header}={value}"
                    )

        if evidence:
            detected.append({
                "name": waf,
                "evidence": sorted(set(evidence))
            })

    return detected