#!/usr/bin/env -S python3 -u

import sys
import os
import re
import argparse
import subprocess
import shutil

args = None
all_triage_symbols = []

def extract_git_info(dir):
    prev_cwd = os.getcwd()
    os.chdir(dir)

    git_branch = None
    git_hash = None

    p = subprocess.Popen("git rev-parse --abbrev-ref HEAD",
                        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True, close_fds=True)
    p.wait()
    if p.returncode != 0:
        print("Error: Failed to extract the git branch in the directory. "+dir+" Error code "+str(p.returncode)+")");
        os.chdir(prev_cwd)
        return "Unknown"

    for line in p.stdout:
        line = line.rstrip()
        line = line.decode()
        git_branch = line
        break

    p = subprocess.Popen("git rev-parse --short HEAD",
                        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True, close_fds=True)
    p.wait()
    if p.returncode != 0:
        print("Error: Failed to extract the git revision in the directory. "+dir+" Error code "+str(p.returncode)+")");
        os.chdir(prev_cwd)
        return "Unknown"

    for line in p.stdout:
        line = line.rstrip()
        line = line.decode()
        git_hash = line
        break

    os.chdir(prev_cwd)
    if git_branch is not None and git_hash is not None:
        return git_branch +" ("+git_hash+")"
    else:
        return "Unknown"


def extract_triage(triage_file):
    """Extract traige symbols"""

    global args
    triage_symbols = []

    with open(args.triage_file, 'r') as tf:
        for line in tf:
            line = line.rstrip()

            # Line comments
            m = re.match(r'^#', line)
            if m is not None:
                continue

            # Empty lines
            m = re.match(r'^\s*$', line)
            if m is not None:
                continue

            triage_symbols.append(line)

    return triage_symbols

def pmix_standard_encode(ref_str):
    """Encode the PMIx Standard LaTeX reference string as something more readable"""

    if ref_str == "apifn":
        return "API"
    elif ref_str == "attr":
        return "attribute"
    elif ref_str == "const":
        return "constant"
    elif ref_str == "envar":
        return "envar"
    elif ref_str == "macro":
        return "macro"
    elif ref_str == "struct":
        return "struct"
    else:
        print("Error: Unknown reference: "+ref_str)
        os._exit(1)

def extract_pmix_standard(pmix_standard_dir):
    """Extract symbols from the PMIx Standard"""

    global args
    all_symbols = {}
    all_symbols_raw = {}
    std_deprecated = {}
    std_removed = {}

    # --------------------------------------------------
    # attributes - grep "newlabel{attr" pmix-standard.aux
    # consts     - grep "newlabel{const" pmix-standard.aux
    # structs    - grep "newlabel{struct" pmix-standard.aux
    # macros     - grep "newlabel{macro" pmix-standard.aux
    # apis       - grep "newlabel{api" pmix-standard.aux
    # envars     - grep "newlabel{envar" pmix-standard.aux
    # --------------------------------------------------
    all_ref_strs = ["attr", "const", "struct", "macro", "apifn", "envar"]
    for ref_str in all_ref_strs:
        cur_set_of_symbols = {}

        if args.verbose is True:
            print ("-"*5 + "> Extracting PMIx Standard: \""+ref_str+"\"")

        # Exclude:
        #   subsection.A => Appendix A: Python Bindings
        p = subprocess.Popen("grep \"newlabel{"+ref_str+"\" "+pmix_standard_dir+"/pmix-standard.aux | grep -v subsection.A",
                             stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True, close_fds=True)
        p.wait()
        if p.returncode != 0:
            print("Error: Failed to extract declared \""+ref_str+"\". grep error code "+str(p.returncode)+")");
            sys.exit(2)

        for line in p.stdout:
            line = line.rstrip()
            line = line.decode()
            m = re.match(r"\s*\\newlabel{"+ re.escape(ref_str) + r":(\w+)", line)
            if m is None:
                print("Error: Failed to extract an \""+ref_str+"\" on the following line")
                print(" line: "+line)
                sys.exit(1)

            # Count will return to 0 when verified
            all_symbols_raw[m.group(1)] = -1
            if "Deprecated" in line:
                std_deprecated[m.group(1)] = -1
            elif re.search('removed', line, re.IGNORECASE):
                std_removed[m.group(1)] = -1
            else:
                cur_set_of_symbols[m.group(1)] = -1

        all_symbols[pmix_standard_encode(ref_str)] = cur_set_of_symbols

    all_symbols['deprecated'] = std_deprecated
    all_symbols['removed'] = std_removed

    # --------------------------------------------------
    if args.verbose is True:
        print ("-"*50)
        for ref_str in sorted(all_symbols):
            print("PMIx Standard Reference \"%10s\" : %4d" % (ref_str, len(all_symbols[ref_str])))
            if args.debug is True:
                for val in sorted(all_symbols[ref_str]):
                    print("  +---> " + val)
        print ("-"*50)

    return all_symbols

def extract_openpmix(openpmix_dir):
    """Extract symbols from OpenPMIx"""

    global args
    all_symbols = {}
    openpmix_deprecated = {}

    openpmix_defines = {}
    openpmix_structs = {}
    openpmix_apis = {}
    openpmix_cbs = {}
    openpmix_all_refs = {}

    # Extract the header files
    openpmix_files = []
    for fname in os.listdir(openpmix_dir + "/include"):
        m = re.search(r'.h', fname)
        if m is not None:
            m = re.search(r'pmi[2]?.h', fname) # Exclude pmi.h and pmi2.h
            if m is None:
                openpmix_files.append(fname)

    # For each header file, extract the symbols
    for openpmix_file in sorted(openpmix_files):
        openpmix_file = openpmix_dir + "/include/" + openpmix_file
        if args.verbose is True:
            print("-"*5 + "> Extracting OpenPMIx Definitions from: " + openpmix_file)

        if "deprecated.h" in openpmix_file:
            parse_deprecated = True
        else:
            parse_deprecated = False
        parse_active = False
        parse_enum = False
        parse_struct = False
        defs_found = 0
        with open(openpmix_file) as fp:
            for line in fp:
                line = line.rstrip()

                m = re.match(r'extern "C"', line);
                if m is None and parse_active is False:
                    continue
                else:
                    parse_active = True

                # typedef enum {
                m = re.match(r'\s*typedef\s+enum\s*', line);
                if m is not None:
                    parse_enum = True
                    continue
                if parse_enum is True:
                    m = re.match(r'\s*}\s*(pmi\w*)', line)
                    if m is not None:
                        if parse_deprecated:
                            openpmix_deprecated[m.group(1)] = -1
                        else:
                            openpmix_structs[m.group(1)] = -1
                            openpmix_all_refs[m.group(1)] = -1
                        defs_found = defs_found + 1
                        parse_enum = False
                        continue
                    m = re.match(r'\s+(\w+)', line)
                    if m is not None:
                        if parse_deprecated:
                            openpmix_deprecated[m.group(1)] = -1
                        else:
                            openpmix_defines[m.group(1)] = -1
                            openpmix_all_refs[m.group(1)] = -1
                        defs_found = defs_found + 1
                        continue

                # typedef struct pmix_data_buffer {
                m = re.match(r'\s*typedef\s+struct\s*\w+\s+{', line);
                if m is not None:
                    parse_struct = True
                    continue
                else:
                    m = re.match(r'\s*typedef\s+struct\s*{', line);
                    if m is not None:
                        parse_struct = True
                        continue
                if parse_struct is True:
                    m = re.match(r'\s*}\s*(pmi\w+)', line)
                    if m is not None:
                        if parse_deprecated:
                            openpmix_deprecated[m.group(1)] = -1
                        else:
                            openpmix_structs[m.group(1)] = -1
                            openpmix_all_refs[m.group(1)] = -1
                        defs_found = defs_found + 1
                        parse_struct = False
                        continue
                    else:
                        continue

                # typedef uint8_t pmix_data_range_t;
                m = re.match(r'\s*typedef\s*\w*\s*(pmi\w*)[;|\[]', line);
                if m is not None:
                    if parse_deprecated:
                        openpmix_deprecated[m.group(1)] = -1
                    else:
                        openpmix_structs[m.group(1)] = -1
                        openpmix_all_refs[m.group(1)] = -1
                    defs_found = defs_found + 1
                    continue

                # #define PMIX_EVENT_BASE                     "pmix.evbase"
                m = re.match(r'#define\s+(\w+)\(', line);
                if m is not None:
                    if parse_deprecated:
                        openpmix_deprecated[m.group(1)] = -1
                    else:
                        openpmix_defines[m.group(1)] = -1
                        openpmix_all_refs[m.group(1)] = -1
                    defs_found = defs_found + 1
                    continue

                # #define PMIx_Heartbeat()
                m = re.match(r'#define\s+(\w+)', line);
                if m is not None:
                    if parse_deprecated:
                        openpmix_deprecated[m.group(1)] = -1
                    else:
                        openpmix_defines[m.group(1)] = -1
                        openpmix_all_refs[m.group(1)] = -1
                    defs_found = defs_found + 1
                    continue

                # PMIX_EXPORT const char* PMIx_Error_string
                m = re.match(r'PMIX_EXPORT\s+\w+\s+\w+\*\s+(PMI\w+)', line);
                if m is not None:
                    if parse_deprecated:
                        openpmix_deprecated[m.group(1)] = -1
                    else:
                        openpmix_apis[m.group(1)] = -1
                        openpmix_all_refs[m.group(1)] = -1
                    defs_found = defs_found + 1
                    continue

                # PMIX_EXPORT <type>* PMI<function>
                m = re.match(r'PMIX_EXPORT\s+\w+\*\s+(PMI\w+)', line);
                if m is not None:
                    if parse_deprecated:
                        openpmix_deprecated[m.group(1)] = -1
                    else:
                        openpmix_apis[m.group(1)] = -1
                        openpmix_all_refs[m.group(1)] = -1
                    defs_found = defs_found + 1
                    continue

                # PMIX_EXPORT <type>** PMI<function>
                m = re.match(r'PMIX_EXPORT\s+\w+\*+\*+\s+(PMI\w+)', line);
                if m is not None:
                    if parse_deprecated:
                        openpmix_deprecated[m.group(1)] = -1
                    else:
                        openpmix_apis[m.group(1)] = -1
                        openpmix_all_refs[m.group(1)] = -1
                    defs_found = defs_found + 1
                    continue

                # PMIX_EXPORT <type> *PMI<function>
                m = re.match(r'PMIX_EXPORT\s+\w+\s+\*+(PMI\w+)', line);
                if m is not None:
                    if parse_deprecated:
                        openpmix_deprecated[m.group(1)] = -1
                    else:
                        openpmix_apis[m.group(1)] = -1
                        openpmix_all_refs[m.group(1)] = -1
                    defs_found = defs_found + 1
                    continue

                # PMIX_EXPORT <type> **PMI<function>
                m = re.match(r'PMIX_EXPORT\s+\w+\s+\*+\*+(PMI\w+)', line);
                if m is not None:
                    if parse_deprecated:
                        openpmix_deprecated[m.group(1)] = -1
                    else:
                        openpmix_apis[m.group(1)] = -1
                        openpmix_all_refs[m.group(1)] = -1
                    defs_found = defs_found + 1
                    continue

                # PMIX_EXPORT pmix_status_t PMIx_Init(
                m = re.match(r'PMIX_EXPORT\s+\w+\s+(PMI\w+)', line);
                if m is not None:
                    if parse_deprecated:
                        openpmix_deprecated[m.group(1)] = -1
                    else:
                        openpmix_apis[m.group(1)] = -1
                        openpmix_all_refs[m.group(1)] = -1
                    defs_found = defs_found + 1
                    continue

                # typedef void (*pmix_iof_cbfunc_t)(
                m = re.match(r'\s*typedef\s+\w+\s+\(\*(\w+)', line);
                if m is not None:
                    if parse_deprecated:
                        openpmix_deprecated[m.group(1)] = -1
                    else:
                        openpmix_cbs[m.group(1)] = -1
                        openpmix_all_refs[m.group(1)] = -1
                    defs_found = defs_found + 1
                    continue

    all_symbols['define'] = openpmix_defines
    all_symbols['struct'] = openpmix_structs
    all_symbols['API'] = openpmix_apis
    all_symbols['callback'] = openpmix_cbs

    # Prune the deprecated list
    # Note: Some items are declared in both the pmix.h and pmix_deprecated.h
    #       to make the old interfaces easier to access. Remove those duplicates.
    for ref_str in all_symbols:
        for val in all_symbols[ref_str]:
            if val in openpmix_deprecated.keys():
                del openpmix_deprecated[val]
    all_symbols['deprecated'] = openpmix_deprecated

    if args.verbose is True:
        print ("-"*50)
        for ref_str in sorted(all_symbols):
            print("OpenPMIx Reference \"%10s\" : %4d" % (ref_str, len(all_symbols[ref_str])))
            if args.debug is True:
                for val in sorted(all_symbols[ref_str]):
                    print("  +---> " + val)
        print ("-"*50)

    return all_symbols

def compare_openpmix_to_pmix_standard(openpmix_symbols, pmix_standard_symbols, all_triage_symbols):
    """Compare OpenPMIx symbols to PMIx Standard"""

    if args.verbose is True:
        print ("-"*5 + "> Checking for OpenPMIx symbols not in the PMIx Standard")

    # Flatten the lists
    all_openpmix_symbols = {}
    for ref_str in openpmix_symbols:
        for val in openpmix_symbols[ref_str]:
            all_openpmix_symbols[val] = -1;
    all_pmix_standard_symbols = {}
    for ref_str in pmix_standard_symbols:
        for val in pmix_standard_symbols[ref_str]:
            all_pmix_standard_symbols[val] = -1;

    # Iterate through the lists to find missing references
    all_missing_refs = {}
    missing_refs = []
    missing_refs_triaged = []
    for openpmix_ref in all_openpmix_symbols:
        found_ref = False

        # Symbol in both OpenPMIx and PMIx Standard
        if openpmix_ref in all_pmix_standard_symbols.keys():
            found_ref = True

        # Exclude deprecated symbols
        if found_ref is False:
            if openpmix_ref in openpmix_symbols['deprecated'].keys():
                found_ref = True

        # Exclude triaged symbols
        if found_ref is False:
            if openpmix_ref in all_triage_symbols:
                missing_refs_triaged.append(openpmix_ref)
                found_ref = True

        # Found a missing symbol
        if found_ref is False:
            missing_refs.append(openpmix_ref)

    all_missing_refs['missing'] = missing_refs
    all_missing_refs['triaged'] = missing_refs_triaged
    return all_missing_refs

def compare_pmix_standard_to_openpmix(openpmix_symbols, pmix_standard_symbols, all_triage_symbols):
    """Compare PMIx Standard symbols to OpenPMIx"""

    if args.verbose is True:
        print ("-"*5 + "> Checking for PMIx Standard symbols not in OpenPMIx")

    # Flatten the lists
    all_openpmix_symbols = {}
    for ref_str in openpmix_symbols:
        for val in openpmix_symbols[ref_str]:
            all_openpmix_symbols[val] = -1;
    all_pmix_standard_symbols = {}
    for ref_str in pmix_standard_symbols:
        for val in pmix_standard_symbols[ref_str]:
            all_pmix_standard_symbols[val] = -1;

    # Iterate through the lists to find missing references
    all_missing_refs = {}
    missing_refs = []
    missing_refs_triaged = []
    for pmix_standard_ref in all_pmix_standard_symbols:
        found_ref = False

        # Symbol in both OpenPMIx and PMIx Standard
        if pmix_standard_ref in all_openpmix_symbols.keys():
            found_ref = True

        # Exclude deprecated and removed
        if found_ref is False:
            if pmix_standard_ref in pmix_standard_symbols['deprecated'].keys():
                found_ref = True
            elif pmix_standard_ref in pmix_standard_symbols['removed'].keys():
                found_ref = True

        # Exclude triaged symbols
        if found_ref is False:
            if pmix_standard_ref in all_triage_symbols:
                missing_refs_triaged.append(pmix_standard_ref)
                found_ref = True

        # Found a missing symbol
        if found_ref is False:
            missing_refs.append(pmix_standard_ref)

    all_missing_refs['missing'] = missing_refs
    all_missing_refs['triaged'] = missing_refs_triaged
    return all_missing_refs

if __name__ == "__main__":

    #
    # Command line parsing
    #
    parser = argparse.ArgumentParser(description="PMIx Standard / OpenPMIx Cross Check")
    parser.add_argument("-v", "--verbose", help="Verbose output", action="store_true")
    parser.add_argument("-d", "--debug", help="Extra debug output", action="store_true")
    parser.add_argument("-o", "--openpmix", help="OpenPMIx checkout directory", nargs='?', default='scratch/openpmix', dest="openpmix_dir")
    parser.add_argument("-s", "--standard", help="PMIx Standard checkout directory", nargs='?', default='scratch/pmix-standard', dest="pmix_standard_dir")
    parser.add_argument("-t", "--triage", help="Traige file of symbols in OpenPMIx not in PMIx Standard", required=False, dest="triage_file")

    parser.parse_args()
    args = parser.parse_args()

    if args.debug is True:
        args.verbose = True

    #
    # OpenPMIx
    #
    if args.openpmix_dir is not None and os.path.isdir(args.openpmix_dir) is False:
        print("Error: OpenPMIx directory not found. " + args.openpmix_dir)
        os._exit(1)

    #
    # PMIx Standard
    #
    if args.pmix_standard_dir is not None and os.path.isdir(args.pmix_standard_dir) is False:
        print("Error: PMIx Standard directory not found. " + args.pmix_standard_dir)
        os._exit(1)

    if os.path.isfile(args.pmix_standard_dir + "/pmix-standard.aux") is False:
        print("Error: PMIx Standard was not compiled. Missing: " + args.pmix_standard_dir + "/pmix-standard.aux")
        os._exit(1)

    #
    # Triage file
    #
    if args.triage_file is not None and os.path.isfile(args.triage_file) is False:
        print("Error: Triage File not found. " + args.triage_file)
        os._exit(1)

    if args.triage_file is not None:
        all_triage_symbols = extract_triage(args.triage_file)

    #
    # Diagnostic output
    #
    print("-"*50)
    print("OpenPMIx Directory     : " + args.openpmix_dir)
    print("             Git Info. : " + extract_git_info(args.openpmix_dir))
    print("PMIx Standard Directory: " + args.pmix_standard_dir)
    print("             Git Info. : " + extract_git_info(args.pmix_standard_dir))
    if args.triage_file is not None:
        print("Traige file            : " + args.triage_file)
    print("-"*50)

    #
    # Extract symbols from PMIx Standard
    #
    pmix_standard_symbols = extract_pmix_standard(args.pmix_standard_dir)

    #
    # Extract symbols from OpenPMIx
    #
    openpmix_symbols = extract_openpmix(args.openpmix_dir)

    #
    # Check: Items defined in OpenPMIx are in the PMIx Standard
    #
    missing_from_pmix_standard = compare_openpmix_to_pmix_standard(openpmix_symbols, pmix_standard_symbols, all_triage_symbols)
    total_missing_pmix_standard = len(missing_from_pmix_standard['missing'])

    #
    # Check: Items defined in PMIx Standard are in OpenPMIx
    #
    missing_from_openpmix = compare_pmix_standard_to_openpmix(openpmix_symbols, pmix_standard_symbols, all_triage_symbols)
    total_missing_openpmix = len(missing_from_openpmix['missing'])

    print("%4d : Symbols missing from the PMIx Standard defined by OpenPMIx" % (total_missing_pmix_standard))
    print("%4d : Symbols missing from OpenPMIx defined by the PMIx Standard" % (total_missing_openpmix))
    print("%4d : Symbols in triage file" % (len(all_triage_symbols)))

    #
    # Double check the triage list
    #
    for t_ref in missing_from_pmix_standard['triaged']:
        if t_ref in all_triage_symbols:
            all_triage_symbols.remove(t_ref)
    for t_ref in missing_from_openpmix['triaged']:
        if t_ref in all_triage_symbols:
            all_triage_symbols.remove(t_ref)

    total_triage_leftovers = len(all_triage_symbols)
    print("%4d : Symbols in triage file that were not missing." % (total_triage_leftovers))

    #
    # Final output
    #
    print("-"*50)

    if total_missing_pmix_standard == 0 and total_missing_openpmix == 0 and total_triage_leftovers == 0:
        print("Success! No missing symbols found!")
        os._exit(0)
    else:
        if total_missing_pmix_standard > 0:
            print("===> PMIx Standard is missing the following %d symbols:" % (total_missing_pmix_standard))
            print("-"*25)
            for val in sorted(missing_from_pmix_standard['missing']):
                print(val)

        if total_missing_openpmix > 0:
            print("===> OpenPMIx is missing the following %d symbols:" % (total_missing_openpmix))
            print("-"*25)
            for val in sorted(missing_from_openpmix['missing']):
                print(val)

        if total_triage_leftovers > 0:
            print("===> Warning: %d symbols in the Triage file were not found to be missing. Check the triage file" % (total_triage_leftovers))
            for t_ref in sorted(all_triage_symbols):
                print(t_ref)
            print("-"*50)

        os._exit(total_missing_pmix_standard + total_missing_openpmix + total_triage_leftovers)

    # --------------------------------------------------
    # Check to make sure that all of the items defined in OpenPMIx are in the PMIx Standard
    # - except for those explicitly excluded
    # --------------------------------------------------
    total_missing_refs = 0

    missing_refs = check_missing_pmix_standard(std_all_refs, openpmix_all_refs,
                                               std_deprecated, std_removed,
                                               openpmix_deprecated,
                                               args.verbose)
    total_missing_refs = total_missing_refs + len(missing_refs)
    if len(missing_refs) > 0:
        print ("-"*50)
        print("Found "+str(len(missing_refs))+" references defined in OpenPMIx, but not in the PMIx Standard")
        for ref in sorted(missing_refs):
            print("PMIx Standard Missing: "+ref)
        print("")

    if len(all_triage_symbols) > 0:
        print("-"*50)
        print("Found "+str(len(all_triage_symbols))+" references defined in the Triage file, but were not listed as in OpenPMIx, but not in the PMIx Standard")
        print("Please check these references in your traige file!")

        for ref in sorted(all_triage_symbols):
            print("Triage Reference: "+ref)


    # --------------------------------------------------
    # Check to make sure that all of the items defined in the PMIx Standard are in OpenPMIx
    # --------------------------------------------------
    missing_refs = check_missing_openpmix(std_all_refs, openpmix_all_refs,
                                          std_deprecated, std_removed,
                                          openpmix_deprecated, args.verbose)
    total_missing_refs = total_missing_refs + len(missing_refs)
    if len(missing_refs) > 0:
        print ("-"*50)
        print("Found "+str(len(missing_refs))+" references defined in PMIx Standard, but not in OpenPMIx")
        for ref in sorted(missing_refs):
            print("OpenPMIx Missing: "+ref)
        print("")


    # Return the total number of missing references
    sys.exit(total_missing_refs)

