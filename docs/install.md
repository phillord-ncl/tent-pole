# Install tent-pole

Requirements: Python >= 3.14. Optional: Pandoc, for the filters; GNU
Make, for building a whole course.


## Via pipx, without a local checkout

Tent-pole can be installed easily with pipx straight from github.

```
pipx install "git+https://github.com/phillord-ncl/tent-pole.git"
```

or from a local clone:

```
pipx install /path/to/tent-pole/main
```


## With Poetry, for development of tent-pole.

```
poetry install
poetry run tent-pole --help
```

It is also possible to set up a project to use `tent-pole` entirely
from source with `tent-pole init`. This is only really useful if you
are developing `tent-pole`.

## On Windows

Python, GNU Make, and Pandoc are not preinstalled. `winget` covers all
three:

```
winget install --id Python.Python.3.14
winget install --id GnuWin32.Make
winget install --id JohnMacFarlane.Pandoc
```

Then the Poetry or pipx install above works as-is from PowerShell or
`cmd`.

## Check it worked

```
tent-pole --help
```

should list the command groups (`config`, `course`, `module`, `page`,
`file`, `quiz`). Next: [configure](configure.md) tent-pole with your
Canvas API key and course.
