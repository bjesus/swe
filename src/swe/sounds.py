from swe.common import xml_file
import xml.etree.ElementTree as ET
import os
from subprocess import Popen, DEVNULL, STDOUT


def play_file(word):
    iso_word = encode_iso(word)
    sound_url = f"http://lexin.nada.kth.se/sound/{iso_word}.mp3"
    os.environ["MPLAYER_VERBOSE"] = "-4"
    Popen(["mplayer", "-really-quiet", sound_url], stdout=DEVNULL, stderr=STDOUT)


def get_sound_file(xml_file, search_word):
    sound_file = False
    tree = ET.parse(xml_file)
    root = tree.getroot()
    for word in root.findall(".//word[@value]"):
        word_value = word.attrib["value"]
        inflections = word.findall("./paradigm/inflection[@value]")
        if word_value == search_word or any(
            inflection.attrib["value"] == search_word for inflection in inflections
        ):
            phonetic = word.findall("./phonetic[@soundFile]")
            if phonetic:
                sound_file = phonetic[0].attrib["soundFile"].replace(".swf", "")
            return (word.attrib["value"], sound_file)
    return (search_word, None)


def play_word(word):
    word_root, sound_file = get_sound_file(xml_file, word)
    if sound_file:
        print("Playing the word", word_root, "\n")
        play_file(sound_file)
    else:
        print("Cannot find sound file for", word_root)


def encode_iso(word):
    iso_mapping = {"å": "0345", "ä": "0344", "ö": "0366"}
    return "".join(iso_mapping.get(char, char) for char in word)
