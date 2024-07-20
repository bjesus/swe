#!/usr/bin/env python

import os
import argparse
import requests
import xml.etree.ElementTree as ET

from swe.sounds import play_word
from swe.common import xml_file
from swe.cli import print_translations


if not os.path.exists(xml_file):
    print("Downloading dictionary... this will only happen once.")
    url = "https://folkets-lexikon.csc.kth.se/folkets/folkets_sv_en_public.xml"
    os.makedirs(os.path.dirname(xml_file), exist_ok=True)
    response = requests.get(url)
    with open(xml_file, "wb") as f:
        f.write(response.content)
    print("Done.")


def search_words(xml_file, search_string):
    tree = ET.parse(xml_file)
    root = tree.getroot()
    result = [
        word.attrib["value"]
        for word in root.findall(".//word[@value]")
        if search_string in word.attrib["value"]
    ]
    return result


def main():
    parser = argparse.ArgumentParser(
        description="Search the Folkets Lexikon XML file for words containing a given string. Run without arguments for interactive interface."
    )
    parser.add_argument(
        "word", nargs="?", default="", help="Word to get definition for"
    )
    parser.add_argument(
        "-s",
        "--search",
        dest="search_string",
        required=False,
        help="Search words in the dictionary",
    )

    parser.add_argument(
        "-p",
        "--play",
        dest="play_word",
        required=False,
        help="Play a word",
    )
    args = parser.parse_args()

    if args.search_string:
        result = search_words(xml_file, args.search_string)
        print("\n".join(result))
    elif args.play_word:
        play_word(args.play_word)
    elif args.word:
        print_translations(xml_file, args.word)
    else:
        from swe.interactive import SvenskaApp

        app = SvenskaApp()
        app.run()
