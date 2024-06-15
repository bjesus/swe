#!/usr/bin/env python3

import os
import argparse
import xml.etree.ElementTree as ET
import html
import tempfile
from pathlib import Path

xml_file = os.path.join(Path.home(), ".local", "share", "swe", 'folkets_sv_en_public.xml')
last_word_file = os.path.join(tempfile.gettempdir(), 'swe-last-word.txt')

if not os.path.exists(xml_file):
    print("Before using swe, you need to download the latest dictionary file.\n\nDownload it from https://folkets-lexikon.csc.kth.se/folkets/folkets_sv_en_public.xml \nThe file is expected at", xml_file)
    exit(1)

def encode_iso(word):
   iso_mapping = {'å': '0345', 'ä': '0344', 'ö': '0366'}
   return ''.join(iso_mapping.get(char, char) for char in word)

def play_word_sound(word):
    iso_word = encode_iso(word)
    sound_url = f'http://lexin.nada.kth.se/sound/{iso_word}.mp3'
    os.environ['MPLAYER_VERBOSE'] = "-4"
    os.system(f'mplayer -quiet {sound_url}')

def search_words(xml_file, search_string):
    tree = ET.parse(xml_file)
    root = tree.getroot()
    result = [word.attrib['value'] for word in root.findall('.//word[@value]') if search_string in word.attrib['value']]
    return result

def print_header(text):
    print(f"\n\033[3m{text}\033[0m")


def print_translations(xml_file, search_word):
    found_word = False
    tree = ET.parse(xml_file)
    root = tree.getroot()
    for word in root.findall('.//word[@value]'):
        word_value = word.attrib['value']
        inflections = word.findall('./paradigm/inflection[@value]')
        
        if word_value == search_word or any(inflection.attrib['value'] == search_word for inflection in inflections):
            found_word = True
            comment = word.get('comment', '')
            print(word_value, end='')
            with open(last_word_file, 'w') as f:
                f.write(word_value)
            if comment:
                print(f' ({html.unescape(comment)})')
            else:
                print()
            if inflections:
                print(", ".join(inflection.attrib['value'] for inflection in inflections))
            translations = word.findall('./translation[@value]')
            if translations:
                print_header("Translations")
                for translation in translations:
                    comment = translation.get('comment', '')
                    print(f'- \033[1m{html.unescape(translation.attrib["value"])}\033[0m', end='')
                    if comment:
                        print(f' ({html.unescape(comment)})')
                    else:
                        print()

            synonyms = word.findall('./synonym[@value]')
            if synonyms:
                print_header("Synonyms")
                for synonym in synonyms:
                    level = synonym.get('level', '')
                    print(f'- {html.unescape(synonym.attrib["value"])}', end='')
                    if level:
                        print(f' ({html.unescape(level)})')
                    else:
                        print()

            examples = word.findall('.//example[@value]')
            if examples:
                print_header("Examples")
                for example in examples:
                    example_translation = example.find('.//translation[@value]')
                    if example_translation is not None:
                        print(f'- {html.unescape(example.attrib["value"])}: {html.unescape(example_translation.attrib["value"])}')

            related = word.findall('./related[@value]')
            if related:
                print_header("Related")
                for rel in related:
                    rel_type = rel.get('type', '')
                    rel_translation = rel.find('./translation[@value]')
                    if rel_translation is not None:
                        print(f'- {html.unescape(rel.attrib["value"])} ({html.unescape(rel_type)}): {html.unescape(rel_translation.attrib["value"])}')

            idioms = word.findall('./idiom[@value]')
            if idioms:
                print_header("Idioms")
                for idiom in idioms:
                    idiom_translation = idiom.find('./translation[@value]')
                    if idiom_translation is not None:
                        print(f'- {html.unescape(idiom.attrib["value"])}: {html.unescape(idiom_translation.attrib["value"])}')

            return
    if not found_word:
        print(f'Word "{search_word}" not found in the XML file.')

def main():
    parser = argparse.ArgumentParser(description='Search XML file for words containing a given string.')
    parser.add_argument('word', nargs='?', default="", help='Word to get definition for')
    parser.add_argument('-s', '--search', dest='search_string', required=False, help='String to search for')
    args = parser.parse_args()

    if args.search_string:
        result = search_words(xml_file, args.search_string)
        print("\n".join(result))
    elif args.word:
        print_translations(xml_file, args.word)
    else:

        if os.path.exists(last_word_file):
            with open(last_word_file, 'r') as f:
                last_searched_word = f.read().strip()
            if last_searched_word:
                print("Playing the word", last_searched_word,"\n")
                play_word_sound(last_searched_word)
                return
        else:
            print("swe\n\nUsage: 'swe ord' OR 'swe -s ord'\nAfter printing a definition, rerun 'swe' to hear it")

if __name__ == "__main__":
    main()
