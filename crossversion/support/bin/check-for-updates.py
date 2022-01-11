#!/usr/bin/python -u

#
#
#

import sys
import os
import re
import argparse
import subprocess
import shutil

# put this in one place
supported_versions = ["master", "v4.1", "v4.0", "v3.2", "v3.1", "v3.0", "v2.2", "v2.1", "v2.0", "v1.2"]

pmix_git_url      = "https://github.com/pmix/pmix.git"
pmix_release_url  = "https://github.com/pmix/pmix/releases/download/"
pmix_install_dir  = ""
pmix_build_dir    = ""

args = None

final_summary = []

count_rebuild=0

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

def check_tree(bld, logfile=None):
    global pmix_build_dir
    global pmix_install_dir
    global args

    orig_dir = os.getcwd()

    local_build_dir   = pmix_build_dir + "/" + bld_server.build_base_dir
    local_install_dir = pmix_install_dir + "/" + bld.build_base_dir

    # If the build directory exists see if we need to update+rebuild, rebuild, or skip.
    if os.path.isdir(local_build_dir) and os.path.isdir(local_install_dir):
        os.chdir(local_build_dir)

        # Not a .git repo
        # if the install dir is present then skip
        if os.path.exists(".git") is False:
            if os.path.isdir(local_install_dir) is True:
                print("Skip: Local install already exists: "+local_install_dir)
                return 1
        # .git repo
        # if there is an upstream update for this branch then rebuild, otherwise skip.
        else:
            ret = subprocess.call(["git", "fetch", "-q", "origin", bld.branch],
                                   stdout=logfile, stderr=logfile, shell=False)
            if 0 != ret:
                os.chdir(orig_dir)
                return ret

            p = subprocess.Popen("git pull origin "+bld.branch,
                                 stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True, close_fds=True)
            p.wait()
            if p.returncode != 0:
                os.chdir(orig_dir)
                return -1

            os.chdir(orig_dir)

            sio = p.stdout.read()
            if "Already up-to-date" in sio:
                print("Skip: Local install already exists ("+local_install_dir+") and branch ("+bld.branch+") has no updates")
                return 1
            else:
                print("\"git pull\" indicated a change on this branch. Flag for rebuild")
                print("Log:\n"+sio)
                return 0

        os.chdir(orig_dir)
    else:
        print("Skip: No local install present for this version.")
        return 1

    return 0

if __name__ == "__main__":
    allBuilds = []

    defbasedir = os.environ['HOME'] + "/scratch"

    # Command line parsing
    parser = argparse.ArgumentParser(description="PMIx Cross Version Check Script")
    parser.add_argument("--basedir", help="Base directory", action="store", dest="basedir", default=defbasedir)

    parser.parse_args()
    args = parser.parse_args()

    # set the directories
    if args.basedir.startswith("."):
        args.basedir = defbasedir + args.basedir[1:]
    pmix_install_dir = args.basedir + "/install"
    pmix_build_dir = args.basedir

    for vers in supported_versions:
        bld = BuildInfo()
        bld.branch = vers
        bld.sync()
        allBuilds.append(bld)

    # Build everything necessary
    for bld_server in allBuilds:
        print("============ PMIx Build: "+bld_server.branch+" =====================")
        ret = check_tree(bld_server)

        if 1 == ret:
            final_summary.append("Build SKIP: "+bld_server.branch+" -> "+bld_server.build_base_dir)
        else:
            final_summary.append("Build ***Rebuild***: "+bld_server.branch+" -> "+bld_server.build_base_dir)
            count_rebuild += 1

    print("="*30 + " Summary " + "="*30)
    for line in final_summary:
        print line

    sys.exit(count_rebuild)
