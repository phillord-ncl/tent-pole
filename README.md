Tent-Pole: Command Line tools for Canvas
========================================

Tent-Pole is a set of command line tools for interacting with content
on Canvas.


Getting Started
---------------

You will need to configure tent-pole with an API key (see instructions to
[Add Access Token](https://community.canvaslms.com/t5/Admin-Guide/How-do-I-manage-API-access-tokens->
This is done via
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

Cheat Sheet
------------

course
- data - Return some information about a course
    - E.g. `python3 tent-pole.py course data 14565`
- modules - Return list of modules in a course
    - E.g. `python3 tent-pole.py course modules 14565`
- files - Return list of modules in a course
    - E.g. `python3 tent-pole.py course files 14565`
- Could be collated?
    - pages - Return list of pages in a course
    - assignments - Return list of assignments in a course
    - quizzes - Return list of quizzes in a course
    - discussions - Return list of discussions in a course


module
- data - Return some information about a module
    - E.g. `python3 tent-pole.py -c=14565 module data TODO`
    - E.g. `python3 tent-pole.py -c=14565 module data 197477`
- list - Return list of items in a module
    - E.g. `python3 tent-pole.py -c=14565 module list TODO`
- delete - Deletes module from a course (should be at the course level?)
    - E.g. `python3 tent-pole.py -c=14565 module delete TEST`
- create - Creates a module to course, even if it already exists (should be at the course level?)
    - E.g. `python3 tent-pole.py -c=14565 module create TEST`
- addpage - Adds page to a module, optional indent argument (0 to 5)
    - E.g. `python3 tent-pole.py -c=14565 module addpage TEST test1`
    - E.g. `python3 tent-pole.py -c=14565 module addpage TEST test1 1`
- addhead - Adds sub header to a module, optional indent argument (0 to 5)
    - E.g. `python3 tent-pole.py -c=14565 module addhead TEST "Formative Exercises"`
    - E.g. `python3 tent-pole.py -c=14565 module addhead TEST "Formative Exercises" 1`
- addfile - Adds file to a module, optional indent argument (0 to 5)
    - E.g. `python3 tent-pole.py -c=14565 module addfile TEST 3203386`
    - E.g. `python3 tent-pole.py -c=14565 module addfile TEST 3203386 1`
- TODO publish - Publish a module on a course
- TODO remove - Removes item (e.g. page) from a course
- TODO reorder - Reorder the Modules?
- TODO update - Update module details (and items?)


page
- data - Return some information about a page
    - E.g. `python3 tent-pole.py -c=14565 page data test1`
    - E.g. `python3 tent-pole.py -c=14565 page data "Module Forms"`
- Create - Create a page that does not exist, throws error if it does
    - E.g. `python3 tent-pole.py -c=14565 page create test.html`
- TODO Dump - Dump information to a local file (what is a .ttp file)?
- update - Update an existing page that exists
    - E.g. `python3 tent-pole.py -c=14565 page update test.html`
- Push - Create or Update a page
    - E.g. `python3 tent-pole.py -c=14565 page push test.html`


file
- data - Return some information about a file
    - E.g. `python3 tent-pole.py -c=14565 file date python.zip`
- dump - Dump information to a local file (what is a .tpf file)?
- push - Create or Update a file, it is found in the unfiled directory
    - E.g. `python3 tent-pole.py -c=14565 file push tent-pole.py`


TODO Other files
- assignment
- quiz
- discussion
- externalurl
TODO externaltool?
