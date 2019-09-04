
# Translated to pyton from JS under the following license:
#
# MIT License
#
# Copyright (c) Sindre Sorhus <sindresorhus@gmail.com> (sindresorhus.com)
#
# Permission is hereby granted, free of charge, to any person obtaining a
# copy of this software and associated documentation files (the "Software")
# to deal in the Software without restriction, including without limitation
# the rights to use, copy, modify, merge, publish, distribute, sublicense,
# and/or sell copies of the Software, and to permit persons to whom the
# Software is furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
# DEALINGS IN THE SOFTWARE.

from collections import namedtuple, Counter
import io
import re

Result = namedtuple('Result', ('amount', 'type', 'indent', 'newline'))

# Detect either spaces or tabs but not both to properly handle tabs for indentation and spaces for alignment
INDENT_REGEX = re.compile(r'^(?:( )+|\t+)')

NEWLINE_REGEX = re.compile(r'\r\n|(?!\r)\n|\r(?!\n)')


def get_most_used(indents):
    result = 0
    maxUsed = 0
    maxWeight = 0

    for key, (usedCount, weight) in indents.items():
        if usedCount > maxUsed or (usedCount == maxUsed and weight > maxWeight):
            maxUsed = usedCount
            maxWeight = weight
            result = key

    return result


def detects(source):
    if not isinstance(source, str):
        raise TypeError('Expected a string')

    # Remember the size of previous line's indentation
    previousSize = 0

    # Remember how many indents/unindents have occurred for a given size and how many lines follow a given indentation.
    # The key is a concatenation of the indentation type (s = space and t = tab) and the size of the indents/unindents.
    #
    # indents = {
    #    t3: [1, 0],
    #    t4: [1, 5],
    #    s5: [1, 0],
    #   s12: [1, 0],
    # }
    indents = {}

    for line in source.splitlines():
        if not line:
            # Ignore empty lines
            continue

        matches = INDENT_REGEX.match(line)

        if matches is None:
            previousSize = 0
            previousIndentType = ''
        else:
            indent = len(matches[0])

            if matches[1]:
                indentType = 's'
            else:
                indentType = 't'

            if indentType != previousIndentType:
                previousSize = 0

            previousIndentType = indentType

            weight = 0

            indentDifference = indent - previousSize
            previousSize = indent

            # Previous line have same indent?
            if indentDifference == 0:
                weight += 1
                # We use the key from previous loop
            else:
                key = indentType + str(abs(indentDifference))

            # Update the stats
            entry = indents.get(key, None)

            if entry is None:
                entry = (1, 0) # Init
            else:
                entry = [entry[0] + 1, entry[1] + weight]

            indents[key] = entry

    result = get_most_used(indents)

    newlines = NEWLINE_REGEX.findall(source)
    c = Counter(newlines)
    newline = c.most_common(1)[0][0] if c else None

    amount = 0
    indent = ''
    type = None

    if result != 0:
        amount = int(result[1:])

        if result[0] == 's':
            type = 'space'
            indent = ' ' * amount
        else:
            type = 'tab'
            indent = '\t' * amount

    return Result(
        amount=amount,
        type=type,
        indent=indent,
        newline=newline,
    )


def detect(filename):
    with io.open(filename, 'r', encoding='utf8') as f:
        return detects(f.read())
