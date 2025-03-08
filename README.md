# swe - Swedish-English Dictionary

`swe` is a command-line interface to the great Swedish-English dictionary "[Folkets lexikon](https://folkets-lexikon.csc.kth.se/folkets/om.en.html)". It works 100% offline. Users can explore translations, idioms, synonyms and more. It can also be used for finding words containing specific substrings, and for listening to the pronunciations of words. Since version 0.3, it can also access [Wiktionary](https://sv.wiktionary.org).

https://github.com/user-attachments/assets/097a29ee-c829-4f6a-acd7-a83e93ee742d

## Installation

You can run `swe` using `uvx swe`, or install it using `uv tool install swe` or `pipx install swe`

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
