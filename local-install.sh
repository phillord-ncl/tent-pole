#!/bin/bash
poetry build
/usr/bin/pip3 install --user ./dist/tent_pole-0.1.0-py3-none-any.whl
