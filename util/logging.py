from termcolor import colored

def print_info(s: str):
    print(colored(s, 'green'))

def print_warning(s: str):
    print(colored(s, 'yellow'))

def print_error(s: str):
    print(colored(s, 'red'))
