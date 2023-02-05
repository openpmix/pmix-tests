#!/usr/bin/env python3

import sys
import errno

def main():
    matrix1 = []
    matrix2 = []
    missing = []
    extras = []
    mismatched = []
    exitcode = 0

    if (3 != len(sys.argv)):
        print("Usage: compare <testout> <baseline>")
        sys.exit(1)

    # open the test output file
    try:
        file = open(sys.argv[1], "r")
    except (OSError, IOError) as e:
        if getattr(e, 'errno', 0) == errno.ENOENT:
            print("Error opening", sys.argv[1], ": not found")
        elif getattr(e, 'errno', 0) == errno.EACCES:
            print("Error opening", sys.argv[1], ": access denied")
        else:
            print("Error opening", sys.argv[1], ":", e.value)
        sys.exit(1)

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

    # open baseline file - check for lines in the
    # baseline that are missing from the test
    # output, and count the number of times we
    # find each matching line. Cache the baseline
    # for later
    try:
        file = open(sys.argv[2], "r")
    except (OSError, IOError) as e:
        if getattr(e, 'errno', 0) == errno.ENOENT:
            print("Error opening", sys.argv[2], ": not found")
        elif getattr(e, 'errno', 0) == errno.EACCES:
            print("Error opening", sys.argv[2], ": access denied")
        else:
            print("Error opening", sys.argv[2], ":", e.value)
        sys.exit(1)

    for line in file:
        found = False
        matrix2.append(line)
        for l in matrix1:
            if (l['line'] == line):
                l['found'] = l['found'] + 1
                found = True
                break
        if not found:
            missing.append(line)
    file.close()

    # output any missing lines
    if (0 < len(missing)):
        exitcode = 1
        print("LINES MISSING FROM", sys.argv[1])
        for l in missing:
            print(l)
        print("")

    # check for lines that are in the test output
    # but are missing from the baseline. No
    # need to count matches here as we already
    # did that test
    for line in matrix1:
        found = False
        for l in matrix2:
            if (l == line['line']):
                found = True
                break
        if not found:
            extras.append(line['line'])

    # output any extra lines
    if (0 < len(extras)):
        exitcode = 1
        print("EXTRA LINES IN TEST OUTPUT", sys.argv[1])
        for l in extras:
            print(l)
        print("")

    # check for mismatched numbers of occurrences
    # of lines
    for l in matrix1:
        if (l['found'] != l['num']):
            # if the line is in "extras", then
            # we ignore it here
            found = False
            for l2 in extras:
                if (l['line'] == l2):
                    found = True
                    break;
            if not found:
                mismatched.append(l)

    # output mismatched numbers of lines
    if (0 < len(mismatched)):
        exitcode = 1
        print("MISMATCHED OCCURRENCES - COMPARING SOURCE", sys.argv[1], "TO BASELINE", sys.argv[2])
        for l in mismatched:
            print("SOURCE", l['num'], " BASELINE:", l['found'], " LINE:", l['line'])

    sys.exit(exitcode)
    
if __name__ == '__main__':
    main()
