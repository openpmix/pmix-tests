#!/usr/bin/python -u

#
# To build only: (-q = quiet mode)
#  ./xversion.py -r -q
# To run only:
#  ./xversion.py -b -q
#

import sys
import os
import re
import argparse
import subprocess
import shutil

# put this in one place
supported_versions = ["master", "v3.1", "v3.0", "v2.2", "v2.1", "v2.0", "v1.2"]

pmix_git_url      = "https://github.com/pmix/pmix.git"
pmix_release_url  = "https://github.com/pmix/pmix/releases/download/"
pmix_install_dir  = ""
pmix_build_dir    = ""

args = None
output_file = os.getcwd() + "/build_output.txt"
result_file = os.getcwd() + "/run_result.txt"

final_summary = []

count_failed=0

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
    global pmix_build_dir
    global pmix_install_dir
    global output_file
    global args

    orig_dir = os.getcwd()

    local_build_dir   = pmix_build_dir + "/" + bld_server.build_base_dir
    local_install_dir = pmix_install_dir + "/" + bld.build_base_dir

    # If the build directory exists see if we need to update+rebuild, rebuild, or skip.
    if os.path.isdir(local_build_dir) and os.path.isdir(local_install_dir):
        os.chdir(local_build_dir)

        # Not a .git repo
        # if the install dir is present then skip, otherwise continue to build
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
                print("\"git pull\" indicated a change on this branch. Rebuilding.")
                print("Log:\n"+sio)
                shutil.rmtree(local_build_dir)

    # If the build directory does not exist then check it out
    if os.path.isdir(local_build_dir) is False:
        if bld.is_git is True:
            print("============ PMIx Build: "+bld.branch+" : Git Clone")
            ret = subprocess.call(["git", "clone",
                                   "-b", bld.branch,
                                   bld.url, local_build_dir],
                                   stdout=logfile, stderr=logfile, shell=False)
            if 0 != ret:
                os.chdir(orig_dir)
                return ret
        elif os.path.isabs(bld.url) and os.path.isdir(bld.url):
            print("============ PMIx Build: "+bld.url+" : Build from source directory")
            shutil.copytree(bld.url, local_build_dir)
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


    os.chdir(local_build_dir)

    if os.path.isdir(local_install_dir):
        shutil.rmtree(local_install_dir)

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
    if "v1" in bld.branch:
        ret = subprocess.call(["./configure",
                               "--disable-debug",
                               "--enable-static",
                               "--disable-shared",
                               "--disable-visibility",
                               "--with-libevent=" + args.libevent,
                               "--with-hwloc=" + args.hwloc1,
                               "--prefix=" + local_install_dir],
                               stdout=logfile, stderr=logfile, shell=False)
    elif "v2" in bld.branch:
        ret = subprocess.call(["./configure",
                               "--disable-debug",
                               "--enable-static",
                               "--disable-shared",
                               "--disable-dlopen",
                               "--disable-per-user-config-files",
                               "--disable-visibility",
                               "--with-libevent=" + args.libevent,
                               "--prefix=" + local_install_dir],
                               stdout=logfile, stderr=logfile, shell=False)
    else:
        ret = subprocess.call(["./configure",
                               "--disable-debug",
                               "--enable-static",
                               "--disable-shared",
                               "--disable-dlopen",
                               "--disable-per-user-config-files",
                               "--with-libevent=" + args.libevent,
                               "--with-hwloc=" + args.hwloc,
                               "--prefix=" + local_install_dir],
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
    os.chdir(local_build_dir + "/test/simple")
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

    client_build_dir   = pmix_build_dir + "/" + bld_client.build_base_dir
    server_build_dir   = pmix_build_dir + "/" + bld_server.build_base_dir

    os.chdir(server_build_dir + "/test/simple")
    cmd = ["./simptest", "-n", "2", "-e", client_build_dir + "/test/simple/simpclient"];

    print("============ PMIx Run  : Run simptest")
    print("Client " + client_build_dir + "/test/simple/simpclient")
    print("Server " + os.getcwd() )
    print("Command: "+ " ".join(cmd))
    with open(result_file, 'w') as logfile:
        ret = subprocess.call(cmd, stdout=logfile, stderr=subprocess.STDOUT, shell=True)
        print("RETURNED " + str(ret))
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
    servers = []
    clients = []

    defbasedir = os.getcwd()

    # Command line parsing
    parser = argparse.ArgumentParser(description="PMIx Cross Version Check Script")
    parser.add_argument("-b", "--no-build", help="Skip building PMIx", action="store_true")
    parser.add_argument("-r", "--no-run", help="Skip running PMIx", action="store_true")
    parser.add_argument("-q", "--quiet", help="Quiet output (output in output.txt)", action="store_true")
    parser.add_argument("--basedir", help="Base directory", action="store", dest="basedir", default=defbasedir)
    parser.add_argument("--with-libevent", help="Where libevent is located", action="store", dest="libevent", default="")
    parser.add_argument("--with-hwloc", help="Where hwloc is located", action="store", dest="hwloc", default="")
    parser.add_argument("--with-hwloc1", help="Where hwloc v1 is located", action="store", dest="hwloc1", default="")
    parser.add_argument("--server-versions", help="Comma-separated PMIx versions to use as servers", action="store", dest="servers", default="all")
    parser.add_argument("--client-versions", help="Comma-separated PMIx versions to use as clients", action="store", dest="clients", default="all")

    parser.add_argument("--with-repo", help="Use this GitHub repo", action="store", dest="gh_repo", default="")
    parser.add_argument("--with-branch", help="Build this GitHub branch", action="store", dest="gh_branch", default="")
    parser.add_argument("--with-src", help="Use this source directory", action="store", dest="raw_src", default="")

    parser.parse_args()
    args = parser.parse_args()

    if args.quiet is True:
        if os.path.exists(output_file):
            os.system("rm " + output_file)

    # 'server' -> 'client' pairs that are not supported
    invalid_pairs.append(["v1.2","master"])
    invalid_pairs.append(["v1.2","v3.1"])
    invalid_pairs.append(["v1.2","v3.0"])
    invalid_pairs.append(["v1.2","v2.2"])
    invalid_pairs.append(["v1.2","v2.1"])
    invalid_pairs.append(["v1.2","v2.0"])
    # --
    invalid_pairs.append(["v2.0","master"])
    invalid_pairs.append(["v2.0","v3.1"])
    invalid_pairs.append(["v2.0","v3.0"])
    invalid_pairs.append(["v2.0","v2.2"])
    invalid_pairs.append(["v2.0","v2.1"])
    invalid_pairs.append(["v2.0","v1.2"])

    # set the directories
    if args.basedir.startswith("."):
        args.basedir = defbasedir + args.basedir[1:]
    pmix_install_dir = args.basedir + "/install"
    pmix_build_dir = args.basedir

    # setup server list
    if "all" in args.servers:
        servers = supported_versions
    else:
        servers = args.servers.split(",")
    if "all" in args.clients:
        clients = supported_versions
    else:
        clients = args.clients.split(",")

    for vers in supported_versions:
        if vers in servers or vers in clients:
            bld = BuildInfo()
            bld.branch = vers
            bld.sync()
            allBuilds.append(bld)

    # Specific repo target
    if len(args.gh_repo) > 0 and len(args.gh_branch) > 0:
        bld = BuildInfo()
        bld.url = args.gh_repo
        bld.branch = args.gh_branch
        bld.is_git = True
        bld.sync()
        allBuilds.append(bld)
        servers.append(bld.branch)
        clients.append(bld.branch)

    # Specific directory target
    if len(args.raw_src) > 0:
        args.raw_src = args.raw_src.rstrip("/")

        bld = BuildInfo()
        bld.url = args.raw_src
        bld.branch = os.path.basename(args.raw_src)
        bld.is_git = False
        bld.sync()
        allBuilds.append(bld)
        servers.append(bld.branch)
        clients.append(bld.branch)


    # Build everything necessary
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
            elif 1 == ret:
                final_summary.append("Build SKIP: "+bld_server.branch+" -> "+bld_server.build_base_dir)
            else:
                final_summary.append("Build ***FAILED***: "+bld_server.branch+" -> "+bld_server.build_base_dir)
                count_failed += 1

    # Run the cross-version test
    if args.no_run is False:
        for bld_server in allBuilds:
            if bld_server.branch not in servers:
                continue
            for bld_client in allBuilds:
                if bld_client.branch not in clients:
                    continue
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
                        final_summary.append("Run ***FAILED***: "+bld_server.branch+" -> "+bld_client.branch)
                        count_failed += 1

    print("="*30 + " Summary " + "="*30)
    for line in final_summary:
        print line

    sys.exit(count_failed)
