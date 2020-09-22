import click
import dpath.util
import logging
import sys


from . import config
from . import course
from . import file
from . import page



logger = logging.getLogger("canvasapi")
handler = logging.StreamHandler(sys.stdout)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

##handler.setLevel(logging.DEBUG)
handler.setFormatter(formatter)
#logger.addHandler(handler)
logger.setLevel(logging.DEBUG)

## CLI Follows
def __course(courseidentifier):
   return course.course_by_guess(courseidentifier)

@click.group()
@click.option("-c","--course", "course", help="Course ID")
def main(course):
    if course:
        ## __course is just to avoid the name clash with the local variable.
        ## The local variable is user facing
        courseobj = __course(course)
        dpath.util.new(config.CONFIG, "general/course", "temp")
        dpath.util.set(config.CONFIG, "general/course", courseobj.id)

main.add_command(config.config)
main.add_command(course.course)
main.add_command(file.file)
main.add_command(page.page)
