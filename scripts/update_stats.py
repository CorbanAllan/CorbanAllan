"""Refresh the public GitHub counts in both profile SVGs (standard library only)."""

import datetime
import json
import os
from pathlib import Path
from urllib.request import Request, urlopen
import xml.etree.ElementTree as ET


ROOT = Path(__file__).resolve().parents[1]
USER = "CorbanAllan"
NS = {"svg": "http://www.w3.org/2000/svg"}
ET.register_namespace("", NS["svg"])


def request(path):
    headers = {"Accept": "application/vnd.github+json", "User-Agent": "profile-stats"}
    if token := os.environ.get("GITHUB_TOKEN"):
        headers["Authorization"] = f"Bearer {token}"
    with urlopen(Request(f"https://api.github.com{path}", headers=headers), timeout=30) as response:
        return json.load(response)


def fetch_stats(fetch=request):
    user = fetch(f"/users/{USER}")
    stars = 0
    page = 1
    while True:
        repos = fetch(f"/users/{USER}/repos?type=owner&per_page=100&page={page}")
        stars += sum(repo["stargazers_count"] for repo in repos)
        if len(repos) < 100:
            break
        page += 1
    # shortcut: public indexed commits only; use authenticated GraphQL for private contributions.
    commits = fetch(f"/search/commits?q=author%3A{USER}%20is%3Apublic&per_page=1")
    if commits["incomplete_results"]:
        raise ValueError("GitHub returned incomplete commit statistics; keeping the previous SVGs")
    stats = {
        "repos": user["public_repos"],
        "stars": stars,
        "commits": commits["total_count"],
        "followers": user["followers"],
        "following": user["following"],
    }
    if any(type(value) is not int or value < 0 for value in stats.values()):
        raise ValueError("GitHub returned an invalid count")
    return stats


def render(svg, stats, date):
    root = ET.fromstring(svg)
    for name, value in {**stats, "updated": date}.items():
        elements = root.findall(f".//svg:tspan[@id='{name}']", NS)
        if len(elements) != 1:
            raise ValueError(f"Expected exactly one SVG field: {name}")
        elements[0].text = f"{value:,}" if isinstance(value, int) else value
    return ET.tostring(root, encoding="unicode") + "\n"


def main():
    stats = fetch_stats()
    date = datetime.datetime.now(datetime.timezone.utc).date().isoformat()
    paths = [ROOT / "assets" / f"profile-{theme}.svg" for theme in ("dark", "light")]
    # Validate both templates and fetch all data before changing either asset.
    rendered = [render(path.read_text(), stats, date) for path in paths]
    for path, svg in zip(paths, rendered):
        path.write_text(svg)
    print(json.dumps(stats, sort_keys=True))


if __name__ == "__main__":
    main()
