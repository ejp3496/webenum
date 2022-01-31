import requests
import argparse


def banner():
    with open('resources/banner.txt','r') as file:
        for f in file:
            print(f)

def main():
    parser = argparse.ArgumentParser(description='Enumerate web directories uwing spidering and directory guessing.')
    parser.add_argument('--test','-t',help='testing',action='store_true')
    args=parser.parse_args()
    
    banner()

    print(args)


main()
