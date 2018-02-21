#!/usr/bin/env python3
import enum
import logging
import os
import random
import sys
from argparse import ArgumentParser
from subprocess import check_call

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())

class Wallpaper:
    def __init__(self, tag):
        self.name = tag.find('h3').getText().strip()
        self.expansion = tag.find('span').getText()
        self.author = tag.find('p', class_="author").getText()[3:]

        self.links = dict()

        for link in tag.find_all('a', class_=""):
            k = link.getText()
            v = link.attrs['download']
            self.links[k] = v

class Gatherer:
    """Gatherer"""
    allowed_filters = ["title", "ASC", "DESC"]

    def __init__(self, path="./"):
        self.session = requests.Session()
        self.parser = None
        self.wallpapers = {}
        self.path = path

    def make_request(self, page, expansion="", title="", filter_by="title", merge=True):
        if filter_by not in self.allowed_filters:
            raise Exception("Wrong filter type. Should be one of the \"%s\"" % ",".join(self.allowed_filters))

        paramsGet = {
            "filter_by": filter_by,
            "expansion": expansion,
            "artist": "-1",
            "title": title,
            "page": page
        }

        response = self.session.get("https://magic.wizards.com/en/see-more-wallpaper", params=paramsGet)

        if merge:
            self.merge(response)

        return response

    def merge(self, response):
        self.parser = BeautifulSoup(response.json()["data"], 'html.parser')

        for tag in self.parser.find_all('div', class_="wrap"):
            wallpaper = Wallpaper(tag)

            for size in wallpaper.links.keys():
                s = self.wallpapers.setdefault(size, [])
                s.append(wallpaper)

    def download_wallpaper(self, wallpaper, size):
        logger.info("Getting %s from %s" % (wallpaper.name, wallpaper.links[size]))

        resp = self.session.get(wallpaper.links[size], stream=True)
        filename = os.path.join(self.path, "%s %s.jpg" % (wallpaper.expansion, wallpaper.name))

        with open(filename, 'wb') as f:
            for chunk in resp.iter_content(1024 * 1024):
                f.write(chunk)

        logger.info("Saved %s to %s" % (wallpaper.name, filename))
        print("Wallpaper was successfully downloaded to %s" % filename)
        return filename

    def choose_random_wallpaper_by_size(self, size="2560x1600"):
        try:
            wallpaper = random.choice(self.wallpapers[size])
        except KeyError:
            raise Exception("No wallpaper of size %s" % size)

        return wallpaper

    def download_pack(self, expansion):
        pass

    def how_many_pages(self, name="", expansion="", inital=150):
        low, high = 0, inital

        while low <= high:
            logger.debug("bin_search: low = %s, high = %s", low, high)
            guess = (high + low) // 2
            req = self.make_request(page=guess, expansion=expansion, title=name, merge=False).json()

            if req["data"] != "" and req["displaySeeMore"] == 0:
                self.number_of_pages = req["page"]
                return
            elif req["displaySeeMore"] == 1:
                low = guess + 1
            else:
                high = guess

        raise Exception("Your binary search sucks: %d %d" % (low, high))

    def get_random_wallpaper(self, name="", expansion="", size="2560x1600"):
        self.how_many_pages(name=name, expansion=expansion)
        page = random.randrange(self.number_of_pages)
        logger.debug("Chosen page = %d / %d" , page + 1, self.number_of_pages)
        self.make_request(page, expansion=expansion, title=name)
        wallpaper = self.choose_random_wallpaper_by_size(size)

        return self.download_wallpaper(wallpaper, size)

if __name__ == "__main__":
    argparser = ArgumentParser(
        prog=sys.argv[0],
        description="Get your wallpaper!"
    )

    argparser.add_argument("-n", "--name", default="", help="Only get wallpapers that contains `name` in its title")
    argparser.add_argument("-e", "--expansion", default="", help="Only get wallpapers from specific expansion")
    argparser.add_argument("-s", "--size", default="2560x1600", help="Size of the wallpaper. Default is 2560x1600. Be prepare to not have your resolution at all :(")
    argparser.add_argument("-p", "--path", default="./", help="Path to download wallpaper, e.g. /home/user/wallpapers/")
    argparser.add_argument("-v", "--verbose", action="store_true", help="Be verbose")
    argparser.add_argument("-w", "--wallpaper", action="store_true", help="Mac only. Set downloaded wallpaper as desktop picture")
    argparser.add_argument("-l", "--log-file", default=None, help="Log file to store verbose output. Useful for cron")

    args = argparser.parse_args()

    # Logging
    if args.log_file:
        ch = logging.FileHandler(args.log_file)
    else:
        ch = logging.StreamHandler()
    ch.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    ch.setLevel(logging.DEBUG)

    if args.verbose:
        logger.setLevel(logging.DEBUG)
    else:
        logger.setLevel(logging.WARNING)

    for handler in logger.handlers[:]:
        logger.removeHandler(handler)

    logger.addHandler(ch)

    g = Gatherer(args.path)
    filename = g.get_random_wallpaper(name=args.name, expansion=args.expansion, size=args.size)

    if args.wallpaper:
        shitty_escaper = lambda x: x.replace('\\', '\\\\').replace('"', '\\"')
        cmd = [
            "osascript",
            "-e",
            'tell application "Finder" to set desktop picture to POSIX file "%s"' % shitty_escaper(os.path.abspath(filename))
        ]
        logger.debug(cmd)
        check_call(cmd)
