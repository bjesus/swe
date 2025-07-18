from __future__ import annotations

from dataclasses import dataclass
from operator import itemgetter
from typing import (
    Callable,
    ClassVar,
    Sequence,
    cast,
)
from rich import style
from rich.text import Text
from rich.table import Table
from textual import events, on
from textual.app import ComposeResult
from textual.binding import Binding
from textual.content import Content
from textual.css.query import NoMatches
from textual.geometry import Offset, Region, Spacing
from textual.style import Style
from textual.widget import Widget
from textual.widgets import Input, OptionList
from textual.widgets.option_list import Option

from swe.textual_autocomplete.fuzzy_search import FuzzySearch


@dataclass
class TargetState:
    text: str
    """The content in the target widget."""

    cursor_position: int
    """The cursor position in the target widget."""


class DropdownItem(Option):
    def __init__(
        self,
        main: str | Content,
        prefix: str | Content | None = None,
        additional: str | None = None,
        id: str | None = None,
        disabled: bool = False,
        theme: dict = {},
    ) -> None:
        """A single option appearing in the autocompletion dropdown. Each option has up to 3 columns.
        Note that this is not a widget, it's simply a data structure for describing dropdown items.

        Args:
            left: The prefix will often contain an icon/symbol, the main (middle)
                column contains the text that represents this option.
            main: The main text representing this option - this will be highlighted by default.
                In an IDE, the `main` (middle) column might contain the name of a function or method.
        """
        self.main = Content(main) if isinstance(main, str) else main
        self.additional = (
            Content(additional) if isinstance(additional, str) else additional
        )
        self.prefix = Content(prefix, style) if isinstance(prefix, str) else prefix
        left = self.prefix
        prompt = self.main

        table = Table.grid(
            expand=True,
            collapse_padding=True,
            padding=0,
        )

        table.add_column(
            self.main.plain,
            justify="left",
            overflow="ellipsis",
            no_wrap=True,
        )
        table.add_column(
            self.prefix.plain,
            justify="right",
            no_wrap=True,
        )
        table.add_row(
            self.main.plain + " ",
            f"[italic {theme.get('text-secondary', '#ffffff')}]{self.prefix.plain}[/]",
        )
        # print(theme.get("text-secondary", "#ffffff"))
        prompt = table
        super().__init__(prompt, id, disabled)

    @property
    def value(self) -> str:
        return self.main.plain


class DropdownItemHit(DropdownItem):
    """A dropdown item which matches the current search string - in other words
    AutoComplete.match has returned a score greater than 0 for this item.
    """


class AutoCompleteList(OptionList):
    pass


class AutoComplete(Widget):
    BINDINGS = [
        Binding("escape", "hide", "Hide dropdown", show=False),
    ]

    DEFAULT_CSS = """\
    AutoComplete {
        height: auto;
        width: 100%;
        max-height: 12;
        display: none;
        background: $surface;
        overlay: screen;

        & AutoCompleteList {
            width: auto;
            height: auto;
            border: none;
            padding: 0;
            margin: 0;
            scrollbar-size-vertical: 1;
            text-wrap: nowrap;
            color: $foreground;
            background: transparent;
        }

        & .autocomplete--highlight-match {
            text-style: bold;
        }

    }
    """

    COMPONENT_CLASSES: ClassVar[set[str]] = {
        "autocomplete--highlight-match",
    }

    def __init__(
        self,
        target: Input | str,
        candidates: Sequence[DropdownItem | str]
        | Callable[[TargetState], list[DropdownItem]]
        | None = None,
        *,
        prevent_default_enter: bool = True,
        prevent_default_tab: bool = True,
        name: str | None = None,
        id: str | None = None,
        classes: str | None = None,
        disabled: bool = False,
    ) -> None:
        """An autocomplete widget.

        Args:
            target: An Input instance or a selector string used to query an Input instance.
                If a selector is used, remember that widgets are not available until the widget has been mounted (don't
                use the selector in `compose` - use it in `on_mount` instead).
            candidates: The candidates to match on, or a function which returns the candidates to match on.
                If set to None, the candidates will be fetched by directly calling the `get_candidates` method,
                which is what you'll probably want to do if you're subclassing AutoComplete and supplying your
                own custom `get_candidates` method.
            prevent_default_enter: Prevent the default enter behavior. If True, when you select a dropdown option using
                the enter key, the default behavior (e.g. submitting an Input) will be prevented.
            prevent_default_tab: Prevent the default tab behavior. If True, when you select a dropdown option using
                the tab key, the default behavior (e.g. moving focus to the next widget) will be prevented.
        """
        super().__init__(name=name, id=id, classes=classes, disabled=disabled)
        self._target = target

        # Users can supply strings as a convenience for the simplest cases,
        # so let's convert them to DropdownItems.
        self.candidates: (
            list[DropdownItem] | Callable[[TargetState], list[DropdownItem]] | None
        )
        """The candidates to match on, or a function which returns the candidates to match on."""
        if isinstance(candidates, Sequence):
            self.candidates = [
                candidate
                if isinstance(candidate, DropdownItem)
                else DropdownItem(main=candidate)
                for candidate in candidates
            ]
        else:
            self.candidates = candidates

        self.prevent_default_enter = prevent_default_enter
        """Prevent the default enter behavior. If True, when you select a dropdown option using
        the enter key, the default behavior (e.g. submitting an Input) will be prevented.
        """

        self.prevent_default_tab = prevent_default_tab
        """Prevent the default tab behavior. If True, when you select a dropdown option using
        the tab key, the default behavior (e.g. moving focus to the next widget) will be prevented.
        """

        self._target_state = TargetState("", 0)
        """Cached state of the target Input."""

        self._fuzzy_search = FuzzySearch()
        """The default implementation used by AutoComplete.match."""

    def compose(self) -> ComposeResult:
        option_list = AutoCompleteList(classes="blue")
        option_list.can_focus = False
        yield option_list

    def on_mount(self) -> None:
        # Subscribe to the target widget's reactive attributes.
        self.target.message_signal.subscribe(self, self._listen_to_messages)  # type: ignore
        self._subscribe_to_target()
        self._handle_target_update()
        self.set_interval(0.2, lambda: self.call_after_refresh(self._align_to_target))

    def _listen_to_messages(self, event: events.Event) -> None:
        """Listen to some events of the target widget."""

        try:
            option_list = self.option_list
        except NoMatches:
            # This can happen if the event is an Unmount event
            # during application shutdown.
            return

        if isinstance(event, events.Key) and option_list.option_count:
            displayed = self.display
            highlighted = option_list.highlighted or 0
            if event.key == "down":
                # Check if there's only one item and it matches the search string
                if option_list.option_count == 1:
                    search_string = self.get_search_string(self._get_target_state())
                    first_option = option_list.get_option_at_index(0).prompt
                    text_from_option = (
                        first_option.plain
                        if isinstance(first_option, Text)
                        else first_option
                    )
                    if text_from_option == search_string:
                        # Don't prevent default behavior in this case
                        return

                # If you press `down` while in an Input and the autocomplete is currently
                # hidden, then we should show the dropdown.
                event.prevent_default()
                event.stop()
                if displayed:
                    highlighted = (highlighted + 1) % option_list.option_count
                else:
                    self.display = True
                    highlighted = 0

                option_list.highlighted = highlighted

            elif event.key == "up":
                if displayed:
                    event.prevent_default()
                    event.stop()
                    highlighted = (highlighted - 1) % option_list.option_count
                    option_list.highlighted = highlighted
            elif event.key == "enter":
                if self.prevent_default_enter and displayed:
                    event.prevent_default()
                    event.stop()
                self._complete(option_index=highlighted)
            elif event.key == "tab":
                if self.prevent_default_tab and displayed:
                    event.prevent_default()
                    event.stop()
                self._complete(option_index=highlighted)
            elif event.key == "escape":
                if displayed:
                    event.prevent_default()
                    event.stop()
                self.action_hide()

        if isinstance(event, Input.Changed):
            # We suppress Changed events from the target widget, so that we don't
            # handle change events as a result of performing a completion.
            self._handle_target_update()

    def action_hide(self) -> None:
        self.styles.display = "none"

    def action_show(self) -> None:
        self.styles.display = "block"

    def _complete(self, option_index: int) -> None:
        """Do the completion (i.e. insert the selected item into the target input).

        This is when the user highlights an option in the dropdown and presses tab or enter.
        """
        if not self.display or self.option_list.option_count == 0:
            return

        option_list = self.option_list
        highlighted = option_index
        option = cast(DropdownItem, option_list.get_option_at_index(highlighted))
        highlighted_value = option.value
        with self.prevent(Input.Changed):
            self.apply_completion(highlighted_value, self._get_target_state())
        self.post_completion(option.id)

    def post_completion(self, id) -> None:
        """This method is called after a completion is applied. By default, it simply hides the dropdown."""
        self.action_hide()

    def apply_completion(self, value: str, state: TargetState) -> None:
        """Apply the completion to the target widget.

        This method updates the state of the target widget to the reflect
        the value the user has chosen from the dropdown list.
        """
        target = self.target
        target.value = ""
        target.insert_text_at_cursor(value)

        # We need to rebuild here because we've prevented the Changed events
        # from being sent to the target widget, meaning AutoComplete won't spot
        # intercept that message, and would not trigger a rebuild like it normally
        # does when a Changed event is received.
        new_target_state = self._get_target_state()
        self._rebuild_options(
            new_target_state, self.get_search_string(new_target_state)
        )

    @property
    def target(self) -> Input:
        """The resolved target widget."""
        if isinstance(self._target, Input):
            return self._target
        else:
            target = self.screen.query_one(self._target)
            assert isinstance(target, Input)
            return target

    def _subscribe_to_target(self) -> None:
        """Attempt to subscribe to the target widget, if it's available."""
        target = self.target
        self.watch(target, "has_focus", self._handle_focus_change)
        self.watch(target, "selection", self._align_and_rebuild)

    def _align_and_rebuild(self) -> None:
        self._align_to_target()
        self._target_state = self._get_target_state()
        search_string = self.get_search_string(self._target_state)
        self._rebuild_options(self._target_state, search_string)

    def _align_to_target(self) -> None:
        """Align the dropdown to the position of the cursor within
        the target widget, and constrain it to be within the screen."""
        x, y = self.target.cursor_screen_offset
        dropdown = self.option_list
        width, height = dropdown.outer_size

        # Constrain the dropdown within the screen.
        x, y, _width, _height = Region(x - 1, y + 1, width, height).constrain(
            "inside",
            "none",
            Spacing.all(0),
            self.screen.scrollable_content_region,
        )
        self.absolute_offset = Offset(x, y)
        self.refresh(layout=True)

    def _get_target_state(self) -> TargetState:
        """Get the state of the target widget."""
        target = self.target
        return TargetState(
            text=target.value,
            cursor_position=target.cursor_position,
        )

    def _handle_focus_change(self, has_focus: bool) -> None:
        """Called when the focus of the target widget changes."""
        if not has_focus:
            self.action_hide()
        else:
            target_state = self._get_target_state()
            search_string = self.get_search_string(target_state)
            self._rebuild_options(target_state, search_string)

    def _handle_target_update(self) -> None:
        """Called when the state (text or cursor position) of the target is updated.

        Here we align the dropdown to the target, determine if it should be visible,
        and rebuild the options in it.
        """
        self._target_state = self._get_target_state()
        search_string = self.get_search_string(self._target_state)

        # Determine visibility after the user makes a change in the
        # target widget (e.g. typing in a character in the Input).
        self._rebuild_options(self._target_state, search_string)
        self._align_to_target()

        if self.should_show_dropdown(search_string):
            self.action_show()
        else:
            self.action_hide()

    def should_show_dropdown(self, search_string: str) -> bool:
        """
        Determine whether to show or hide the dropdown based on the current state.

        This method can be overridden to customize the visibility behavior.

        Args:
            search_string: The current search string.

        Returns:
            bool: True if the dropdown should be shown, False otherwise.
        """
        option_list = self.option_list
        option_count = option_list.option_count

        if len(search_string) == 0 or option_count == 0:
            return False
        elif option_count == 1:
            first_option = option_list.get_option_at_index(0).prompt
            text_from_option = (
                first_option.plain if isinstance(first_option, Text) else first_option
            )
            return text_from_option != search_string
        else:
            return True

    def _rebuild_options(self, target_state: TargetState, search_string: str) -> None:
        """Rebuild the options in the dropdown.

        Args:
            target_state: The state of the target widget.
        """
        option_list = self.option_list
        option_list.clear_options()
        if self.target.has_focus:
            matches = self._compute_matches(target_state, search_string)
            if matches:
                option_list.add_options(matches)
                option_list.highlighted = 0

    def get_search_string(self, target_state: TargetState) -> str:
        """This value will be passed to the match function.

        This could be, for example, the text in the target widget, or a substring of that text.

        Returns:
            The search string that will be used to filter the dropdown options.
        """
        return target_state.text[: target_state.cursor_position]

    def _compute_matches(
        self, target_state: TargetState, search_string: str
    ) -> list[DropdownItem]:
        """Compute the matches based on the target state.

        Args:
            target_state: The state of the target widget.

        Returns:
            The matches to display in the dropdown.
        """

        # If items is a callable, then it's a factory function that returns the candidates.
        # Otherwise, it's a list of candidates.
        candidates = self.get_candidates(target_state)
        matches = self.get_matches(target_state, candidates, search_string)
        return matches

    def get_candidates(self, target_state: TargetState) -> list[DropdownItem]:
        """Get the candidates to match against."""
        candidates = self.candidates
        if isinstance(candidates, Sequence):
            return list(candidates)
        elif candidates is None:
            raise NotImplementedError(
                "You must implement get_candidates in your AutoComplete subclass, because candidates is None"
            )
        else:
            # candidates is a callable
            return candidates(target_state)

    def get_matches(
        self,
        target_state: TargetState,
        candidates: list[DropdownItem],
        search_string: str,
    ) -> list[DropdownItem]:
        """Given the state of the target widget, return the DropdownItems
        which match the query string and should be appear in the dropdown.

        Args:
            target_state: The state of the target widget.
            candidates: The candidates to match against.
            search_string: The search string to match against.

        Returns:
            The matches to display in the dropdown.
        """
        if not search_string:
            return candidates

        matches_and_scores: list[tuple[DropdownItem, float]] = []
        append_score = matches_and_scores.append
        match = self.match

        return candidates
        for candidate in candidates:
            score_main, offsets = match(search_string, candidate.main.plain)
            score_additional, _ = match(search_string, candidate.additional.plain)
            score_prefix, _ = match(search_string, candidate.prefix.plain)

            # Determine the highest score
            score = max(score_main, score_additional, score_prefix)

            if score > 0:
                highlighted = self.apply_highlights(candidate.main, offsets)
                highlighted_item = DropdownItemHit(
                    main=highlighted,
                    prefix=candidate.prefix,
                    id=candidate.id,
                    disabled=candidate.disabled,
                    theme=(candidate.theme or {}),
                )
                append_score((highlighted_item, score))

        matches_and_scores.sort(key=itemgetter(1), reverse=True)
        matches = [match for match, _ in matches_and_scores]
        return matches

    def match(self, query: str, candidate: str) -> tuple[float, tuple[int, ...]]:
        """Match a query (search string) against a candidate (dropdown item value).

        Returns a tuple of (score, offsets) where score is a float between 0 and 1,
        used for sorting the matches, and offsets is a tuple of integers representing
        the indices of the characters in the candidate string that match the query.

        So, if the query is "hello" and the candidate is "hello world",
        and the offsets will be (0,1,2,3,4). The score can be anything you want -
        and the highest score will be at the top of the list by default.

        The offsets will be highlighted in the dropdown list.

        A score of 0 means no match, and such candidates will not be shown in the dropdown.

        Args:
            query: The search string.
            candidate: The candidate string (dropdown item value).

        Returns:
            A tuple of (score, offsets).
        """
        return self._fuzzy_search.match(query, candidate)

    def apply_highlights(self, candidate: Content, offsets: tuple[int, ...]) -> Content:
        """Highlight the candidate with the fuzzy match offsets.

        Args:
            candidate: The candidate which matched the query. Note that this may already have its
                own styling applied.
            offsets: The offsets to highlight.
        Returns:
            A [rich.text.Text][`Text`] object with highlighted matches.
        """
        # TODO - let's have styles which account for the cursor too
        match_style = Style.from_rich_style(
            self.get_component_rich_style("autocomplete--highlight-match", partial=True)
        )

        plain = candidate.plain
        for offset in offsets:
            if not plain[offset].isspace():
                candidate = candidate.stylize(match_style, offset, offset + 1)

        return candidate

    @property
    def option_list(self) -> AutoCompleteList:
        return self.query_one(AutoCompleteList)

    @on(OptionList.OptionSelected, "AutoCompleteList")
    def _apply_completion(self, event: OptionList.OptionSelected) -> None:
        # Handles click events on dropdown items.
        self._complete(event.option_index)
