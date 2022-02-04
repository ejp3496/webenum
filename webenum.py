#!/usr/bin/env python3.8
#
#                                           WEBenum
#
# @desc a tool to enumerator web directories using both recursive spidering and directory guessing.
#
# @author Evan Palmiotti
# @required requests, argparse, bs4, re, sys
########################################################################################################

import requests
import argparse
from bs4 import BeautifulSoup
import re
from sys import stdout
import datetime

BANNER = "\n" \
        "|‾|" + " " * 5 + "/‾/ " + "_" * 4 + "/ __ )___  ____  __  " + "_" * 6 + " ___\n" \
        "| | /| / / __/ / __  / _ \\/ __ \\/ / / / __ `__ \\\n" \
        "| |/ |/ / /___/ /_/ /  __/ / / / /_" + "/ " * 7 + "\n|__/|__/"+"_" * 5 + "/"+"_" * 5 + "" \
        "/\\___/_/ /_/\\__,_/_/ /_/ /_/\n" \
        "" + "=" * 50 + "\n" + " " * 25 + "=" * 25 + "\n" + " " * 38 + "=" * 12  # Ascii art banner

URLS = []                # found urls (updated by script)
DOMAINS = []             # found domains (updated by script)
WORDLIST = []              # word list read from file
ARGS: any                # stored arguments (updated by script)
ORIGINAL_DOMAIN = ''     # Original Domain (updated by script)
DEPTH = 3                # Default depth for spidering

#
# @desc easy access storage for urls
# @var service - service string (http or https)
# @var domain - domain and subdomain string
# @var path - url path
# @var port - port sting (ex. :443)
# @var params - anything after '?' in the url
#
class Url:
    def __init__(self, path):
        reg_match = parse_url(path)
        self.service = reg_match.group('service') or ''
        self.domain = reg_match.group('domain') or ''
        self.path = reg_match.group('path') or ''
        self.port = reg_match.group('port') or ''
        self.params = reg_match.group('params') or ''
        self.status = None

    def set_status(self, status):
        self.status = status

    def __str__(self): return self.service+self.domain+self.port+self.path+self.params

    def __repr__(self): return self.service+self.domain+self.port+self.path

    def __eq__(self, other): return repr(self) == repr(other)

    def __lt__(self, other): return repr(other) < repr(self)

    def __le__(self, other): return repr(other) <= repr(self)

    def __gt__(self, other): return repr(other) > repr(self)

    def __ge__(self, other): return repr(other) >= repr(self)

#
# @desc sets command line arguments and help strings.
#   parses command line arguments using argparse and returns an object of settings.
#
# @return parsed_args - Namespace with arguments
#
def parseargs():
    parser = argparse.ArgumentParser(description='Enumerate web directories using spidering and directory guessing.',
                                     epilog='placeholder')
    parser.add_argument('-url', '-u', help='url to crawl', required=True)
    parser.add_argument('--quiet', '-q', help="Don't display banner", action='store_true')
    parser.add_argument('--allow-subdomains', '-s', help="allow scanner to request subdomains", action='store_true')
    parser.add_argument('--depth', '-d', help="depth of directory spidering (default="+str(DEPTH), type=int)
    parser.add_argument('--wordlist', '-w', help="wordlist to use for directory guessing")
    parser.add_argument('--check-all-urls', '-c', help="Don't check URLs found in HTML pages for status codes",
                        action='store_true')
    return parser.parse_args()

#
# @desc Prints pretty ascii art banner
#
def print_banner():
    print(BANNER)
    print('\n'+'='*75+'\n')

#
# @desc Prints update to bottom of the screen while running
# @param update - string to print
#
def print_update(update):
    update = str(datetime.datetime.now().strftime('%H:%M:%S')) + ': ' + update
    if len(update) > 100:
        update = update[0:97:]+'...'
    stdout.write('\r'+update)
    stdout.flush()

#
# @desc Prints url to the screen without interfering with the update text
# @param url - url to print
#
def print_new_url(url):
    if url.status is not None:
        print("\033[F\r%-150s \t (status:%3s)" % (str(url), url.status))
    else:
        print("\033[F\r%-150s \t" % (str(url)))

#
# @desc Overwrites final update and print various statistics
#
def print_final_stats():
    print('\r'+' '*100)
    print('='*75+'\n')
    print('STATISTICS:')
    print('\tURLS:', len(URLS))
    print('\tDOMAINS:', len(DOMAINS))

#
# @desc Parses url in string form and return a regex object with named groups
# @param str_url - url to print
#
def parse_url(str_url):
    reg_url = re.compile("^(?P<service>https?://)?(?P<domain>[a-zA-Z0-9.]*)?(?P<port>:\d{1,4})?"
                         "(?P<path>[/.%_\-a-zA-Z0-9]*)?(?P<params>[?,#].*)?")
    match = reg_url.match(str_url)
    return match

#
# @desc helper function for build_url_string. takes and path as a string and returns the parent path.
# @param path - path as a string (ex. /test/testy)
# @return new_path - parent path as a string (ex. /test)
#
def move_up_path(path):
    path_array = re.split(r"(/[^/]*)", path)
    new_path = ''
    for directory in path_array[:-2:]:
        new_path += directory
    return new_path

#
# @desc builds url string for cases where a partial url is given and returns it.
# @param str_url - url string a html page (ex. ../test/testy)
# @param original_url - object of url requested to get the html page (ex. https://test.com/about)
# @return new_url - the url object built by combining str_url and original_url (ex. https:/test.com/test/testy
#
def build_url_string(str_url, original_url):
    new_url = original_url.service + original_url.domain + original_url.port
    original_path = original_url.path

    # if the original url is a file use the parent path (ex. /test/test.html -> /test/)
    if '.' in original_path:
        original_path = move_up_path(original_url.path)

    if str_url and len(str_url) > 1:
        if str_url[0] == '.':
            # handle urls like ./
            if str_url[1] == '/':
                new_url = new_url + original_path + str_url[2::]
                return new_url
            # handle urls like ../
            elif str_url[1] == '.':
                new_url = new_url + move_up_path(original_url.path) + str_url[2::]

        # handle urls like /test
        elif str_url[0] == '/':
            new_url = new_url + str_url
            return new_url

        # handle urls like #test
        elif str_url[0] == '#':
            new_url = new_url + original_path + original_url.params + str_url
        else:
            if ':' not in str_url:
                if len(original_path) > 1:
                    if original_path[-1] == '/':
                        new_url = new_url + original_path + str_url
                else:
                    new_url = new_url + original_path + '/' + str_url
    return new_url

#
# @desc finds all links on a given html page and returns a list of Url objects to visit next
# @param page - html string
# @param path - the request url that produced the html page
# @return paths - list of Url objects to visit next
#
def find_links(page, path):
    soup = BeautifulSoup(page, 'html.parser')
    links = soup.findAll('a')
    paths = []
    for link in links:
        # ignor <a> flags with no 'href' attribute
        try:
            url_str = link['href']
        except KeyError:
            continue

        # if the href is a shortened url, build a full url
        if '://' not in url_str:
            new_url = Url(build_url_string(url_str, path))
        else:
            new_url = Url(url_str)

        # Need to handle empty hrefs
        if new_url is None:
            continue

        # check if the new url is on an acceptable domain and add it to the necessary lists
        if ARGS.check_all_urls:
            new_url.status = check_url(new_url)

        if ORIGINAL_DOMAIN == new_url.domain:
            if new_url not in URLS:
                paths.append(new_url)
                URLS.append(new_url)
                print_new_url(new_url)
        elif ORIGINAL_DOMAIN in new_url.domain and ARGS.allow_subdomains:
            if new_url not in URLS:
                paths.append(new_url)
                URLS.append(new_url)
                print_new_url(new_url)
            if new_url.domain not in DOMAINS:
                DOMAINS.append(new_url.domain)
    return paths


#
# @desc recursive function to spider the web address and add found urls to global list.
# @param url - starting url as Url object
# @param depth - integer for maximum recursive depth
#
def spider(url, depth):
    print_update('Depth: ' + str(depth) + ' Guessing: ' + str(url))
    brute_force(url, depth)
    print_update('Depth: ' + str(depth) + ' Requesting: ' + str(url))
    r = requests.get(str(url)) # , allow_redirects=False)
    paths = find_links(r.text, url)

    # exit conditions for recursion
    if depth >= DEPTH or len(paths) == 0:
        return

    for path in paths:
        spider(path, depth+1)


#
# @desc requests url and looks for a response other than 404
# @param test_url - url to test
# @return True - if url does not produce 404
#
def check_url(test_url):
    r = requests.get(test_url.strip('\n')) # ,allow_redirects=False)
    return r.status_code

#
# @desc loads words from wordlist file
#
def parse_wordlist():
    global WORDLIST, ARGS
    with open(ARGS.wordlist, 'r') as word_file:
        for word in word_file:
            WORDLIST.append(word)

#
# @desc use directory guessing on a given url and adds found urls to necessary lists
# @param url - url to guess from
# @param wordlist - wordlist of paths to guess
# @param depth - current depth in the spidering process
#
def brute_force(url, depth):
    if '.' not in url.path:
        index = 0
        for word in WORDLIST:
            index += 1
            # figure out if a / needs to be added or taken away
            if len(url.path) != 0 and len(word) != 0:
                if url.path[-1] == '/' and word[0] == '/':
                    word = word[1::]
                elif url.path[-1] != '/' and word[0] != '/':
                    word = '/' + word
            elif len(url.path) == 0:
                word = '/' + word

            test_url = url.service + url.domain + url.port + url.path + word
            if test_url not in URLS:
                if check_url(test_url) != 404:
                    new_url = Url(test_url)
                    #print(new_url,test_url,check_url(test_url))
                    print_update('Depth: ' + str(depth) + ' Guessing: ' + str(index) + '/' + str(len(WORDLIST)) + '  ' + str(url))
                    URLS.append(new_url)
                    print_new_url(new_url)

#
# @main
# @desc processes arguments and kicks off spidering. Once done, prints final statistics.
#
def main():
    global ARGS, ORIGINAL_DOMAIN, DEPTH
    ARGS = parseargs()
    if ARGS.depth:
        DEPTH = ARGS.depth
    if not ARGS.quiet:
        print_banner()

    if ARGS.wordlist:
        parse_wordlist()
    original_url = Url(ARGS.url)
    ORIGINAL_DOMAIN = original_url.domain
    DOMAINS.append(ORIGINAL_DOMAIN)

    spider(original_url, 0)
    print_final_stats()


main()
