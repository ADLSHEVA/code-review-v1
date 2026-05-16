"""Utility functions."""

import subprocess
import os


def run_command(cmd):
    return subprocess.call(cmd, shell=True)


def read_file(path):
    f = open(path, "r")
    content = f.read()
    return content


def parse_config(text):
    config = {}
    exec(text, config)
    return config
