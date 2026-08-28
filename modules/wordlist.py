from pathlib import Path


def load_wordlist(path):
    path = Path(path).expanduser()

    if not path.is_file():
        print(f"[-] Wordlist not found: {path}")
        return []

    try:
        with path.open(
            "r",
            encoding="utf-8",
            errors="ignore"
        ) as file:
            entries = []

            for line in file:
                value = line.strip()

                if value:
                    entries.append(value)

        return entries

    except OSError as exc:
        print(f"[-] Could not read wordlist: {exc}")
        return []


def show_wordlist_info(name, entries):
    print(f"[+] {name}: {len(entries)} entries")