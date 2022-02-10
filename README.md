<pre>|‾|     /‾/ ____/ __ )___  ____  __  ______ ___
| | /| / / __/ / __  / _ \/ __ \/ / / / __ `__ \
| |/ |/ / /___/ /_/ /  __/ / / / /_/ / / / / / /
|__/|__/_____/_____/\___/_/ /_/\__,_/_/ /_/ /_/</pre>

## Description
Web enumerator similar to dirbuster or gobuster but utilizes brute forcing AND spidering to get a more complete picture of a web surface. Git project includes a small word list named ```wordlist.txt```
  - No clunky GUI
  - Highly customizable
  - fast

## Installation
```bash
git clone https://github.com/ejp3496/webenum.git
cd webenum
pip install -r requests.txt
python3 webenum.py -h
```

## Usage
### Basic Example
```bash
python3 webenum.py -u http://127.0.0.1:8000 -w wordlist.txt
```
![image](https://user-images.githubusercontent.com/43967089/153477780-3d23ed82-2b73-4138-b66f-a54e69a72b80.png)

### Options
```
options:
  -h, --help            show this help message and exit
  -url URL, -u URL      Url to crawl
  --quiet, -q           Only print found urls
  --allow-subdomains, -s
                        Allow scanner to request subdomains
  --depth DEPTH, -d DEPTH
                        Depth of directory spidering (default=3) (0=unlimited)
  --brute-force-depth BRUTE_FORCE_DEPTH, -b BRUTE_FORCE_DEPTH
                        Maximum spidering depth to do brute force directory guessing(default=0) (0=same as spider depth)
  --wordlist WORDLIST, -w WORDLIST
                        Wordlist to use for directory guessing
  --check-all-urls, -c  Don't check URLs found in HTML pages for status codes
  --timeout TIMEOUT     Timeout time for requests.
  --out-file OUT_FILE, -o OUT_FILE
                        Write results to specified file
  --threads THREADS, -t THREADS
                        Number of threads to run
  --no-verify-ssl, -v   Don't verify SSL
  --out-file-domains OUT_FILE_DOMAINS, -Od OUT_FILE_DOMAINS
                        Write domains to a file
  --follow-redirects, -r
                        Follow HTTP redirects

Examples:
        webenum.py -h http://test.com -d 4                                          --Enumerate using only spirdering to depth of 4
        webenum.py -h http://test.com -w wordlist.txt                               --Enumerate using spidering and brute forcing to level 3
        webenum.py -h https://test.com -w wordlist -d 5 -b 3                        --Enumerate using spidering to level 5 and brute forcing to level 3
        webenum.py -h https://test.com -s -w wordlist -o urls.txt -Od domanis.txt   --Enumerate using both methods including subdomains and saving both found urls and found subdomains to files
```
