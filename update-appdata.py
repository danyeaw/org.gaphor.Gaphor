import re
import ssl
import sys
import textwrap
import time
import urllib.request
from xml.etree import ElementTree as etree

from markdown_it import MarkdownIt


def update_release(appdata_file, version, date, notes):
    tree = etree.parse(appdata_file)

    release = find_release(tree, version, date)
    update_release_details(release, version, notes)

    etree.indent(tree)
    tree.write(appdata_file, encoding="utf-8", xml_declaration=True)


def find_release(tree, version, date):
    if (release := tree.find(f"./releases/release[@version='{version}']")) is None:
        release = etree.Element("release", attrib={"version": version, "date": date})
        tree.find("./releases").insert(0, release)

    return release


def test_find_release():
    tree = etree.parse("share/org.gaphor.Gaphor.appdata.xml")

    release = find_release(tree, "2.17.0", "DATE")

    # Should have found the existing node
    assert release.attrib["date"] != "DATE"


def update_release_details(release, version, notes):
    for node in release.findall("*"):
        release.remove(node)

    release.append(notes)

    url = etree.SubElement(release, "url")
    url.text = f"https://github.com/gaphor/gaphor/releases/tag/{version}"


def download_news_from_github():
    url = "https://raw.githubusercontent.com/gaphor/gaphor/main/CHANGELOG.md"
    with urllib.request.urlopen(url, context=ssl.create_default_context()) as response:
        return response.read().decode(encoding="utf-8")


def test_download_news_from_github():
    news = download_news_from_github()

    assert news
    assert "2.18.0" in news


def parse_changelog(changelog_md: str):
    md = MarkdownIt("default", {"breaks": False, "html": True})
    html = md.render(changelog_md)
    changelog = etree.fromstring(f"<root>{html}</root>")

    version = "INVALID"
    news: dict[str, etree.Element] = {}

    for node in changelog:
        if node.tag == "h2" and node.text:
            version = node.text
            news[version] = etree.Element("description")
        else:
            news[version].append(node)

    return news


def test_parse_changelog():
    fragment = textwrap.dedent("""\
        2.1.0
        ------
        - Feature
          three
        - Feature four

        2.0.0
        ------
        - Feature one
        - Feature two
        """)

    changelog = parse_changelog(fragment)

    assert "2.0.0" in changelog
    assert "2.1.0" in changelog

    assert "Feature one" in etree.tostring(changelog["2.0.0"]).decode("utf-8")
    assert "Feature two" in etree.tostring(changelog["2.0.0"]).decode("utf-8")
    assert "Feature\nthree" in etree.tostring(changelog["2.1.0"]).decode("utf-8")
    assert "Feature four" in etree.tostring(changelog["2.1.0"]).decode("utf-8")


def run_tests():
    for name, maybe_test in list(globals().items()):
        if name.startswith("test_"):
            print(name, "...", end="")
            maybe_test()
            print(" okay")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        version = sys.argv[1]
        today = time.strftime("%Y-%m-%d")
        changelog = parse_changelog(download_news_from_github())
        update_release(
            "share/org.gaphor.Gaphor.appdata.xml",
            version,
            today,
            changelog.get(version, ["Bug fixes."]),
        )
    else:
        run_tests()
