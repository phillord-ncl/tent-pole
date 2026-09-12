#!/usr/bin/env python3

import glob
import os

print("# -*- Makefile -*-\n")
srcs = glob.glob("*.py")

alltargets = []

for src in srcs:
    stem = os.path.splitext(src)[ 0 ]

    if stem.startswith("test_"):
        print("%s.test_out: %s.py" % (stem, stem))
        alltargets.append("%s.test_out" % (stem))
        continue

    f = open(src,"r")
    src_string = f.read()

    if ("## Status: Crash" in src_string):
        print("%s.crash: %s.py" % (stem,stem))
        alltargets.append("%s.crash" % (stem))
    elif ("## Status: Shell" in src_string):
        print("%s.stout: %s.py" % (stem,stem))
        alltargets.append("%s.stout" % (stem))
    else:
        print("%s.out: %s.py" % (stem,stem))
        alltargets.append("%s.out" % (stem))

for script in glob.glob( "*.pys" ):
    stem = os.path.splitext(script)[ 0 ]
    print("%s.stout: %s.pys" % (stem,stem))
    alltargets.append("%s.stout" % (stem))


print("all-targets: " + " " \
      + " ".join(
          [targ + ".tpf" for targ in alltargets] +
          [src + ".tpf" for src in srcs]
        )
      )
