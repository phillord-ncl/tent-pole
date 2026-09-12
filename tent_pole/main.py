import click
import dpath.util
import logging
import os
import sys


from . import config
from . import course
from . import file
from . import module
from . import page


logger = logging.getLogger("canvasapi")
handler = logging.StreamHandler(sys.stdout)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

##handler.setLevel(logging.DEBUG)
handler.setFormatter(formatter)
#logger.addHandler(handler)
logger.setLevel(logging.DEBUG)

## CLI Follows
@click.group()
@click.option("-c","--course", "course", help="Course ID")
@click.option("--beta", is_flag=True, help="Target [dev] test_course_id/"
              "test_api_url/test_api_key from your config instead of "
              "[general]/[course], for this invocation only. Takes "
              "priority over -c/--course.")
def main(course, beta):
    if beta:
        os.environ["TENT_POLE_USE_TEST_CONFIG"] = "1"
    if course:
        dpath.util.new(config.CONFIG, "course/identifier", "temp")
        dpath.util.set(config.CONFIG, "course/identifier", course[1:])

@main.command(name="pkg-dir", help="Print the path to tent-pole's "
              "installed package directory, e.g. for a downstream "
              "Makefile to locate the shipped make-rules/ and bin/.")
def pkg_dir():
    print(os.path.dirname(__file__))

main.add_command(config.config)
main.add_command(course.course)
main.add_command(file.file)
main.add_command(module.module)
main.add_command(page.page)
