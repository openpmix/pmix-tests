#!/usr/bin/python

#
# To build only: (-q = quiet mode)
#  ./bin/cvc-0-setup-builds.py -r -q
# To run only:
#  ./bin/cvc-0-setup-builds.py -b -q
#

import sys
import os
import re
import argparse
import subprocess

pmix_git_url      = "git@github.com:pmix/pmix.git"
pmix_release_url  = "https://github.com/pmix/pmix/releases/download/"
pmix_base_dir     = "/tmp/pmix-test/"
pmix_install_dir  = pmix_base_dir + "/install/"
pmix_build_dir    = pmix_base_dir
pmix_libevent_dir = "/tmp/pmix-test/libevent"

args = None
output_file = os.getcwd() + "/build_output.txt"
result_file = os.getcwd() + "/run_result.txt"

final_summary = []

class BuildInfo:
    def __init__(self):
        global pmix_git_url

        self.branch = None
        self.is_git = True
        self.url = pmix_git_url
        self.build_base_dir = None
        self.build_install_dir = None

    def sync(self):
        global pmix_install_dir

        if self.branch is None:
            print "Error: Branch must be defined"
            sys.exit(1)
        if self.build_base_dir is None:
            self.build_base_dir = "pmix-" + self.branch
        if self.build_install_dir is None:
            self.build_install_dir = pmix_install_dir + self.build_base_dir

    def display(self):
        print("Branch: %6s" % (self.branch))

def build_tree(bld, logfile=None):
    global pmix_libevent_dir
    global pmix_build_dir
    global pmix_install_dir
    global output_file
    global args

    orig_dir = os.getcwd()

    if os.path.isdir(pmix_build_dir + bld_server.build_base_dir) is False:
        if bld.is_git is True:
            print("============ PMIx Build: "+bld.branch+" : Git Clone")
            ret = subprocess.call(["git", "clone",
                                   "-b", bld.branch,
                                   bld.url, pmix_build_dir + bld_server.build_base_dir],
                                   stdout=logfile, stderr=logfile, shell=False)
            if 0 != ret:
                os.chdir(orig_dir)
                return ret
        else:
            print("============ PMIx Build: "+bld.branch+" : Unpack tarball")
            ret = subprocess.call(["wget",bld.url], stdout=logfile, stderr=logfile, shell=False)
            if 0 != ret:
                os.chdir(orig_dir)
                return ret
            print("============ Error: non-git builds not yet supported")
            # TODO
            os.chdir(orig_dir)
            return -1;

    os.chdir(pmix_build_dir + bld_server.build_base_dir)
    print("============ PMIx Build: "+bld.branch+" : "+os.getcwd())

    print("============ PMIx Build: "+bld.branch+" : Autogen")
    if os.path.exists("autogen.pl") is True:
        ret = subprocess.call(["./autogen.pl"], stdout=logfile, stderr=logfile, shell=False)
    else:
        ret = subprocess.call(["./autogen.sh"], stdout=logfile, stderr=logfile, shell=False)
    if 0 != ret:
        os.chdir(orig_dir)
        return ret

    print("============ PMIx Build: "+bld.branch+" : Configure")
    ret = subprocess.call(["./configure",
                           "--disable-debug",
                           "--enable-static",
                           "--disable-shared",
                           "--disable-dlopen",
                           "--disable-per-user-config-files",
                           "--with-libevent=" + pmix_libevent_dir,
                           "--prefix=" + pmix_install_dir + "/" + bld.build_base_dir],
                           stdout=logfile, stderr=logfile, shell=False)
    if 0 != ret:
        os.chdir(orig_dir)
        return ret

    print("============ PMIx Build: "+bld.branch+" : Make")
    ret = subprocess.call(["make"], stdout=logfile, stderr=logfile, shell=False)
    if 0 != ret:
        os.chdir(orig_dir)
        return ret

    print("============ PMIx Build: "+bld.branch+" : Make Install")
    ret = subprocess.call(["make", "install"], stdout=logfile, stderr=logfile, shell=False)
    if 0 != ret:
        os.chdir(orig_dir)
        return ret

    print("============ PMIx Build: "+bld.branch+" : Make Test")
    os.chdir(pmix_build_dir + bld_server.build_base_dir + "/test/simple")
    ret = subprocess.call(["make"], stdout=logfile, stderr=logfile, shell=False)
    if 0 != ret:
        os.chdir(orig_dir)
        return ret

    print("============ PMIx Build: "+bld.branch+" : Done " + orig_dir)
    os.chdir(orig_dir)
    return ret

def run_test(bld_server, bld_client):
    global pmix_build_dir
    global result_file

    orig_dir = os.getcwd()
    os.chdir(pmix_build_dir + bld_server.build_base_dir + "/test/simple")

    print("============ PMIx Run  : Run simptest")
    with open(result_file, 'w') as logfile:
        ret = subprocess.call(["./simptest",
                               "-n", "2",
                               "-e", pmix_build_dir + bld_client.build_base_dir + "/test/simple/simpclient"],
                               stdout=logfile, stderr=logfile, shell=False)
        if 0 != ret:
            os.chdir(orig_dir)
            return ret

    if args.quiet is False:
        with open(result_file, 'r') as logfile:
            for line in logfile:
                print(line),
        print("")

    os.chdir(orig_dir)
    return ret

if __name__ == "__main__":
    allBuilds = []
    invalid_pairs = []

    # Command line parsing
    parser = argparse.ArgumentParser(description="PMIx Cross Version Check Script")
    parser.add_argument("-b", "--no-build", help="Skip building PMIx", action="store_true")
    parser.add_argument("-r", "--no-run", help="Skip running PMIx", action="store_true")
    parser.add_argument("-q", "--quiet", help="Quiet Output (output in output.txt)", action="store_true")
    parser.parse_args()
    args = parser.parse_args()

    if args.quiet is True:
        if os.path.exists(output_file):
            os.system("rm " + output_file)

    # 'server' -> 'client' pairs that are not supported
    invalid_pairs.append(["v1.2","master"])
    invalid_pairs.append(["v1.2","v3.0"])
    invalid_pairs.append(["v1.2","v2.1"])
    invalid_pairs.append(["v1.2","v2.0"])
    # --
    invalid_pairs.append(["v2.0","master"])
    invalid_pairs.append(["v2.0","v3.0"])
    invalid_pairs.append(["v2.0","v2.1"])

    # Git master
    bld = BuildInfo()
    bld.branch = "master"
    bld.sync()
    allBuilds.append(bld)

    # Git v3.0
    bld = BuildInfo()
    bld.branch = "v3.0"
    bld.sync()
    allBuilds.append(bld)

    # Git v2.1
    bld = BuildInfo()
    bld.branch = "v2.1"
    bld.sync()
    allBuilds.append(bld)

    # Git v2.0
    bld = BuildInfo()
    bld.branch = "v2.0"
    bld.sync()
    allBuilds.append(bld)

    # Git v1.2
    bld = BuildInfo()
    bld.branch = "v1.2"
    bld.sync()
    allBuilds.append(bld)

    # Tar v3.0.0
    # bld = BuildInfo()
    # bld.branch = "v3.0.0"
    # bld.is_git = False
    # bld.url = pmix_release_url + "v3.0.0/pmix-3.0.0.tar.bz2"
    # bld.sync()
    # allBuilds.append(bld)

    if args.no_build is False:
        for bld_server in allBuilds:
            print("============ PMIx Build: "+bld_server.branch+" =====================")
            if args.quiet is True:
                with open(output_file, 'a') as logfile:
                    logfile.write("============ PMIx Build: "+bld_server.branch+" =====================")
                    logfile.flush()
                    ret = build_tree(bld_server, logfile)
            else:
                ret = build_tree(bld_server)

            if 0 == ret:
                final_summary.append("Build PASS: "+bld_server.branch+" -> "+bld_server.build_base_dir)
            else:
                final_summary.append("Build FAIL: "+bld_server.branch+" -> "+bld_server.build_base_dir)

    if args.no_run is False:
        for bld_server in allBuilds:
            for bld_client in allBuilds:
                is_valid = True
                for pair in invalid_pairs:
                    if bld_server.branch is pair[0] and bld_client.branch is pair[1]:
                        is_valid = False

                if is_valid:
                    print("="*70)
                    print("Server: %6s -> Client: %6s" % (bld_server.branch, bld_client.branch))
                    ret = run_test(bld_server, bld_client)
                    if 0 == ret:
                        final_summary.append("Run PASS: "+bld_server.branch+" -> "+bld_client.branch)
                    else:
                        final_summary.append("Run FAIL: "+bld_server.branch+" -> "+bld_client.branch)

    print("="*30 + " Summary " + "="*30)
    for line in final_summary:
        print line