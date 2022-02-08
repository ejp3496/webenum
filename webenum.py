#!/usr/bin/env python3.8
#
#                                           WEBenum
#
# @desc a tool to enumerator web directories using both recursive spidering and directory guessing.
#
# @author Evan Palmiotti
# @required requests, argparse, bs4, re, sys
# @todo:
#       add connection check at the beginning to find the not found code
#       graceful shutdown after ctrlc
#       make -b arg contingent on -w
#       file output for domains
#       add file size in list
########################################################################################################
import os
import requests
import argparse
from bs4 import BeautifulSoup
import re
from sys import stdout
from time import time
import colorama
import threading

BANNER = "\n" \
        "\033[34m|‾|" + " " * 5 + "/‾/ \033[31m" + "_" * 4 + "/\033[33m __ )\033[34m___  \033[32m____  \033[34m__  __\033[31m____ ___\n" \
        "\033[34m| | /| / /\033[31m __/\033[33m / __  /\033[34m _ \\\033[32m/ __ \\\033[34m/ / / / \033[31m__ `__ \\\n" \
        "\033[34m| |/ |/ / \033[31m/___/\033[33m /_/ /\033[34m  __/\033[32m / / /\033[34m /_/ / \033[31m/"+" /" * 4 + "\n" \
        "\033[34m|__/|__/\033[31m"+"_" * 5 + "/\033[33m"+"_" * 5 + "" \
        "/\033[34m\\___/\033[32m_/ /_/\033[34m\\__,_/\033[31m_/ /_/ /_/\n" \
        "" + "=" * 50 + "\n" + " " * 25 + "\033[33m=" * 25 + "\n" + " " * 38 + "\033[32m=" * 12  # Ascii art banner

URLS = []                # found urls (updated by script)
DOMAINS = []             # found domains (updated by script)
WORDLIST = []              # word list read from file
ARGS: any                # stored arguments (updated by script)
ORIGINAL_DOMAIN = ''     # Original Domain (updated by script)
THREAD_LOCK = threading.Lock()
START = time()

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

class BruteForceThread(threading.Thread):
    def __init__(self, url, word, found_urls, depth):
        threading.Thread.__init__(self)
        self.url = url
        self.word = word
        self.found_urls = found_urls
        self.depth = depth
        self.exc = None

    def run(self):
        try:
            brute_force_thread(self.depth, self.url, self.word, self.found_urls)
        except Exception as e:
            self.exc = e

    def join(self):
        threading.Thread.join(self)
        if self.exc:
            raise self.exc


def brute_force_thread(depth, url, word, found_urls):
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
        THREAD_LOCK.acquire()
        THREAD_LOCK.release()
        status = check_url(test_url)
        if status and status != 404:
            new_url = Url(test_url)
            new_url.status = status
            THREAD_LOCK.acquire()
            URLS.append(new_url)
            found_urls.append(new_url)
            print_update(depth, url, new_url, 0)
            THREAD_LOCK.release()

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
    parser.add_argument('--allow-subdomains', '-s', help="allow scanner to request subdomains", action='store_true',
                        default=False)
    parser.add_argument('--depth', '-d', help="depth of directory spidering (default=3) (0=unlimited)", type=int,
                        default=3)
    parser.add_argument('--brute-force-depth', '-b', help="maximum spidering depth to do brute force directory guessing"
                        "(default=0) (0=same as spider depth)", type=int, default=0)
    parser.add_argument('--wordlist', '-w', help="wordlist to use for directory guessing")
    parser.add_argument('--check-all-urls', '-c', help="Don't check URLs found in HTML pages for status codes",
                        action='store_true')
    parser.add_argument('--timeout', help='timeout time for requests.', default=10)
    parser.add_argument('--out-file', '-o', help='write results to specified file', default=None)
    parser.add_argument('--threads', '-t', help='Number of threads to run', default=3)
    return parser.parse_args()

#
# @desc Prints pretty ascii art banner
#
def print_banner():
    print(BANNER)
    print('\n'+'='*75)
    for arg_name, arg_value in vars(ARGS).items():
        print('%-20s %s' % (arg_name+':', arg_value))
    print('='*75+'\n\n')

def pad_or_trim(string):
    max_width = os.get_terminal_size().columns
    length = len(string)
    if length != max_width:
        if length < max_width:
            padding = max_width - length
            string = string + ' '*padding
        else:
            string = string[0:max_width-length-3:] + '...'
    return string

#
# @desc Prints update to bottom of the screen while running
# @param update - string to print
#
def print_update(depth, url, new_url, mode):
    if mode == 1:
        update = '\r%.2f | Depth: %2i | Spidering %-20s' % (time()-START, depth, url)
    else:
        update = '\r%.2f | Depth: %2i | Brute Forcing %-20s' % (time()-START, depth, url)

    if new_url is not None:
        if new_url.status is not None:
            url_string = "\r%-100s (status:%3s)" % (str(new_url), new_url.status)
            stdout.write(pad_or_trim(url_string)+'\n')
            stdout.flush()
        else:
            url_string = "\r%-100s" % (str(new_url))
            stdout.write(pad_or_trim(url_string)+'\n')
            stdout.flush()
        stdout.write(pad_or_trim(update))
        stdout.flush()
    else:
        stdout.write(pad_or_trim(update))
        stdout.flush()

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
def find_links(page, path, depth):
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
            if new_url.status:
                new_url.status = check_url(new_url)
            else:
                new_url.status = 'Timeout'

        if ORIGINAL_DOMAIN in new_url.domain and ARGS.allow_subdomains:
            if new_url.domain not in DOMAINS:
                DOMAINS.append(new_url.domain)
            if new_url not in URLS:
                paths.append(new_url)
                URLS.append(new_url)
                print_update(depth, path, new_url, 1)

    return paths

def request(url):
    r = None
    try:
        r = requests.get(str(url).strip('\n'), timeout=ARGS.timeout)
    except Exception as e:
        if str(url) == ARGS.url:
            exit_with_error('Error sending request: ' + str(e))
    return r

#
# @desc recursive function to spider the web address and add found urls to global list.
# @param url - starting url as Url object
# @param depth - integer for maximum recursive depth
#
def spider(url, depth):
    found_urls = []
    print_update(depth, url, None, 1)
    try:
        r = request(url)
    except Exception as e:
        exit_with_error("Error requesting URL: "+str(e))
    if ARGS.brute_force_depth == 0 or depth <= ARGS.brute_force_depth:
        found_urls = brute_force(url, depth)
    paths = []
    if r:
        paths = find_links(r.text, url, depth)
        paths = paths + found_urls
    # exit conditions for recursion
    if depth >= ARGS.depth > 0 or len(paths) == 0:
        return

    for path in paths:
        spider(path, depth+1)

#
# @desc requests url and looks for a response other than 404
# @param test_url - url to test
# @return True - if url does not produce 404
#
def check_url(test_url):
    r = request(test_url)
    if r:
        return r.status_code
    return None

def exit_with_error(error):
    print('\r\033[31m '+error)
    exit(0)

#
# @desc loads words from wordlist file
#
def parse_wordlist():
    global WORDLIST, ARGS
    try:
        with open(ARGS.wordlist, 'r') as word_file:
            for word in word_file:
                WORDLIST.append(word)
    except Exception as e:
        exit_with_error('Error reading wordlist file ' + str(e))


#
# @desc use directory guessing on a given url and adds found urls to necessary lists
# @param url - url to guess from
# @param depth - current depth in the spidering process
#
def brute_force(url, depth):
    found_urls = []
    if '.' not in url.path:
        index = 0
        while index < len(WORDLIST):
            thread_list = []
            thread_number = int(ARGS.threads)
            words_left = len(WORDLIST) - index
            if words_left < thread_number:
                thread_number = words_left

            for i in range(0, thread_number):
                thread_list.append(BruteForceThread(url, WORDLIST[index].strip('\n'), found_urls, depth))
                index += 1
                thread_list[i].start()

            for thread in thread_list:
                try:
                    thread.join()
                except Exception as e:
                    exit_with_error('Error joining threads: '+str(e))
    return found_urls

#
# @main
# @desc processes arguments and kicks off spidering. Once done, prints final statistics.
#
def main():
    global ARGS, ORIGINAL_DOMAIN
    colorama.init(autoreset=True)
    ARGS = parseargs()
    if not ARGS.quiet:
        print_banner()

    if ARGS.wordlist:
        parse_wordlist()
    original_url = Url(ARGS.url)
    ORIGINAL_DOMAIN = original_url.domain
    DOMAINS.append(ORIGINAL_DOMAIN)

    spider(original_url, 0)
    print_final_stats()

    if ARGS.out_file:
        try:
            with open(ARGS.out_file, 'w') as out_file:
                index = 0
                for url in URLS:
                    index += 1
                    if index >= len(URLS):
                        out_file.write(str(url))
                    else:
                        out_file.write(str(url)+'\n')
        except Exception as e:
            exit_with_error('Error writing to file ' + str(e))


main()