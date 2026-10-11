import unittest
import xml.etree.ElementTree as ET

from update_stats import NS, ROOT, fetch_stats, render


class StatsTests(unittest.TestCase):
    def fetch(self, path):
        if path.startswith("/search/"):
            return {"total_count": 1234, "incomplete_results": False}
        if "/repos?" in path:
            return [{"stargazers_count": 2}] * (100 if path.endswith("&page=1") else 1)
        return {"public_repos": 101, "followers": 7, "following": 3}

    def test_paginates_repositories_and_uses_commit_total(self):
        self.assertEqual(fetch_stats(self.fetch), {
            "repos": 101, "stars": 202, "commits": 1234, "followers": 7, "following": 3,
        })

    def test_incomplete_commit_results_fail(self):
        def fetch(path):
            data = self.fetch(path)
            if path.startswith("/search/"):
                data["incomplete_results"] = True
            return data
        with self.assertRaisesRegex(ValueError, "incomplete"):
            fetch_stats(fetch)

    def test_both_templates_render_every_stat(self):
        stats = fetch_stats(self.fetch)
        for theme in ("dark", "light"):
            svg = (ROOT / "assets" / f"profile-{theme}.svg").read_text()
            root = ET.fromstring(render(svg, stats, "2026-10-11"))
            for key, value in stats.items():
                self.assertEqual(root.find(f".//svg:tspan[@id='{key}']", NS).text, f"{value:,}")
            self.assertEqual(root.find(".//svg:tspan[@id='updated']", NS).text, "2026-10-11")

    def test_missing_fields_fail(self):
        with self.assertRaisesRegex(ValueError, "SVG field"):
            render('<svg xmlns="http://www.w3.org/2000/svg"/>', {"repos": 3}, "2026-10-11")


if __name__ == "__main__":
    unittest.main()
