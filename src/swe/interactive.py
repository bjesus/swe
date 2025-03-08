import xml.etree.ElementTree as ET
import editdistance
import requests

from lxml import html
from markdownify import markdownify
from textual import on
from textual.app import App, ComposeResult
from textual.widgets import Footer, Input, Markdown
from textual.app import App, ComposeResult

from swe._autocomplete import AutoComplete, Dropdown, DropdownItem, InputState
from swe.common import xml_file
from swe.sounds import play_word

items = []
MAX_DROPDOWN_ITEMS = 50


class SvenskaApp(App):
    """A Swedish-English dictionary."""

    visible_word = ""
    wiktionary_content = ""

    DATA = []

    tree = ET.parse(xml_file)
    root = tree.getroot()
    for word in root.findall(".//word[@value]"):
        entry = [
            word.attrib["value"],
            ", ".join([t.attrib["value"] for t in word.findall("./translation")]),
            " ".join(
                [
                    t.attrib["value"]
                    for t in word.findall("./paradigm/inflection[@value]")
                ]
            ),
        ]

        DATA.append(entry)

    for rank, (word, translation, inflections) in enumerate(DATA, start=2):
        items.append(
            DropdownItem(
                word,
                translation,
                inflections,
            )
        )

    def get_items(self, input_state: InputState) -> list[DropdownItem]:
        matches = [
            item
            for item in items
            if input_state.value.lower() in item.main.plain.lower()
            or input_state.value.lower() in item.left_meta.plain.lower()
            or input_state.value.lower() in item.right_meta.plain.lower()
        ]

        return sorted(
            matches,
            key=lambda v: editdistance.eval(v.main.plain, input_state.value.lower()),
        )[:MAX_DROPDOWN_ITEMS]

    def get_answer(self, search_word) -> str:
        answer = ""
        for word in self.root.findall(".//word[@value]"):
            word_value = word.attrib["value"]
            inflections = word.findall("./paradigm/inflection[@value]")

            if word_value == search_word or any(
                inflection.attrib["value"] == search_word for inflection in inflections
            ):
                comment = word.get("comment", "")
                answer += "## " + word_value

                if inflections:
                    answer += (
                        "\n`"
                        + (
                            ", ".join(
                                inflection.attrib["value"] for inflection in inflections
                            )
                        )
                        + "`\n"
                    )

                translations = word.findall("./translation[@value]")
                if translations:
                    answer += "\n\n**"

                    answer += ", ".join(
                        (
                            f"{translation.attrib['value']}</span> ({translation.attrib['comment']})"
                            if translation.get("comment", "")
                            else "" + translation.attrib["value"] + ""
                        )
                        for translation in translations
                    )
                    answer += "**"
                if comment:
                    answer += f"\n\n*{comment}*"
                synonyms = word.findall("./synonym[@value]")
                if synonyms:
                    answer += "\n\n### Synonyms\n"
                    answer += ", ".join(synonym.attrib["value"] for synonym in synonyms)
                    answer += ""

                examples = word.findall(".//example[@value]")
                if examples:
                    answer += "\n\n### Examples"
                    for example in examples:
                        example_translation = example.find(".//translation[@value]")
                        if example_translation is not None:
                            answer += f"\n- {example.attrib['value']}: *{example_translation.attrib['value']}*"
                    answer += ""

                idioms = word.findall("./idiom[@value]")
                if idioms:
                    answer += "\n\n ### Idioms"
                    for idiom in idioms:
                        idiom_translation = idiom.find("./translation[@value]")
                        if idiom_translation is not None:
                            answer += f"\n- {idiom.attrib['value']}: *{idiom_translation.attrib['value']}*"
                    answer += ""

                return answer

        return "Word not found"

    CSS_PATH = "style.tcss"

    BINDINGS = [
        ("ctrl+q", "quit", "Quit"),
        ("ctrl+p", "play", "Play"),
        ("ctrl+s", "wiktionary", "Wiktionary"),
    ]

    def action_play(self) -> None:
        play_word(visible_word)

    def action_wiktionary(self) -> None:
        global wiktionary_content

        a = requests.get(
            f"https://sv.wiktionary.org/w/index.php?title={visible_word}&printable=yes"
        )

        tree = html.fromstring(a.text)
        wiktionary_content = a.text
        mw_parser_output = tree.find_class("mw-parser-output")
        if not mw_parser_output:
            wiktionary_content = "not found"
            return
        html_content = html.tostring(
            mw_parser_output[0], pretty_print=False, encoding="unicode"
        )
        svenska_div = mw_parser_output[0].get_element_by_id("Svenska")
        if not svenska_div:
            wiktionary_content = "not found"
        content_after_svenska = []
        for element in svenska_div.getparent().getnext():
            content = html.tostring(element, pretty_print=False, encoding="unicode")
            if content and 'id="Översättningar"' in content:
                break
            content_after_svenska.append(content)
        html_content_after_svenska = "".join(content_after_svenska)

        wiktionary_content = html_content
        wiktionary_content = markdownify(html_content_after_svenska)

        self.query_one(Markdown).update(wiktionary_content)

    TITLE = "swe"

    def compose(self) -> ComposeResult:
        """Create child widgets for the app."""
        yield AutoComplete(
            Input(classes="search"),
            Dropdown(items=self.get_items),
        )
        yield Markdown()
        yield Footer()

    @on(AutoComplete.Selected)
    def select_word(self, event: AutoComplete.Selected) -> None:
        global visible_word
        visible_word = event.item.main.plain.lower()
        viewer = self.query_one(Markdown)
        viewer.update(self.get_answer(visible_word))
        viewer.display = True
        viewer.focus()

    @on(Markdown.LinkClicked)
    def navigate(self, event: Markdown.LinkClicked) -> None:
        global visible_word
        visible_word = event.href.split("/")[4].split("#")[0]
        self.action_wiktionary()
