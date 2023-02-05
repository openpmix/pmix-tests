#!/usr/bin/env python3

import sys

def main():
    matrix1 = []
    missing = []
    extras = []
    exitcode = 0

    if (3 != len(sys.argv)):
        print("Usage: compare <testout> <baseline>")
        sys.exit(1)

    # open the first file
    file = open(sys.argv[1], "r")
    for line in file:
        # see if we already have this line
        found = False
        for l2 in matrix1:
            if (l2['line'] == line):
                l2['num'] = l2['num'] + 1
                found = True
                break
        if not found:
            matrix1.append({'line': line, 'num': 1, 'found': 0})
    file.close()

    # open in second file
    file = open(sys.argv[2], "r")
    for line in file:
        found = False
        for l in matrix1:
            if (l['line'] == line):
                l['found'] = l['found'] + 1
                found = True
        if not found:
            missing.append(line)
    file.close()

    if (0 < len(missing)):
        exitcode = 1
        print("LINES MISSING FROM", sys.argv[1])
        for l in missing:
            print(l)

    # check for mismatched numbers of occurrences
    # of lines
    for l in matrix1:
        if (l['found'] != l['num']):
            extras.append(l)
    
    if (0 < len(extras)):
        exitcode = 1
        print("MISMATCHED OCCURRENCES - COMPARING SOURCE", sys.argv[1], "TO BASELINE", sys.argv[2])
        for l in extras:
            print("SOURCE", l['num'], " BASELINE:", l['found'], " LINE:", l['line'])

    sys.exit(exitcode)
    
if __name__ == '__main__':
    main()
