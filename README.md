# MTGGatherer
## Description

This python script allows you to download random MTG wallpaper. You can optionally specify name, expanstion or size (default is 2560x1600).

## Usage
```
usage: gatherer.py [-h] [-n NAME] [-e EXPANSION] [-s SIZE] [-p PATH] [-v] [-w]
                   [-l LOG_FILE]

Get your wallpaper!

optional arguments:
  -h, --help            show this help message and exit
  -n NAME, --name NAME  Only get wallpapers that contains `name` in its title
  -e EXPANSION, --expansion EXPANSION
                        Only get wallpapers from specific expansion
  -s SIZE, --size SIZE  Size of the wallpaper. Default is 2560x1600. Be
                        prepare to not have your resolution at all :(
  -p PATH, --path PATH  Path to download wallpaper, e.g.
                        /home/user/wallpapers/
  -v, --verbose         Be verbose
  -w, --wallpaper       Mac only. Set downloaded wallpaper as desktop picture
  -l LOG_FILE, --log-file LOG_FILE
                        Log file to store verbose output. Useful for cron
```