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
                results.append(str(tag))
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

def retrieve_mirrors(urls):
    mirrors = []
    counter = 1
    for url in urls:
        print("-> Retrieving mirror (%s/%s): %s" % (counter, len(args.mirrors), url))
        mirror = Website(url)
        if mirror.has_errors() is None:
            mirrors.append(mirror)
        else:
            print("There was an error while retrieving %s, skipping ..." % url)
            if args.debug:
                print("Message: %s\n" % mirror.has_errors())
        counter += 1
    return mirrors

def retrieve_original(url):
    print("-> Retrieving original: %s\n" % args.url)
    original = Website(url)
    if original.has_errors():
        sys.exit("\nERROR: Cannot retrieve URL, please try again")
    else:
        return original

def diff_inline_scripts(original, mirror):
    original_inline_scripts = original.get_inline_scripts()
    mirror_inline_scripts = mirror.get_inline_scripts()
    return set(original_inline_scripts) - set(mirror_inline_scripts)

def diff_external_script_urls(original, mirror):
    results = []
    original_script_urls = [url.geturl() for url in original.get_external_script_urls()]
    mirror_script_urls = mirror.get_external_script_urls()
    for mirror_url in mirror_script_urls:
        if not any(w.endswith(mirror_url.path) for w in original_script_urls):
            results.append(mirror_url)
    return results

def diff_external_script_contents(original, mirror):
    results = []
    original_script_urls = [url.geturl() for url in original.get_external_script_urls()]
    mirror_script_urls = mirror.get_external_script_urls()
    for mirror_url in mirror_script_urls:
        for original_url in original_script_urls:
            if original_url.endswith(mirror_url.path):
                try:
                    original_script = requests.get(original_url, timeout=TIMEOUT, headers=HEADERS)
                    mirror_script = requests.get(mirror_url.geturl(), timeout=TIMEOUT, headers=HEADERS)
                    if original_script.status_code == 200 and mirror_script.status_code == 200:
                        if len(original_script.text) != len(mirror_script.text):
                            result = {
                                'original_url': original_url,
                                'mirror_url': mirror_url.geturl(),
                                'original_script': original_script.text,
                                'mirror_script': mirror_script.text
                            }
                            results.append(result)
                except Exception as e:
                    if args.debug:
                        print("-> Error: Could not check difference between %s and %s\n" % (url1, url2))
                        print(e)
                    else:
                        pass
    return results

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Compare JavaScript assets between a website and its mirrors")
    parser.add_argument('-u', '--url', help='original website URL', required=True)
    parser.add_argument('mirrors', help='list of mirror website URLs', metavar='URLs', nargs='*')
    parser.add_argument('-o', '--output', help='print results into CSV file', metavar='file')
    parser.add_argument('-i', '--inline', help='compare inline scripts between <script></script> tags', action='store_true')
    parser.add_argument('-e', '--external', help='compare list of URLs in <script src="">', action='store_true')
    parser.add_argument('-a', '--assets', help='compare contents of matching external scripts', action='store_true')
    parser.add_argument('-v', '--verbose', help='print contents of results', action='store_true')
    parser.add_argument('-d', '--debug', help='debug mode', action='store_true')

    args = parser.parse_args()
    orig = retrieve_original(args.url)
    mirrors = retrieve_mirrors(args.mirrors)

    print("\n-> Done, crunching data ...\n")

    if args.output:
        separator = ','
        with open(args.output, 'w') as file:
            header = ["Original", "Mirror", "Additional Inline Scripts", "Additional External Scripts", "Differing External Scripts"]
            file.write("%s\n" % separator.join(header))
            for mirror in mirrors:
                line = []
                line.append(orig.url)
                line.append(mirror.url)
                line.append(len(diff_inline_scripts(orig, mirror)))
                line.append(len(diff_external_script_urls(orig, mirror)))
                line.append(len(diff_external_script_contents(orig, mirror)))
                output = map(str, line)
                file.write("%s\n" % separator.join(output))
        file.close()

    if args.inline:
        print("\nCOMPARING INLINE SCRIPTS WITH ORIGINAL SITE")
        print('=' * 64)
        for mirror in mirrors:
            print("%s <=> %s" % (orig.url, mirror.url))
            results = diff_inline_scripts(orig, mirror)
            if len(results) > 0:
                print("!!! %s additional inline scripts found, use '-v' for more details\n" % (len(results)))
                if args.verbose:
                    print("!!! The following inline scripts are inserted on this mirror:")
                    for result in results:
                        print("\n%s\n" % result)
                        print('- ' * 32)
            else:
                print("-> Phew! No difference is found, all inline scripts match\n")

    if args.external:
        print("\nDIFFERENCES IN LIST OF EXTERNAL SCRIPTS WITH ORIGINAL SITE")
        print('=' * 64)
        for mirror in mirrors:
            print("\n%s <=> %s" % (orig.url, mirror.url))
            print('-' * 64)
            results = diff_external_script_urls(orig, mirror)
            if len(results) > 0:
                print("!!! %s additional scripts found, use '-v' for more details\n" % (len(results)))
                if args.verbose:
                    print("!!! Injected scripts:")
                    for result in results:
                        print("  <script src=\"%s\">" % result.geturl())
            else:
                print("-> Phew! No difference is found, list of external scripts match\n")

    if args.assets:
        print("\nDIFFERENCES IN CONTENTS OF MATCHING EXTERNAL SCRIPTS")
        print('=' * 64)
        for mirror in mirrors:
            scripts = diff_external_script_contents(orig, mirror)
            for script in scripts:
                result = []
                print("!!! Difference found in %s and %s\n" % (script['original_url'], script['mirror_url']))
                for line in difflib.unified_diff(script['original_script'].split("\n"), script['mirror_script'].split("\n"), fromfile=script['original_script'], tofile=script['mirror_script']):
                    result.append(line[:75] + (line[75:] and ".."))
                    print("\n".join(result))

    print("\nDone.")
