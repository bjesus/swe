import xml.etree.ElementTree as ET
import editdistance
import requests
import os
import toml
import subprocess

from lxml import html
from markdownify import markdownify
from textual import on
from textual.app import App, ComposeResult
from textual.widgets import Footer, Input, Markdown

# from swe._autocomplete import AutoComplete, Dropdown, DropdownItem, InputState
from textual_autocomplete import AutoComplete, DropdownItem, TargetState
from swe.common import xml_file
from swe.sounds import play_word

from xdg_base_dirs import xdg_config_home

visible_word = ""
items = []
DATA = []

MAX_DROPDOWN_ITEMS = 50


class SvenskaApp(App):
    """A Swedish-English dictionary."""

    TITLE = "swe"
    config_dir = xdg_config_home()

    # Step 2: Define the path to the toml config file
    config_file = os.path.join(config_dir, "swe.toml")

    global config
    theme_variables = {}
    config = {}
    # Step 3: Check if the file exists
    if os.path.exists(config_file):
        try:
            config = toml.load(config_file)
        except toml.TomlDecodeError as e:
            print(f"Error reading TOML file: {e}")

    wiktionary_content = ""

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

    CSS_PATH = "style.tcss"

    BINDINGS = [
        ("ctrl+q", "quit", "Quit"),
        ("ctrl+p", "play", "Play"),
        ("ctrl+s", "wiktionary", "Wiktionary"),
    ]
    ENABLE_COMMAND_PALETTE = False
    if config.get("custom_command", False) and not config.get(
        "auto_run_custom_command", False
    ):
        BINDINGS.append(
            ("ctrl+t", "custom", config.get("custom_command_title", "Custom"))
        )

    def on_mount(self) -> None:
        global DATA
        self.theme = config.get("theme", "textual-dark")

        for rank, (word, translation, inflections) in enumerate(DATA, start=2):
            items.append([word, translation, inflections, str(rank)])

    def get_answer(self, id) -> str:
        global visible_word
        global visible_word_id
        search_word = items[id][0]
        visible_word_id = id
        visible_word = search_word
        answer = ""
        word = self.root.findall(".//word[@value]")[id]
        word_value = word.attrib["value"]
        inflections = word.findall("./paradigm/inflection[@value]")

        comment = word.get("comment", "")
        answer += "## " + word_value

        if inflections:
            answer += (
                "\n`"
                + (", ".join(inflection.attrib["value"] for inflection in inflections))
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

        return answer.strip()

    def action_custom(self) -> None:
        # Step 5: Check if the `custom_command` key exists in the TOML file
        if "custom_command" not in config:
            print("custom_command key not found in the config file.")
            return

        # Step 6: Get the custom command from the TOML file
        custom_command = config["custom_command"]

        # Step 7: Execute the command and pass "foo" to it via stdin
        try:
            process = subprocess.Popen(
                custom_command,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                shell=True,
            )
            stdout, stderr = process.communicate(
                input=(visible_word + "\n" + self.get_answer(visible_word_id)).encode()
            )

            # Print the output or any error from the command
            if process.returncode == 0:
                print(f"Command output: {stdout.decode()}")
            else:
                print(f"Error executing command: {stderr.decode()}")

        except Exception as e:
            print(f"Error executing the command: {e}")

    def action_play(self) -> None:
        global visible_word
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

    def compose(self) -> ComposeResult:
        """Create child widgets for the app."""
        topself = self

        class WordChooser(AutoComplete):
            def get_candidates(self, target_state: TargetState) -> list[DropdownItem]:
                input = target_state.text.lower()
                matches = [
                    item
                    for item in items
                    if input in item[0].lower()
                    or input in item[1].lower()
                    or input in item[2].lower()
                ]

                return [
                    DropdownItem(
                        main=v[0],
                        prefix=v[1],
                        additional=v[2],
                        id=v[3],
                        theme=topself.theme_variables,
                    )
                    for v in sorted(
                        matches,
                        key=lambda v: editdistance.eval(
                            v[0], target_state.text.lower()
                        ),
                    )[:MAX_DROPDOWN_ITEMS]
                ]

            def post_completion(self, id) -> None:
                viewer = topself.query_one(Markdown)
                viewer.update(topself.get_answer(int(id) - 2))
                viewer.display = True
                viewer.focus()

                if config.get("custom_command", False) and config.get(
                    "auto_run_custom_command", False
                ):
                    topself.action_custom()

                self.action_hide()

        input = Input(classes="search")
        input.styles.layer = "above"
        yield input
        wordchooser = WordChooser(input)
        wordchooser.styles.layer = "above"
        yield wordchooser
        markdown = Markdown()
        markdown.styles.offset = (0, 2)
        markdown.styles.layer = "below"
        yield markdown
        yield Footer()

    @on(Markdown.LinkClicked)
    def navigate(self, event: Markdown.LinkClicked) -> None:
        global visible_word
        visible_word = event.href.split("/")[4].split("#")[0]
        self.action_wiktionary()
