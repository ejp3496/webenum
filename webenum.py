import requests
import argparse
from bs4 import BeautifulSoup
import re
from treelib import Node, Tree

banners = "\n" \
        "| |"+" "*5+"/ / "+"_"*4+"/ __ )___  ____  __  "+"_"*6+" ___\n" \
        "| | /| / / __/ / __  / _ \\/ __ \\/ / / / __ `__ \\\n" \
        "| |/ |/ / /___/ /_/ /  __/ / / / /_/ / / / / / /\n|__/|__/_____/_____/\\___/_/ /_/\\__,_/_/ /_/ /_/\n" \
        ""+"="*50+"\n"+" "*25+"="*25+"\n"+" "*38+"="*12
trees = {}
args: any

def banner():
    print(banners)


def parseargs():
    parser = argparse.ArgumentParser(description='Enumerate web directories using spidering and directory guessing.')
    parser.add_argument('-url', '-u', help='url to crawl', required=True)
    parser.add_argument('--quiet', '-q',help="Don't display banner", action='store_true')
    parser.add_argument('--allow-subdomains', '-s',help="allow scanner to request subdomains", action='store_true')
    args = parser.parse_args()
    return args


def listurls():
    urllist = []
    for dom, tree in trees.items():
        for url in tree.paths_to_leaves():
            listitem = ''
            for dir in url:
                listitem += dir
            urllist.append(dom[0]+dom[1]+listitem+dom[2])
    return sorted(urllist)


def parseurl(strurl):
    regurl = re.compile("^(?P<service>https?:\/\/)?(?P<domain>[a-zA-Z0-9.]*)?(?P<port>:\d{1,4})?(?P<path>[\/.%_\-a-zA-Z0-9]*)?(?P<params>[?,#].*)?")
    match = regurl.match(strurl)
    return match

def createdom(service,domain,port):
    if port is None:
        port = ''
    return (service,domain,port)


def addpathtotree(path,dom):
    pathar = re.split(r"(\/[^\/]*)",path)
    while '' in pathar:
        pathar.remove('')
    parent = trees[dom].root
    if parent and parent[-1] == '/':
        pathar[0] = pathar[0][1::]
    if len(pathar) == 0:
        trees[dom].create_node('', '')
    for dir in pathar:
        if trees[dom].contains(dir):
            parent = trees[dom][dir]
        else:
            newparent = trees[dom].create_node(dir, dir, parent=parent)
            parent = newparent


def findpaths(page,dom, path):
    soup = BeautifulSoup(page, 'html.parser')
    links = soup.findAll('a')
    paths=[]
    for link in links:
        try:
            urlstr = link['href']
            print('ORIGINAL:',link)
        except KeyError as e:
            continue
        if '://' not in urlstr:
            if urlstr[0] == '/':
                urlstr = urlstr[1::]
            if '?' in urlstr:
                urlstr = urlstr.split('?')[0]
            if '#' in urlstr:
                urlstr = urlstr.split('#')[0]
            urlstr = parseurl(path).group('path') + '/' + urlstr
            print('short url:', dom[0]+dom[1]+dom[2]+urlstr)
            addpathtotree(urlstr, dom)
            paths.append(dom[0]+dom[1]+dom[2]+urlstr)
        else:
            regurl = parseurl(urlstr)

            if regurl is None:
                continue
            if dom[1] == regurl.group('domain'):
                addpathtotree(regurl.group('path'), dom)
                paths.append(dom[0]+dom[1]+dom[2]+urlstr)
                print('LONGURL', dom[0] + dom[1] + dom[2] + regurl.group('path'))
            elif dom[1] in regurl.group('domain') and args.allow_subdomains:
                newdom = createdom(regurl.group('service'), regurl.group('domain'), regurl.group('port'))
                trees[newdom] = Tree()
                tmppath = regurl.group('path')
                if tmppath is None:
                    tmppath = ''
                addpathtotree(tmppath, newdom)
                paths.append(newdom[0]+newdom[1]+newdom[2]+regurl.group('path'))
                print('LONGURL_NEW_DOMAIN', newdom[0] + newdom[1] + newdom[2] + regurl.group('path'))
    return paths


def main():
    global trees, args
    args = parseargs()
    print(args)
    if not args.quiet:
        banner()

    regurl = parseurl(args.url)

    dom = createdom(regurl.group('service'), regurl.group('domain'), regurl.group('port'))

    root = regurl.group('path')
    if root == '':
        root = ''+root
    trees = {dom: Tree()}
    trees[dom].create_node(root, root)
    r = requests.get(args.url)
    paths = findpaths(r.text, dom, args.url)

    for path in paths:
        print('requesting:', path)
        pathobj=parseurl(path)
        r = requests.get(path)

        dom = createdom(pathobj.group('service'), pathobj.group('domain'), pathobj.group('port'))
        newpaths = findpaths(r.text, dom, path)

    for dom, tree in trees.items():
        print(dom[0]+dom[1]+dom[2])
        print(tree)

    count=0
    for url in listurls():
        count += 1
        print(url+'\n')
    print(str(count)+' URLs')


main()
