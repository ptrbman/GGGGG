import subprocess
import re
import os
from pathlib import Path

# Remove strange characters from output when parsing results
def escape_ansi(line):
    ansi_escape = re.compile(r'(?:\x1B[@-_]|[\x80-\x9F])[0-?]*[ -/]*[@-~]')
    return ansi_escape.sub('', line)


# Runs verifyta on infile and queryfile, and parses result to figure out the answers
def runUPPAAL(verifytaLocation, infile, queryfile, outputfile, verbose=False):
    cmdPath = str(Path(verifytaLocation).absolute())
    inPath = str(Path(infile).absolute())
    queryPath = str(Path(queryfile).absolute())
    outPath = str(Path(outputfile).absolute())
    # cmd = "\"" + verifytaLocation + "\" \"" + str(infile) + "\" \"" + queryfile + "\" > " + "\"" + outputfile + "\""
    
    cmd = cmdPath + " " + inPath + " " + queryPath +  " > " + outPath
    # print("\n\t", cmd)
    os.system(cmd)

    f = open(outPath, "r")
    answers = []
    curquery = -1
    for ll in f:
        l = escape_ansi(ll)
        if re.search(r"Verifying formula.*", l) != None:
            curquery = int(re.search(r"[0-9]+", l)[0])
        elif re.search(r"Formula is satisfied", l):
            answers.append((curquery, "sat"))
        elif re.search(r"Formula is NOT satisfied", l):
            answers.append((curquery, "unsat"))
        elif l.isspace():
            True
        elif re.search(r"Options for the", l):
            True
        elif re.search(r"Generating", l):
            True
        elif re.search(r"Search order is", l):
            True
        elif re.search(r"Using conservative", l):
            True
        elif re.search(r"Seed is", l):
            True
        elif re.search(r"State space", l):
            True
        elif re.search(r"Options for the", l):
            True
        elif re.search(r"Options for the", l):
            True
        else:
            if (verbose):
                print("runUPPAAL: unhandled input: ", l)
    return answers
