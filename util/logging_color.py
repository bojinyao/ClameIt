from termcolor import colored

def _info(s: str) -> str:
    return colored(s, 'green')

def _warn(s: str) -> str:
    return colored(s, 'yellow')

def _error(s: str) -> str:
    return colored(s, 'red')

def _debug(s: str) -> str:
    return colored(s, 'cyan')
