import base64
import hashlib
import re
import subprocess

import requests
from bs4 import BeautifulSoup

_DEFAULT_ALGORITHM = "sha384"

_RECOGNIZED_ALGORITHMS = ("sha512", "sha384", "sha256")

_INTEGRITY_PATTERN = re.compile(
    r"""
    [ \t]*                                  # RFC 5234 (ABNF): WSP
    (?P<algorithm>%(algorithms)s)           # W3C CSP2: hash-algo
    -
    (?P<b64digest>[a-zA-Z0-9+/]+[=]{0,2})   # W3C CSP2: base64-value
    (?P<options>\?[\041-\176]*)?            # RFC 5234 (ABNF): VCHAR
    [ \t]*                                  # RFC 5234 (ABNF): WSP
    """
    % dict(algorithms="|".join(_RECOGNIZED_ALGORITHMS)),
    re.VERBOSE,
)


def _generate(resource, algorithm=_DEFAULT_ALGORITHM):
    hasher = hashlib.new(algorithm, resource)
    digest = hasher.digest()
    return f"{algorithm}-{base64.standard_b64encode(digest).decode()}"


def _update_tag(tag, src_attribute: str) -> bool:
    if tag.has_attr(src_attribute) and tag[src_attribute].startswith("https://"):
        used_algorithms = _DEFAULT_ALGORITHM
        if tag.has_attr("integrity"):
            match = _INTEGRITY_PATTERN.match(tag["integrity"])
            # print(match)
            if match is not None and match.group("algorithm") in _RECOGNIZED_ALGORITHMS:
                used_algorithms = match.group("algorithm")
            response = requests.get(tag[src_attribute])
            if not response.ok:
                print("Error while fetching", tag[src_attribute])
                return False

            tag["integrity"] = _generate(response.content, used_algorithms)
        if not hasattr(tag, "crossorigin"):
            tag["crossorigin"] = "anonymous"
        if not hasattr(tag, "referrerpolicy"):
            tag["referrerpolicy"] = "no-referrer"
    return True


with open("tilecloud_chain/templates/openlayers.html") as f:
    soup = BeautifulSoup(f, "html.parser")

    scripts = soup.findAll("script")
    for tag in scripts:
        _update_tag(tag, "src")

    styles = soup.findAll("link")
    for style in styles:
        _update_tag(style, "href")

with open("tilecloud_chain/templates/openlayers_.html", "w") as f:
    f.write(soup.prettify())

subprocess.run(["pre-commit", "run", "--file=tilecloud_chain/templates/openlayers_.html"])
