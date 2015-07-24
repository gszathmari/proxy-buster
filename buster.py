#/usr/bin/env python

import requests
import argparse
import sys
import difflib
import shelve
from urllib.parse import urlparse
from bs4 import BeautifulSoup

TIMEOUT = 5
# Fake user agent because of mischevious mirrors
HEADERS = {'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_4) AppleWebKit/600.7.12 (KHTML, like Gecko) Version/8.0.7 Safari/600.7.12'}

class Mirrors:
    def __init__(self, filename):
        self.data = shelve.open(filename)

    def __getitem__(self, url):
        try:
            return self.data[url]
        except KeyError:
            pass

    def close(self):
        self.data.close()

    # Retrieve website mirrors
    def populate(self, urls):
        counter = 1
        for url in urls:
            print("-> Retrieving mirror (%s/%s): %s" % (counter, len(mirror_urls), url))
            # Create website Object
            mirror = Website(url)
            # Do not add if retrieval was not successful
            if mirror.has_errors() is None:
                self.data[url] = mirror
            else:
                print("There was an error while retrieving %s, skipping ..." % url)
                if args.debug:
                    print("Message: %s\n" % mirror.has_errors())
            counter += 1

# Object to store website data
class Website:
    def __init__(self, url):
        url_object = urlparse(url)
        self.url = url_object.geturl()
        self.scheme = url_object.scheme
        self.error = None
        self.inline_scripts = []
        self.external_script_urls = []
        try:
            r = requests.get(self.url, timeout=TIMEOUT, headers=HEADERS)
            if r.status_code == 200:
                soup = BeautifulSoup(r.text, 'html.parser')
                # Parse HTML for <script> tags
                for tag in soup.find_all("script"):
                    # If tag is <script src="">
                    if tag.get("src"):
                        url = urlparse(tag.get("src"), self.scheme)
                        self.external_script_urls.append(url)
                    # If tag is inline script
                    else:
                        self.inline_scripts.append(str(tag))
            else:
                self.error = Error("Website did not respond with HTTP 200")
        except Exception as e:
            self.error = e

    def has_errors(self):
        return self.error

    def get_inline_scripts(self):
        return sorted(self.inline_scripts)

    def get_external_script_urls(self):
        return sorted(self.external_script_urls)

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

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Compare JavaScript assets between a selected website and its mirrors")
    groupMandatory = parser.add_argument_group('available mirror tests')
    groupDataFile = parser.add_argument_group('data file')
    parser.add_argument('-u', '--url', help='original website URL', required=True)
    parser.add_argument('-m', '--mirror-list', help='supply mirror URLs from file', metavar='file')
    parser.add_argument('mirrors', help='list of mirror website URLs', metavar='mirror', nargs='*')
    groupMandatory.add_argument('-i', '--inline', help='compare inline scripts between <script></script> tags', action='store_true')
    groupMandatory.add_argument('-e', '--external', help='compare list of URLs in <script src="">', action='store_true')
    groupMandatory.add_argument('-o', '--output', help='print test statistics into CSV file', metavar='file')
    groupDataFile.add_argument('-f', '--file', help='data file to store responses from mirrors', default='mirrors.dat')
    groupDataFile.add_argument('-n', '--nocheck', help='use data file instead of the Internet', action='store_true')
    parser.add_argument('-v', '--verbose', help='print contents of results', action='store_true')
    parser.add_argument('-d', '--debug', help='debug mode', action='store_true')

    args = parser.parse_args()

    if args.mirror_list:
        mirror_urls = []
        with open(args.mirror_list, 'r') as f:
            for line in f:
                mirror_urls.append(line.rstrip())
    else:
        mirror_urls = args.mirrors

    # Retrieve original website
    original = retrieve_original(args.url)

    # Load mirrors data file
    mirrors = Mirrors(args.file)

    if not args.nocheck:
        # Populate mirrors data file
        mirrors.populate(mirror_urls)

    # Generate CSV file with stats
    if args.output:
        separator = ','
        with open(args.output, 'w') as file:
            header = ["Original", "Mirror", "Additional Inline Scripts", "Additional External Scripts"]
            file.write("%s\n" % separator.join(header))
            for url in mirror_urls:
                # Retrieve data from shelve file
                mirror = mirrors[url]
                line = []
                # Generate CSV data
                line.append(original.url)
                line.append(mirror.url)
                line.append(len(diff_inline_scripts(original, mirror)))
                line.append(len(diff_external_script_urls(original, mirror)))
                output = map(str, line)
                # Add data to CSV
                file.write("%s\n" % separator.join(output))
        file.close()
        print("\n-> Output has been written to: %s\n" % args.output)

    if args.inline:
        print("\nCOMPARING INLINE SCRIPTS WITH ORIGINAL SITE")
        print('=' * 60)
        for url in mirror_urls:
            mirror = mirrors[url]
            # Skip if URL does not exist in data file
            if not mirror:
                print("-> %s does not exist in data file, skipping ...\n" % url)
                break
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
        for url in mirror_urls:
            mirror = mirrors[url]
            # Skip if URL does not exist in data file
            if not mirror:
                print("-> %s does not exist in data file, skipping ...\n" % url)
                break
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

mirrors.close()
print("Done.\n")
