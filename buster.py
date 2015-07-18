#/usr/bin/env python

import requests
import argparse
import sys
import difflib
from urllib.parse import urlparse
from bs4 import BeautifulSoup

TIMEOUT = 5
HEADERS = {'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_4) AppleWebKit/600.7.12 (KHTML, like Gecko) Version/8.0.7 Safari/600.7.12'}

class Website:
    def __init__(self, url):
        u = urlparse(url)
        self.url = u.geturl()
        self.scheme = u.scheme
        self.error = None
        try:
            r = requests.get(self.url, timeout=TIMEOUT, headers=HEADERS)
            if r.status_code == 200:
                self.soup = BeautifulSoup(r.text, 'html.parser')
            else:
                self.error = Error("Website did not respond with HTTP 200")
        except Exception as e:
            self.error = e

    def has_errors(self):
        return self.error

    def get_inline_scripts(self):
        results = []
        for tag in self.soup.find_all("script"):
            if tag.get("src") is None:
                results.append(tag.get_text(strip=True))
        return sorted(results)

    def get_external_script_urls(self):
        results = []
        for tag in self.soup.find_all("script"):
            if tag.get("src"):
                url = urlparse(tag.get("src"), self.scheme)
                results.append(url)
        return sorted(results)

    def get_external_script_assets(self):
        results = {}
        urls = self.get_external_script_urls()
        for url in urls:
            result = {}
            try:
                r = requests.get(url.geturl(), timeout=TIMEOUT, headers=HEADERS)
                if r.status_code == 200:
                    results[url.path] = r.text
            except Exception:
                pass
        return results

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Compare JavaScript assets between a website and its mirrors")
    parser.add_argument('-u', '--url', help='original website URL', required=True)
    parser.add_argument('mirrors', help='list of mirror website URLs', metavar='URLs', nargs='*')
    parser.add_argument('-i', '--inline', help='compare inline scripts between <script></script> tags', action='store_true')
    parser.add_argument('-e', '--external', help='compare list of URLs in <script src="">', action='store_true')
    parser.add_argument('-a', '--assets', help='compare contents of external scripts', action='store_true')
    parser.add_argument('-v', '--verbose', help='print contents of results', action='store_true')
    parser.add_argument('-d', '--debug', help='debug mode', action='store_true')

    args = parser.parse_args()
    mirrors = []
    counter = 1
    orig = Website(args.url)

    print("-> Retrieving original: %s" % args.url)
    if orig.has_errors():
        print(orig.has_errors())
        sys.exit("\nERROR: Cannot retrieve URL, please try again")
    for url in args.mirrors:
        print("-> Retrieving mirror (%s/%s): %s" % (counter, len(args.mirrors), url))
        mirror = Website(url)
        if mirror.has_errors() is None:
            mirrors.append(mirror)
        else:
            print("There was an error while retrieving %s, skipping ..." % url)
            if args.debug:
                print("Message: %s\n" % mirror.has_errors())
        counter += 1

    if args.inline:
        orig_inline_scripts = orig.get_inline_scripts()
        print("\nComparing inline scripts with original".upper())
        print('=' * 50)
        for mirror in mirrors:
            results = set(orig_inline_scripts) - set(mirror.get_inline_scripts())
            print("%s <=> %s" % (orig.url, mirror.url))
            if len(results) > 0:
                print("!!! %s additional inline scripts found, use '-v' for more details\n" % (len(results)))
                if args.verbose:
                    for result in results:
                        print(result)
                        print('-' * 64)
            else:
                print("-> Phew! No difference is found, all inline scripts match\n")

    if args.external:
        orig_urls = [orig_url.geturl() for orig_url in orig.get_external_script_urls()]
        print("\nComparing list of external scripts with original".upper())
        print('=' * 50)
        for mirror in mirrors:
            print("\n%s <=> %s" % (orig.url, mirror.url))
            print('-' * 64)
            results = []
            for mirror_url in mirror.get_external_script_urls():
                if not any(w.endswith(mirror_url.path) for w in orig_urls):
                    results.append(mirror_url)
            if len(results) > 0:
                print("!!! %s additional scripts found, use '-v' for more details\n" % (len(results)))
                if args.verbose:
                    print("!!! Injected scripts:")
                    for result in results:
                        print(result)
                        print("  <script src=\"%s\">" % result.geturl())
            else:
                print("-> Phew! No difference is found, list of external scripts match\n")

    if args.assets:
        orig_urls = [orig_url.geturl() for orig_url in orig.get_external_script_urls()]
        print("\nComparing contents of external scripts".upper())
        print('=' * 50)
        for mirror in mirrors:
            print("Checking: %s <=> %s\n" % (orig.url, mirror.url))
            for mirror_url in mirror.get_external_script_urls():
                for orig_url in orig_urls:
                    if orig_url.endswith(mirror_url.path):
                        url1 = orig_url
                        url2 = mirror_url.geturl()
                        try:
                            r1 = requests.get(url1, timeout=TIMEOUT, headers=HEADERS)
                            r2 = requests.get(url2, timeout=TIMEOUT, headers=HEADERS)
                            if r1.status_code == 200 and r2.status_code == 200:
                                result = []
                                for line in difflib.unified_diff(r1.text.split("\n"), r2.text.split("\n"), fromfile=url1, tofile=url2):
                                    result.append(line[:75] + (line[75:] and ".."))
                                if len(result) > 0:
                                    print("\n".join(result))
                                    print("!!! Difference found in %s and %s\n" % (url1, url2))
                        except Exception as e:
                            if args.debug:
                                print("-> Error: Could not check difference between %s and %s\n" % (url1, url2))
                                print(e)
                            else:
                                pass

    print("\nDone.")
