import sys


def print_err(*args, **kwargs):
    return print(*args, file=sys.stderr, **kwargs)