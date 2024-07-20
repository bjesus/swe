import html
import xml.etree.ElementTree as ET
from swe.common import xml_file


def print_header(text):
    print(f"\n\033[3m{text}\033[0m")


def print_translations(xml_file, search_word):
    found_word = False
    tree = ET.parse(xml_file)
    root = tree.getroot()
    for word in root.findall(".//word[@value]"):
        word_value = word.attrib["value"]
        inflections = word.findall("./paradigm/inflection[@value]")
        if word_value == search_word or any(
            inflection.attrib["value"] == search_word for inflection in inflections
        ):
            found_word = True
            comment = word.get("comment", "")
            print(f"\033[58;5;158m\033[4:2m\033[1m{word_value}\033[0m", end="")
            if "class" in word.attrib:
                print(f" ({word.attrib['class']})", end="")

            if comment:
                print(f" ({html.unescape(comment)})")
            else:
                print()
            if inflections:
                print(
                    ", ".join(inflection.attrib["value"] for inflection in inflections)
                )
            translations = word.findall("./translation[@value]")
            if translations:
                print_header("Translations")
                for translation in translations:
                    comment = translation.get("comment", "")
                    print(
                        f'-> \033[1m{html.unescape(translation.attrib["value"])}\033[0m',
                        end="",
                    )
                    if comment:
                        print(f" ({html.unescape(comment)})")
                    else:
                        print()

            synonyms = word.findall("./synonym[@value]")
            if synonyms:
                print_header("Synonyms")
                for synonym in synonyms:
                    level = synonym.get("level", "")
                    print(f'- {html.unescape(synonym.attrib["value"])}', end="")
                    if level:
                        print(f" ({html.unescape(level)})")
                    else:
                        print()

            examples = word.findall(".//example[@value]")
            if examples:
                print_header("Examples")
                for example in examples:
                    example_translation = example.find(".//translation[@value]")
                    if example_translation is not None:
                        print(
                            f'- {html.unescape(example.attrib["value"])}: {html.unescape(example_translation.attrib["value"])}'
                        )

            related = word.findall("./related[@value]")
            if related:
                print_header("Related")
                for rel in related:
                    rel_type = rel.get("type", "")
                    rel_translation = rel.find("./translation[@value]")
                    if rel_translation is not None:
                        print(
                            f'- {html.unescape(rel.attrib["value"])} ({html.unescape(rel_type)}): {html.unescape(rel_translation.attrib["value"])}'
                        )

            idioms = word.findall("./idiom[@value]")
            if idioms:
                print_header("Idioms")
                for idiom in idioms:
                    idiom_translation = idiom.find("./translation[@value]")
                    if idiom_translation is not None:
                        print(
                            f'- {html.unescape(idiom.attrib["value"])}: {html.unescape(idiom_translation.attrib["value"])}'
                        )
            print("")

    if not found_word:
        print(f'Word "{search_word}" not found in the XML file.')
