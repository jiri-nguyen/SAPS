"""Generate `deploy/keycloak/realm-saps.json` from `fixtures/companies.json` (SAPS-43).

Run `make keycloak-realm` in backend/. With `--check` it writes nothing and exits 1 when the committed file is
out of date (the tests check this in CI).
"""

import sys
from pathlib import Path

from saps.adapters.demo.companies import load_demo_companies
from saps.adapters.demo.keycloak_realm import render_realm

FIXTURES = Path(__file__).parents[1] / "fixtures"
TARGET = Path(__file__).parents[2] / "deploy" / "keycloak" / "realm-saps.json"


def main(argv: list[str]) -> int:
    content = render_realm(load_demo_companies(FIXTURES))
    if "--check" in argv:
        if not TARGET.exists() or TARGET.read_text() != content:
            print(f"{TARGET} is out of date: run `make keycloak-realm`", file=sys.stderr)
            return 1
        return 0
    TARGET.write_text(content)
    print(f"wrote {TARGET}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
