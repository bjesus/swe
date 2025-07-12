# swe - Swedish-English Dictionary

`swe` is a command-line interface to the great Swedish-English dictionary "[Folkets lexikon](https://folkets-lexikon.csc.kth.se/folkets/om.en.html)". It works 100% offline. Users can explore translations, idioms, synonyms and more. It can also be used for finding words containing specific substrings, and for listening to the pronunciations of words. Since version 0.3, it can also access [Wiktionary](https://sv.wiktionary.org).

<https://github.com/user-attachments/assets/097a29ee-c829-4f6a-acd7-a83e93ee742d>

## Installation

You can run `swe` using `uvx swe`, or install it using `uv tool install swe` or `pipx install swe`

## Configuration

The interactive mode can take a few settings from at $XDG_CONFIG_HOME/swe.toml:

```tool
custom_command = '/home/user/.scripts/swe-favorite' # this will introduce a new button
custom_command_title = 'Save' # this will be the button label
theme = 'dracula' # specify a theme
auto_run_custom_command = false # this command will run automatically for every word
```

Swe will pipe the current word through STDIN to the commands you specify. You can check out some [Textual themes here](https://github.com/Textualize/textual/blob/93709e91fd492a628393508614c50f65d6d16c1c/src/textual/theme.py#L181).

### Zsh Completion

The repository includes a Zsh completion file [\_swe](_swe) to enhance the user experience by enabling word auto-completion.

To enable Zsh completion, do the following:

```sh
cp swe/_swe ~/.zsh/completion/_swe
chmod +x ~/.zsh/completion/_swe
```

You will need to restart Zsh for the changes to take effect.

## Usage

1. `swe` - Enter interactive mode
2. `swe ord` - Print the translation for the specified word
3. `swe -s ord` - Print all words containing the specified substring ("ord" in this example).
