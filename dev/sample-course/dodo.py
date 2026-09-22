"""doit equivalent of this directory's own Makefile -- pulls in
tent-pole's built-in rules, then adds the two rules this fixture needs
that aren't generic tent-pole behaviour (matching the Makefile's own
test-image.png/test-video.mp4 rules): the demonstration of a course
adding its own extra task_* functions alongside the built-ins, the
same way CSC1034's make-inc/rules.inc adds its lecture-slide pandoc
rules alongside tent-pole's own make-rules/rules.inc."""

import os

from tent_pole.doit_rules import *  # noqa: F401,F403


def task_test_image():
    """test-image.png: gen_test_image.py -- not checked in, generated
    so the repo carries no binary test data."""
    return {
        "actions": [["python3", "gen_test_image.py"]],
        "file_dep": ["gen_test_image.py"],
        "targets": ["test-image.png"],
    }


def task_test_video():
    """test-video.mp4 -- no source file, matching the Makefile's own
    rule; build once and leave alone rather than every run."""
    return {
        "actions": [[
            "ffmpeg", "-f", "lavfi", "-i",
            "testsrc=duration=2:size=320x240:rate=15",
            "-f", "lavfi", "-i", "sine=frequency=440:duration=2",
            "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac",
            "-shortest", "-y", "test-video.mp4",
        ]],
        "targets": ["test-video.mp4"],
        "uptodate": [os.path.exists("test-video.mp4")],
    }
