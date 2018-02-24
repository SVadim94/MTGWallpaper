#!/usr/bin/env python3
import enum
import logging
import os
import random
import sys
import time
from argparse import ArgumentParser
from subprocess import check_call

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())

class Wallpaper:
    def __init__(self, html_description):
        self.name = html_description.find('h3').getText().strip()
        self.expansion = html_description.find('span').getText().replace('(', '').replace(')', '').strip()
        self.author = html_description.find('p', class_="author").getText()[3:]

        self.size_links_dict = dict()

        for link in html_description.find_all('a', class_=""):
            size = link.getText()
            link = link.attrs['download']
            self.size_links_dict[size] = link

            logger.debug("Parsing wallpaper: [%s] %s %s", self.expansion, self.name, size)

class Gatherer:
    allowed_filters = ["title", "ASC", "DESC"]

    def __init__(self, path="./"):
        self.session = requests.Session()
        self.parser = None
        self.size_wallpapers_dict = {}
        self.path = path

    def make_request(self, page, expansion="", title="", filter_by="title"):
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

        return response

    def parse_response(self, response):
        result = []

        self.parser = BeautifulSoup(response.json()["data"], 'html.parser')

        for html_description in self.parser.find_all('div', class_="wrap"):
            wallpaper = Wallpaper(html_description)
            logger.debug("[%s] %s was parsed successfully", wallpaper.expansion, wallpaper.name)

            result.append(wallpaper)

        return result

    def download_wallpaper(self, wallpaper, size):
        if size not in wallpaper.size_links_dict:
            new_size = self.get_biggest_size(wallpaper)
            logger.warning("No wallpaper of size %s. Falling back to %s", size, new_size)
            size = new_size

        logger.info("Fetching %s from %s" % (wallpaper.name, wallpaper.size_links_dict[size]))
        resp = self.session.get(wallpaper.size_links_dict[size], stream=True)
        filename = os.path.join(self.path, "[%s] %s.jpg" % (wallpaper.expansion, wallpaper.name))

        with open(filename, 'wb') as f:
            for chunk in resp.iter_content(1024 * 1024):
                f.write(chunk)

        logger.info("Saved %s to %s" % (wallpaper.name, filename))
        print("Wallpaper was successfully downloaded to %s" % filename)

        return filename

    def get_biggest_size(self, wallpaper):
        logger.debug("[%s] %s: choosing biggest wallpaper", wallpaper.expansion, wallpaper.name)
        biggest_cl, biggest_size = 0, None

        for size, link in wallpaper.size_links_dict.items():
            response = self.session.head(link)

            if int(response.headers["Content-Length"]) > biggest_cl:
                biggest_size = size

        logger.debug("[%s] %s: size '%s' was chosen", wallpaper.expansion, wallpaper.name, biggest_size)
        return biggest_size

    def choose_random_wallpaper_by_size(self, wallpapers, size="2560x1600"):
        try:
            wallpaper = random.choice([wp for wp in wallpapers if size in wp.size_links_dict.keys()])
        except IndexError:
            raise Exception("No wallpaper of size %s" % size)

        return wallpaper

    def download_pack(self, name="", expansion="", size="2560x1600"):
        page = 0

        while True:
            logger.debug("Fetching page %d", page)
            response = self.make_request(page, expansion=expansion, title=name)
            wallpapers = self.parse_response(response)

            # Downloading
            for wallpaper in wallpapers:
                logger.debug("Downloading [%s] %s", wallpaper.expansion, wallpaper.name)
                self.download_wallpaper(wallpaper, size)

            if response.json()["displaySeeMore"] == 0:
                break

            page += 1

    def how_many_pages(self, name="", expansion="", inital=150):
        low, high = 0, inital

        while low <= high:
            logger.debug("bin_search: low = %s, high = %s", low, high)
            guess = (high + low) // 2
            response = self.make_request(page=guess, expansion=expansion, title=name).json()

            if response["data"] != "" and response["displaySeeMore"] == 0:
                self.number_of_pages = response["page"]
                return
            elif response["displaySeeMore"] == 1:
                low = guess + 1
            else:
                high = guess

        raise Exception("Your binary search sucks: %d %d" % (low, high))

    def get_random_wallpaper(self, name="", expansion="", size="2560x1600"):
        self.how_many_pages(name=name, expansion=expansion)
        page = random.randrange(self.number_of_pages)
        logger.debug("Chosen page = %d / %d" , page + 1, self.number_of_pages)
        response = self.make_request(page, expansion=expansion, title=name)
        wallpapers = self.parse_response(response)
        wallpaper = self.choose_random_wallpaper_by_size(wallpapers, size)

        return self.download_wallpaper(wallpaper, size)


def main(args):
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

    if args.download_pack:
        if args.expansion == "" and args.name == "":
            logger.warning(
                "You have not specified expansion. That means you will end up downloading all MTG wallpapers. "\
                "This will take a lot of time and probably not want you want. You have got 10 seconds to cancel (CTRL+C)"
            )
        time.sleep(10)
        g.download_pack(args.name, args.expansion, args.size)
        exit(0)

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
    argparser.add_argument("-d", "--download-pack", action="store_true", help="Download all wallpapers from specific expansion and/or with specific word in title (specify expansion name and title with -e / -n)")

    args = argparser.parse_args()

    main(args)
