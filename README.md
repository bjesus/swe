# swe - Swedish-English Dictionary

<p align="center">
<img width="516" height="469" src="https://github.com/bjesus/swe/assets/55081/839c6420-2d91-4fb3-bab9-29494974ad6c" />
</p>

`swe` is a command-line interface to the great Swedish-English dictionary "[Folkets lexikon](https://folkets-lexikon.csc.kth.se/folkets/om.en.html)". It works 100% offline. Users can explore translations, idioms, synonoms and more. It can also be used for finding words containing specific substrings, and for listening to the pronunciations of words.

## Installation

You can install `swe` using `pipx install swe`

### Zsh Completion

The repository includes a Zsh completion file [\_swe](_swe) to enhance the user experience by enabling word auto-completion.

To enable Zsh completion, do the following:

```
$ cp swe/_swe ~/.zsh/completion/_swe
$ chmod +x ~/.zsh/completion/_swe
```

You will need to restart Zsh for the changes to take effect.

## Usage

1. `swe -s ord` - Print all words containing the specified substring ("ord" in this example).
2. `swe ord` - Print the translation for the specified word
3. `swe` - Play the sound of the latest translated word
