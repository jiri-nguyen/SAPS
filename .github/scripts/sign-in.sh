#!/usr/bin/env bash
# Signs a demo user in through Keycloak the way a browser does (SAPS-44): the SAPS API sends the browser to Keycloak,
# the login form is posted, Keycloak sends it back to the callback, which sets `saps_session` in the cookie jar.
# Prints the URL where the browser ends up; exits 1 when no SAPS session was created (e.g. `/?signIn=no_company`).
#
# Usage: sign-in.sh <web app origin> <username> <password> <cookie jar> [return path]
set -euo pipefail

web="$1" username="$2" password="$3" jar="$4" return_to="${5:-/}"
page="$(mktemp)"
trap 'rm -f "$page"' EXIT
rm -f "$jar"

quoted="$(python3 -c 'import sys, urllib.parse; print(urllib.parse.quote(sys.argv[1], safe=""))' "$return_to")"
curl -fsS -c "$jar" -b "$jar" -L -o "$page" "$web/v1/session/sign-in?returnTo=$quoted"

action="$(python3 - "$page" <<'PY'
import html.parser
import sys


class LoginForm(html.parser.HTMLParser):
    action = None

    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        if tag == "form" and values.get("id") == "kc-form-login":
            self.action = values.get("action")


form = LoginForm()
form.feed(open(sys.argv[1], encoding="utf-8").read())
if not form.action:
    sys.exit("no Keycloak login form on the sign-in page")
print(form.action)
PY
)"

final="$(curl -fsS -c "$jar" -b "$jar" -L -o /dev/null -w '%{url_effective}' \
  --data-urlencode "username=$username" --data-urlencode "password=$password" "$action")"
echo "$final"
case "$final" in
  *"signIn="*) exit 1 ;;
esac
grep -q saps_session "$jar"
