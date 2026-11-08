#!/usr/bin/env python3
"""Drop docker.io credential helpers so anonymous Hub pulls work under Podman.

Bad/empty docker.io entries in containers auth.json cause
"incorrect username/password" on anonymous pulls. Keeps other registries
(e.g. ghcr.io) intact.
"""

import argparse
import json
import sys
from pathlib import Path


def _is_docker_hub(key: str) -> bool:
    return "docker.io" in key or "index.docker.io" in key


def ensure_anonymous_dockerhub(auth_path: Path) -> bool:
    """Rewrite auth.json if needed. Returns True when the file was written."""
    auth_path.parent.mkdir(parents=True, exist_ok=True)
    data: dict = json.loads(auth_path.read_text()) if auth_path.exists() else {}
    helpers = dict(data.get("credHelpers") or {})
    auths = dict(data.get("auths") or {})
    changed = False

    for key in list(helpers):
        if _is_docker_hub(key):
            helpers.pop(key)
            changed = True

    for key in list(auths):
        if _is_docker_hub(key) and not auths[key]:
            auths.pop(key)
            changed = True

    data["credHelpers"] = helpers
    data["auths"] = auths

    if changed or not auth_path.exists():
        auth_path.write_text(json.dumps(data, indent=2) + "\n")
        return True
    return False


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "auth_path",
        nargs="?",
        type=Path,
        default=Path.home() / ".config" / "containers" / "auth.json",
        help="Path to containers auth.json (default: ~/.config/containers/auth.json)",
    )
    args = parser.parse_args(argv)
    if ensure_anonymous_dockerhub(args.auth_path):
        print(f"updated {args.auth_path} for anonymous docker.io pulls")
    return 0


if __name__ == "__main__":
    sys.exit(main())
