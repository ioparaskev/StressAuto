#!/usr/bin/python

import sys
import time


def stdout_with_delay(character, seconds_delay=0.0):
    time.sleep(seconds_delay)
    sys.stdout.write(character)
    sys.stdout.flush()


def stdout_word_with_delay(text, delay=0.1):
    for character in text:
        stdout_with_delay(character, seconds_delay=delay)


def progress_bar(text='-', placeholder='-', toolbar_width=60,
                 delimiters=('[', ']')):
    import sys
    text_length = len(text) if text else 0
    toolbar_width += text_length
    # setup toolbar
    sys.stdout.write('{0}{1}{2}'.format(delimiters[0], " " * toolbar_width,
                                        delimiters[1]))
    sys.stdout.flush()
    # return to start of line, after '['
    sys.stdout.write("\b" * (toolbar_width + 1))

    for i in xrange((toolbar_width - text_length) / 2):
        stdout_with_delay(placeholder, seconds_delay=0.1)

    stdout_word_with_delay(text)

    for i in xrange((toolbar_width + text_length) / 2, toolbar_width):
        stdout_with_delay(placeholder, seconds_delay=0.1)

    sys.stdout.write("\n")


def main():
    sys.stdout.flush()
    progress_bar('TEST', '-')
    delimeters = ('|', '|')
    progress_bar('', delimiters=delimeters)
    progress_bar('TEST', delimiters=delimeters)


if __name__ == '__main__':
    main()