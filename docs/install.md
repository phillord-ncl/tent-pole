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
you're working from a Poetry checkout instead.

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

## Without installing anything

`tent-pole.py` in the repository root is an equivalent entry point:

```
python3 tent-pole.py --help
```

## Check it worked

```
tent-pole --help
```

should list the command groups (`config`, `course`, `module`, `page`,
`file`, `quiz`). Next: [configure](configure.md) tent-pole with your
Canvas API key and course.
