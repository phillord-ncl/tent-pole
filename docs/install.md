# Install tent-pole

Requirements: Python >= 3.14. Optional: Pandoc, for the filters.
`tent-pole build` (for building a whole course) needs nothing extra --
it's built on [doit](https://pydoit.org/), a regular Python
dependency installed alongside tent-pole itself.


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

```
pipx install --editable /path/to/tent-pole/main
```

keeps `tent-pole`/`canvas-filter`/`code-include-filter`/
`include-deps-filter` on your `PATH` live against the checkout -- edit
the source, no reinstall needed. This is the way to develop against a
project that lives anywhere (unlike `poetry run`, which needs to run
from inside the checkout). `poetry install` is still what you want for
running tent-pole's own test suite.

## On Windows

Python and Pandoc are not preinstalled. `winget` covers both -- no
separate GNU Make install needed, unlike before `tent-pole build`
existed:

```
winget install --id Python.Python.3.14
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
