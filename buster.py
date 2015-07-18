#/usr/bin/env python

import requests
import argparse
import sys
import difflib
from urllib.parse import urlparse
from bs4 import BeautifulSoup

TIMEOUT = 5
# Fake user agent because of mischevious mirrors
HEADERS = {'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_4) AppleWebKit/600.7.12 (KHTML, like Gecko) Version/8.0.7 Safari/600.7.12'}

# Object to store website data
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

    # To check if retrieval was successful
    def has_errors(self):
        return self.error

    # Parse HTML to extract inline <script> tags
    def get_inline_scripts(self):
        results = []
        for tag in self.soup.find_all("script"):
            # This is for filtering out external scripts
            if tag.get("src") is None:
                results.append(str(tag))
        return sorted(results)

    # Parse HTML to extract URLs pointing to external scripts
    def get_external_script_urls(self):
        results = []
        for tag in self.soup.find_all("script"):
            # We filter out inline scripts
            if tag.get("src"):
                url = urlparse(tag.get("src"), self.scheme)
                results.append(url)
        return sorted(results)

# Retrieve website mirrors
def retrieve_mirrors(urls):
    mirrors = []
    counter = 1
    for url in urls:
        print("-> Retrieving mirror (%s/%s): %s" % (counter, len(args.mirrors), url))
        # Create website Object
        mirror = Website(url)
        # Do not add if retrieval was not successful
        if mirror.has_errors() is None:
            mirrors.append(mirror)
        else:
            print("There was an error while retrieving %s, skipping ..." % url)
            if args.debug:
                print("Message: %s\n" % mirror.has_errors())
        counter += 1
    return mirrors

# Retrieve original website for comparison
def retrieve_original(url):
    print("-> Retrieving original: %s\n" % args.url)
    original = Website(url)
    # If download fails, give up and exit
    if original.has_errors():
        sys.exit("\nERROR: Cannot retrieve URL, please try again")
    else:
        return original

# Extract inline scripts from original and mirror and return the differences
def diff_inline_scripts(original, mirror):
    original_inline_scripts = original.get_inline_scripts()
    mirror_inline_scripts = mirror.get_inline_scripts()
    return set(original_inline_scripts) - set(mirror_inline_scripts)

# Extract external script URLs return those are not on the original website
def diff_external_script_urls(original, mirror):
    results = []
    # Get all script URLs from original website
    original_script_urls = [url.geturl() for url in original.get_external_script_urls()]
    # Get all script URLs from mirror
    mirror_script_urls = mirror.get_external_script_urls()
    # Compare mirror URLs with original
    for mirror_url in mirror_script_urls:
        # If mirror URL is not on the original website, add to results
        if not any(w.endswith(mirror_url.path) for w in original_script_urls):
            results.append(mirror_url)
    return results

# Retrieve external scripts and compare their contents
def diff_external_script_contents(original, mirror):
    results = []
    # Get all script URLs from original website
    original_script_urls = [url.geturl() for url in original.get_external_script_urls()]
    # Get all script URLs from mirror
    mirror_script_urls = mirror.get_external_script_urls()
    # Find script URLs that are in the original and the mirror site
    for mirror_url in mirror_script_urls:
        for original_url in original_script_urls:
            # If matching script URL is found, retrieve both for comparison
            if original_url.endswith(mirror_url.path):
                try:
                    original_script = requests.get(original_url, timeout=TIMEOUT, headers=HEADERS)
                    mirror_script = requests.get(mirror_url.geturl(), timeout=TIMEOUT, headers=HEADERS)
                    # If retrieval was successul, compare if they match
                    if original_script.status_code == 200 and mirror_script.status_code == 200:
                        # If script does not match, add to results
                        if len(original_script.text) != len(mirror_script.text):
                            result = {
                                'original_url': original_url,
                                'mirror_url': mirror_url.geturl(),
                                'original_script': original_script.text,
                                'mirror_script': mirror_script.text
                            }
                            results.append(result)
                # Handle requests library exceptions
                except Exception as e:
                    if args.debug:
                        print("-> Error: Could not check difference between %s and %s\n" % (url1, url2))
                        print(e)
                    else:
                        pass
    return results

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Compare JavaScript assets between a selected website and its mirrors")
    groupMandatory = parser.add_argument_group('available mirror tests')
    parser.add_argument('-u', '--url', help='original website URL', required=True)
    parser.add_argument('mirrors', help='list of mirror website URLs', metavar='mirror', nargs='*')
    groupMandatory.add_argument('-i', '--inline', help='compare inline scripts between <script></script> tags', action='store_true')
    groupMandatory.add_argument('-e', '--external', help='compare list of URLs in <script src="">', action='store_true')
    groupMandatory.add_argument('-a', '--assets', help='compare contents of matching external scripts', action='store_true')
    groupMandatory.add_argument('-o', '--output', help='print test statistics into CSV file', metavar='file')
    parser.add_argument('-v', '--verbose', help='print contents of results', action='store_true')
    parser.add_argument('-d', '--debug', help='debug mode', action='store_true')

    args = parser.parse_args()
    # Retrieve original and mirror websites
    original = retrieve_original(args.url)
    mirrors = retrieve_mirrors(args.mirrors)

    # Generate CSV file with stats
    if args.output:
        separator = ','
        with open(args.output, 'w') as file:
            header = ["Original", "Mirror", "Additional Inline Scripts", "Additional External Scripts", "Differing External Scripts"]
            file.write("%s\n" % separator.join(header))
            for mirror in mirrors:
                line = []
                line.append(original.url)
                line.append(mirror.url)
                line.append(len(diff_inline_scripts(original, mirror)))
                line.append(len(diff_external_script_urls(original, mirror)))
                line.append(len(diff_external_script_contents(original, mirror)))
                output = map(str, line)
                file.write("%s\n" % separator.join(output))
        file.close()
        print("\n-> Output has been written to: %s\n" % args.output)

    if args.inline:
        print("\nCOMPARING INLINE SCRIPTS WITH ORIGINAL SITE")
        print('=' * 60)
        for mirror in mirrors:
            print("\n%s <=> %s" % (original.url, mirror.url))
            print('-' * 60)
            results = diff_inline_scripts(original, mirror)
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
        print('=' * 60)
        for mirror in mirrors:
            print("\n%s <=> %s" % (original.url, mirror.url))
            print('-' * 60)
            results = diff_external_script_urls(original, mirror)
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
        print('=' * 60)
        for mirror in mirrors:
            print("\n%s <=> %s" % (original.url, mirror.url))
            print('-' * 60)
            scripts = diff_external_script_contents(original, mirror)
            if len(scripts) > 0:
                for script in scripts:
                    # Use difflib to generate fancy results
                    result = []
                    print("!!! Difference found in %s and %s\n" % (script['original_url'], script['mirror_url']))
                    for line in difflib.unified_diff(script['original_script'].split("\n"), script['mirror_script'].split("\n"), fromfile=script['original_script'], tofile=script['mirror_script']):
                        result.append(line[:75] + (line[75:] and ".."))
                        print("\n".join(result))
            else:
                print("-> Phew! No differences are found in external scripts\n")

print("Done.\n")
