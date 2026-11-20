import datetime as dt
import json
from html import unescape
from html.parser import HTMLParser
import os
from pathlib import Path
import re
import subprocess
from urllib.error import HTTPError
from urllib.parse import urlparse
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo


def api(path, method="GET", payload=None):
    token = os.environ["MAILERLITE_API_TOKEN"].strip()
    if not re.fullmatch(r"[A-Za-z0-9._~+/=-]{32,}", token):
        raise SystemExit("MAILERLITE_API_TOKEN is missing or malformed")
    request = Request(
        "https://connect.mailerlite.com/api/" + path,
        data=None if payload is None else json.dumps(payload).encode(),
        headers={"Authorization": "Bearer " + token,
                 "Accept": "application/json", "Content-Type": "application/json"},
        method=method,
    )
    try:
        with urlopen(request, timeout=25) as response:
            return json.load(response)
    except HTTPError as error:
        raise SystemExit(f"MailerLite {method} {path.split('?')[0]} returned HTTP {error.code}") from None


def issue_path():
    if os.environ.get("ISSUE_DATE"):
        date = dt.date.fromisoformat(os.environ["ISSUE_DATE"])
        return Path(f"newsletters/sunday-jam/{date}.json")
    before = os.environ["BEFORE_SHA"]
    sha = os.environ["GITHUB_SHA"]
    files = subprocess.check_output(
        ["git", "diff", "--name-only", "--diff-filter=AM", before, sha],
        text=True,
    ).splitlines()
    issues = [Path(file) for file in files
              if re.fullmatch(r"newsletters/sunday-jam/\d{4}-\d{2}-\d{2}\.json", file)]
    if len(issues) != 1:
        raise SystemExit("Expected exactly one changed Sunday Jam issue")
    return issues[0]


def matching_records(path, name):
    while path:
        result = api(path)
        yield from (record for record in result["data"] if record["name"] == name)
        next_page = result.get("links", {}).get("next")
        path = None
        if next_page:
            url = urlparse(next_page)
            if url.scheme != "https" or url.netloc != "connect.mailerlite.com":
                raise SystemExit("Unexpected MailerLite pagination URL")
            path = url.path.removeprefix("/api/") + "?" + url.query


class NewsletterBlocks(HTMLParser):
    def __init__(self):
        super().__init__()
        self.blocks = []
        self.text = []
        self.href = None
        self.heading = False

    def flush(self):
        if any(node["text"].strip() for node in self.text):
            self.blocks.append(("heading" if self.heading else "paragraph",
                                {"content": self.text}))
        self.text = []

    def handle_starttag(self, tag, attributes):
        attrs = dict(attributes)
        if tag in {"h1", "h2", "h3", "p", "li", "td"}:
            self.flush()
            self.heading = tag.startswith("h")
        elif tag == "img":
            self.flush()
            src = attrs.get("src", "")
            if not src.startswith("https://"):
                raise SystemExit("Newsletter images require HTTPS URLs")
            self.blocks.append(("image", {"attrs": {"src": src, "alt": attrs.get("alt", "")}}))
        elif tag == "a":
            self.href = attrs.get("href")

    def handle_endtag(self, tag):
        if tag in {"h1", "h2", "h3", "p", "li", "td"}:
            self.flush()
            self.heading = False
        elif tag == "a":
            self.href = None
        elif tag == "body":
            self.flush()

    def handle_data(self, value):
        if self.href == "{$unsubscribe}":
            return  # MailerLite's simple editor includes its own unsubscribe footer.
        node = {"type": "text", "text": re.sub(r"\s+", " ", value)}
        if self.href:
            if not self.href.startswith("https://"):
                raise SystemExit("Newsletter links require HTTPS URLs")
            node["marks"] = [{"type": "link", "attrs": {"href": self.href}}]
        self.text.append(node)


def main():
    path = issue_path()
    issue_date = dt.date.fromisoformat(path.stem)
    issue = json.loads(path.read_text())
    if issue_date.weekday() != 6:
        raise SystemExit("Expected a Sunday issue date")
    html = issue["html"]
    markers = ("This Week at Jam Lab", "Highest rated", "Lowest rated",
               "Archive pick", "The Latest Article", "The Rest of the Reviews",
               "Around the Music World", "Five Albums on the Radar", "{$unsubscribe}")
    if len(html) < 2500 or any(marker not in html for marker in markers):
        raise SystemExit("Issue HTML is incomplete")
    blocks = NewsletterBlocks()
    body = re.search(r"<body\b[^>]*>([\s\S]+)</body>", html, re.IGNORECASE)
    if not body:
        raise SystemExit("Issue is missing its HTML body")
    blocks.feed(body.group(1))
    blocks.flush()
    live = os.environ.get("SUNDAY_JAM_LIVE") == "true"
    name = f"The Sunday Jam | {issue_date}" + ("" if live else " | verified-editor proof")
    groups = []
    send_at = None
    if live:
        chicago = ZoneInfo("America/Chicago")
        now = dt.datetime.now(chicago)
        send_at = dt.datetime.combine(issue_date, dt.time(8), chicago)
        if not dt.timedelta() < send_at - now <= dt.timedelta(days=3):
            raise SystemExit("Production scheduling requires a Sunday within the next three days")
        matches = list(matching_records("groups?limit=100", "The Sunday Jam"))
        if len(matches) != 1:
            raise SystemExit("Expected exactly one Sunday Jam subscriber group")
        groups = [matches[0]["id"]]

    existing_draft = None
    for status in ("sent", "ready", "draft"):
        existing = list(matching_records(f"campaigns?filter[status]={status}&limit=100", name))
        if existing and status != "draft":
            print(f"Issue already exists ({status})")
            return
        if len(existing) > 1:
            raise SystemExit("Multiple MailerLite drafts match this issue")
        if existing:
            existing_draft = existing[0]

    payload = {
        "name": name,
        "type": "regular",
        "groups": groups,
        "emails": [{"subject": issue["subject"], "from_name": "Jam Laboratory",
                    "from": "newsletter@jamlaboratory.com", "editor": "simple"}],
    }
    if existing_draft:
        campaign_id = existing_draft["id"]
        api(f"campaigns/{campaign_id}", "PUT", {"name": name, "groups": groups})
    else:
        campaign_id = api("campaigns", "POST", payload)["data"]["id"]
    print(f"Created MailerLite draft {campaign_id}", flush=True)
    saved = api(f"campaigns/{campaign_id}")["data"]
    email, = saved["emails"]
    email_path = f"emails/{email['id']}"
    content = api(email_path)
    etag = content["etag"]
    for block in content["data"]["blocks"]:
        etag = api(f"{email_path}/blocks/{block['id']}", "DELETE", {"etag": etag})["etag"]
    for block_type, editor_content in blocks.blocks:
        etag = api(f"{email_path}/blocks", "POST", {
            "etag": etag, "type": block_type, "editor_content": editor_content,
        })["etag"]

    preview = unescape(api(f"{email_path}/html")["data"]["html"])
    if any(marker not in preview for marker in markers):
        raise SystemExit("The saved MailerLite preview is missing required content")
    if not live:
        print("Verified saved MailerLite HTML. No email scheduled or sent.")
        return
    timezones = [row for row in api("timezones")["data"]
                 if row["name"] == "America/Chicago"]
    if len(timezones) != 1:
        raise SystemExit("MailerLite did not return exactly one America/Chicago timezone")
    api(f"campaigns/{campaign_id}/schedule", "POST", {
        "delivery": "scheduled",
        "schedule": {"date": send_at.strftime("%Y-%m-%d"),
                     "hours": "08", "minutes": "00",
                     "timezone_id": int(timezones[0]["id"])},
    })
    print(f"Scheduled campaign {campaign_id} for {send_at.isoformat()}")


if __name__ == "__main__":
    main()
