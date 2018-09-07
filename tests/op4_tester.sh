#!/bin/bash

export PYTHONPATH="${PYTHONPATH}:../:../pynastran:../../binaryornot:../../binaryornot/binaryornot"
export PYTHON="python"
${PYTHON} op4_tester.py
