Tent-Pole: Command Line tools for Canvas
========================================

Tent-Pole is a set of command line tools for interacting with content
on Canvas.


Getting Started
---------------

You will need to configure tent-pole with an API key. This is done via
a TOML file which can be either in the current working directory, or
in your user configuration path (see
https://pypi.org/project/appdirs/). Or in both places.

```
[general]
api_key = "put-your-api-key-in-here"
```


Tent-pole uses a subcommand structure. So, for example, to push a page
to blackboard.

```
tent-pole.py --course=23212 page push ./dev/test-1.html
Pushed:./dev/test-1.html as test-1
```
