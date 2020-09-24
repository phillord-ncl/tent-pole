import click
import dpath.util
import logging
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
def main(course):
    if course:
        dpath.util.new(config.CONFIG, "course/identifier", "temp")
        dpath.util.set(config.CONFIG, "course/identifier", course)

main.add_command(config.config)
main.add_command(course.course)
main.add_command(file.file)
main.add_command(module.module)
main.add_command(page.page)
