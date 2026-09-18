# Install tent-pole

Requirements: Python >= 3.14. Optional: Pandoc, for the filters; GNU
Make, for building a whole course.

## With Poetry, for development

```
poetry install
poetry run tent-pole --help
```

Every other command in these docs assumes `tent-pole` is already on
your `PATH` -- prefix with `poetry run` (or `poetry shell` first) if
you're working from a Poetry checkout instead. `tent-pole.py` in the
repository root is an equivalent entry point, so `python3 tent-pole.py
--help` also works as a shorthand -- but only inside an environment
that already has tent-pole's dependencies installed (i.e. after
`poetry install`, run via `poetry run`/`poetry shell` same as above),
not as a way to skip installing anything.

## As a `tent-pole` binary on your `PATH`

From a local checkout, on top of the Poetry install above:

```
./local-install.sh
```

## Via pipx, without a local checkout

Tent-pole isn't on PyPI, but pipx installs anything pip can, straight
from GitHub:

```
pipx install "git+https://github.com/phillord-ncl/tent-pole.git"
```

or from a local clone:

```
pipx install /path/to/tent-pole/main
```

## On Windows

Python, GNU Make, and Pandoc are not preinstalled. `winget` covers all
three:

```
winget install --id Python.Python.3.14
winget install --id GnuWin32.Make
winget install --id JohnMacFarlane.Pandoc
```

Then the Poetry or pipx install above works as-is from PowerShell or
`cmd`. `local-install.sh` is a Bash script and needs WSL or Git Bash to
run -- pipx is the simpler route to a `tent-pole` binary on native
Windows.

## Check it worked

```
tent-pole --help
```

should list the command groups (`config`, `course`, `module`, `page`,
`file`, `quiz`). Next: [configure](configure.md) tent-pole with your
Canvas API key and course.
