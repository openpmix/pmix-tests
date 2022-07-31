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
supported_versions = ["master", "v4.2", "v4.1", "v3.1", "v3.2"]

pmix_git_url      = "https://github.com/pmix/pmix.git"
pmix_release_url  = "https://github.com/pmix/pmix/releases/download/"
pmix_install_dir  = ""
pmix_build_dir    = ""

timeout_cmd = None

args = None
output_file = os.getcwd() + "/build_output.txt"
result_file = os.getcwd() + "/run_result.txt"

final_summary_build = []
final_summary_client = []
final_summary_tool = []
final_summary_check = []

count_failed=0
count_failed_tool=0
count_failed_check=0

# provide the array of tests used in "make check" - for each
# target branch, we need to append the full path to their "pmix_client"
# executable
make_check_tests = ["-n 4 --ns-dist 3:1 --fence \"[db | 0:0-2;1:0]\" -e ",
                    "-n 4 --ns-dist 3:1 --fence \"[db | 0:;1:0]\" -e ",
                    "-n 4 --ns-dist 3:1 --fence \"[db | 0:;1:]\" -e ",
                    "-n 4 --ns-dist 3:1 --fence \"[0:]\" -e ",
                    "-n 4 --ns-dist 3:1 --fence \"[b | 0:]\" -e ",
                    "-n 4 --ns-dist 3:1 --fence \"[d | 0:]\" --noise \"[0:0,1]\" -e ",
                    "-n 4 --job-fence -c -e ",
                    "-n 4 --job-fence -e ",
                    "-n 2 --test-publish -e ",
                    "-n 2 --test-spawn -e ",
                    "-n 2 --test-connect -e ",
                    "-n 5 --test-resolve-peers --ns-dist \"1:2:2\" -e ",
                    "-n 5 --test-replace 100:0,1,10,50,99 -e ",
                    "-n 5 --test-internal 10 -e "]

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
        # If there is an upstream update for this branch then rebuild, otherwise skip.
        # If we encounter a network issue then skip the refresh and run with what we have.
        else:
            ret = subprocess.call(["git", "fetch", "-q", "origin", bld.branch],
                                   stdout=logfile, stderr=logfile, shell=False)
            if 0 != ret:
                print("Error: \"git fetch -q origin "+bld.branch+"\" failed. Possible network issue. (rtn "+str(ret)+")");
                os.chdir(orig_dir)
                return 2

            p = subprocess.Popen("git pull origin "+bld.branch,
                                 stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True, close_fds=True)
            p.wait()
            if p.returncode != 0:
                print("Skip: Error: \"git pull origin "+bld.branch+"\" failed. Possible network issue. (rtn "+str(p.returncode)+")");
                os.chdir(orig_dir)
                return 2

            os.chdir(orig_dir)

            sio = p.stdout.read()
            if "Already up-to-date" in sio or "Already up to date" in sio:
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
                print("Error: \"git clone "+bld.branch+" "+bld.url+"\" failed. Possible network issue.");
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
        return ret if ret < 0 or ret > 2 else (ret + 1000)

    print("============ PMIx Build: "+bld.branch+" : Configure")
    if bld.branch.startswith("v1"):
        ret = subprocess.call(["./configure",
                               "--disable-debug",
                               "--enable-static",
                               "--disable-shared",
                               "--disable-visibility",
                               "--with-libevent=" + args.libevent,
                               "--with-hwloc=" + args.hwloc1,
                               "--prefix=" + local_install_dir],
                               stdout=logfile, stderr=logfile, shell=False)
    elif bld.branch.startswith("v2"):
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
        return ret if ret < 0 or ret > 2 else (ret + 1000)

    print("============ PMIx Build: "+bld.branch+" : Make")
    ret = subprocess.call(["make", "-j", "4"], stdout=logfile, stderr=logfile, shell=False)
    if 0 != ret:
        os.chdir(orig_dir)
        return ret if ret < 0 or ret > 2 else (ret + 1000)

    print("============ PMIx Build: "+bld.branch+" : Make Install")
    ret = subprocess.call(["make", "-j", "4", "install"], stdout=logfile, stderr=logfile, shell=False)
    if 0 != ret:
        os.chdir(orig_dir)
        return ret if ret < 0 or ret > 2 else (ret + 1000)

    print("============ PMIx Build: "+bld.branch+" : Make Test")
    os.chdir(local_build_dir + "/test/simple")
    ret = subprocess.call(["make"], stdout=logfile, stderr=logfile, shell=False)
    if 0 != ret:
        os.chdir(orig_dir)
        return ret if ret < 0 or ret > 2 else (ret + 1000)

    print("============ PMIx Build: "+bld.branch+" : Done " + orig_dir)
    os.chdir(orig_dir)
    return ret

def run_test(bld_server, bld_client, test_client=False, test_tool=False, test_check=None):
    global pmix_build_dir
    global result_file
    test_name = ""
    test_bin = ""
    cmd = ""

    if test_client is False and test_tool is False and test_check is None:
        print("Error: No test specified.")
        return 42
    if (test_client and test_tool) or (test_client and test_check is not None) or (test_tool and test_check is not None):
        print("Error: Only one test can be specified per call.")
        return 42

    orig_dir = os.getcwd()

    client_build_dir   = pmix_build_dir + "/" + bld_client.build_base_dir
    server_build_dir   = pmix_build_dir + "/" + bld_server.build_base_dir

    if timeout_cmd is not None:
        timeout_str = timeout_cmd + " --preserve-status -k 35 30 "
    else:
        timeout_str = ""

    if test_client:
        test_name = "Client"
        test_bin = client_build_dir + "/test/simple/simpclient"
        cmd = timeout_str + "./simptest -n 2 -xversion -e " + test_bin
    elif test_check is not None:
        test_name = "Make Check"
        test_bin = client_build_dir + "/test/pmix_client"
        cmd = timeout_str + "./pmix_test " + test_check  + test_bin
    else:
        test_name = "Tool"
        test_bin = client_build_dir + "/test/simple/simptool"
        cmd = timeout_str + "./simptest -n 1 --xversion -e " + test_bin

    # Check if the test binary exists
    if os.path.isfile(test_bin) is False:
        print("Error: Test binary (%s) does not exist." % (test_bin))
        return 1

    if test_check is not None:
        os.chdir(server_build_dir + "/test")
        print("-----> : Run simptest "+test_name)
        print("%7s: %s" % (test_name, test_bin) )
        print("Server : " + os.getcwd() )
        print("Command: cd " + os.getcwd() + " ; " + cmd)
    else:
        os.chdir(server_build_dir + "/test/simple")
        print("-----> : Run "+test_name)
        print("%10s: %s" % (test_name, test_bin) )
        print("Server : " + os.getcwd() )
        print("Command: cd " + os.getcwd() + " ; " + cmd)

    if os.path.isfile(result_file):
        os.remove(result_file)
    with open(result_file, 'w') as logfile:
        ret = subprocess.call(cmd, stdout=logfile, stderr=subprocess.STDOUT, shell=True)
        if 0 != ret:
            print("Status : " + str(ret) + " ***FAILED***")
        else:
            print("Status : " + str(ret))

    if args.quiet is False or 0 != ret:
        print("-----> : Test output")
        num_lines = 0
        num_lines_skipped = 0
        with open(result_file, 'r') as logfile:
            for line in logfile:
                num_lines += 1
                if args.max_output_lines > 0 and num_lines > args.max_output_lines:
                    num_lines_skipped += 1
                else:
                    print(line),
        if num_lines_skipped > 0:
            print("!! Warning !! Skipped the last %d of %d lines of output." % (num_lines_skipped, num_lines))

        print("")
    else:
        print("-----> : Test output (Not shown)")

    os.chdir(orig_dir)

    return ret

if __name__ == "__main__":
    allBuilds = []
    invalid_pairs = []
    invalid_tool_pairs = []
    invalid_make_check_tests = []
    servers = []
    clients = []

    defbasedir = os.getcwd()

    # Command line parsing
    parser = argparse.ArgumentParser(description="PMIx Cross Version Check Script")
    parser.add_argument("-b", "--no-build", help="Skip building PMIx", action="store_true")
    parser.add_argument("-r", "--no-run", help="Skip running PMIx", action="store_true")
    parser.add_argument("-q", "--quiet", help="Quiet output (output in output.txt)", action="store_true")
    parser.add_argument("--basedir", help="Base directory", action="store", dest="basedir", default=defbasedir)
    parser.add_argument("--skip-client", help="Skip Client tests", action="store_true")
    parser.add_argument("--skip-tool", help="Skip Tool tests", action="store_true")
    parser.add_argument("--make-check", help="Run make check tests [DISABLED]", action="store_true")
    parser.add_argument("--with-libevent", help="Where libevent is located", action="store", dest="libevent", default="")
    parser.add_argument("--with-hwloc", help="Where hwloc is located", action="store", dest="hwloc", default="")
    parser.add_argument("--with-hwloc1", help="Where hwloc v1 is located", action="store", dest="hwloc1", default="")
    parser.add_argument("--server-versions", help="Comma-separated PMIx versions to use as servers", action="store", dest="servers", default="all")
    parser.add_argument("--client-versions", help="Comma-separated PMIx versions to use as clients", action="store", dest="clients", default="all")

    parser.add_argument("--with-repo", help="Use this GitHub repo", action="store", dest="gh_repo", default="")
    parser.add_argument("--with-branch", help="Build this GitHub branch", action="store", dest="gh_branch", default="")
    parser.add_argument("--with-src", help="Use this source directory", action="store", dest="raw_src", default="")
    parser.add_argument("--max-output-lines", help="Maximum number of lines of error output to display (0=all)", type=int, action="store", dest="max_output_lines", default="100")

    parser.parse_args()
    args = parser.parse_args()

    if args.quiet is True:
        if os.path.exists(output_file):
            os.system("rm " + output_file)

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

    # 'server' -> 'client' pairs that are not supported
    invalid_pairs.append(["v2.0","master"])
    invalid_pairs.append(["v2.0","v3.1"])
    invalid_pairs.append(["v2.0","v3.0"])
    invalid_pairs.append(["v2.0","v2.2"])
    invalid_pairs.append(["v2.0","v2.1"])

    # 'server' -> 'client' tool pairings that are not supported
    invalid_tool_pairs.append(["v2.1","master"])
    invalid_tool_pairs.append(["v2.1","v3.1"])
    invalid_tool_pairs.append(["v2.1","v3.0"])
    invalid_tool_pairs.append(["v2.1","v2.2"])
    invalid_tool_pairs.append(["v2.1","v2.0"])
    # --
    invalid_tool_pairs.append(["v2.0","master"])
    invalid_tool_pairs.append(["v2.0","v3.1"])
    invalid_tool_pairs.append(["v2.0","v3.0"])
    invalid_tool_pairs.append(["v2.0","v2.2"])
    invalid_tool_pairs.append(["v2.0","v2.1"])

    # 'server' -> 'client' "make check" pairs that are not supported
    # NOTE: we will first check the overall pairing per the above
    # invalid_pairs settings, and then we will check for a specific
    # test that is not supported by the target branch
    invalid_make_check_tests.append(["v2.0", "test-resolve-peers"])

    # PR_TARGET_BRANCH is an envar set by Jenkins CI to indicate the target branch
    # This is no way from the github branch itself to tell where it was targeted.
    # As such we need some external envar to tell us.
    target_branch = None
    try:
        target_branch = os.environ['PR_TARGET_BRANCH']
        if target_branch == "v2.0":
            invalid_pairs.append([bld.branch,"master"])
            invalid_pairs.append([bld.branch,"v3.1"])
            invalid_pairs.append([bld.branch,"v3.0"])
            invalid_pairs.append([bld.branch,"v2.2"])
            invalid_pairs.append([bld.branch,"v2.1"])
            # --
            invalid_tool_pairs.append([bld.branch,"master"])
            invalid_tool_pairs.append([bld.branch,"v3.1"])
            invalid_tool_pairs.append([bld.branch,"v3.0"])
            invalid_tool_pairs.append([bld.branch,"v2.2"])
            invalid_tool_pairs.append([bld.branch,"v2.1"])
        elif target_branch == "v2.1":
            invalid_tool_pairs.append([bld.branch,"master"])
            invalid_tool_pairs.append([bld.branch,"v3.1"])
            invalid_tool_pairs.append([bld.branch,"v3.0"])
            invalid_tool_pairs.append([bld.branch,"v2.2"])
            invalid_tool_pairs.append([bld.branch,"v2.0"])
        elif target_branch == "master":
            invalid_pairs.append([bld.branch,"master"])
            invalid_tool_pairs.append([bld.branch,"master"])
            invalid_pairs.append(["master", bld.branch])
            invalid_tool_pairs.append(["master", bld.branch])
        elif target_branch == "v4.2":
            invalid_pairs.append([bld.branch,"v4.2"])
            invalid_tool_pairs.append([bld.branch,"v4.2"])
            invalid_pairs.append(["v4.2", bld.branch])
            invalid_tool_pairs.append(["v4.2", bld.branch])
        elif target_branch == "v4.1:
            invalid_pairs.append([bld.branch,"v4.1"])
            invalid_tool_pairs.append([bld.branch,"v4.1"])
            invalid_pairs.append(["v4.1", bld.branch])
            invalid_tool_pairs.append(["v4.1", bld.branch])
        else:
            invalid_pairs.append(["v2.0",bld.branch])
            invalid_tool_pairs.append(["v2.0",bld.branch])
            invalid_tool_pairs.append(["v2.1",bld.branch])
    except KeyError as e:
        # Ignore if envar is not set
        pass

    # find the timeout command - if on Mac, this may well
    # be "gtimeout", so check for it
    for path in os.environ["PATH"].split(os.pathsep):
        fpath = os.path.join(path, "gtimeout")
        if os.path.isfile(fpath) and os.access(fpath, os.X_OK):
            timeout_cmd = "gtimeout"
            break
        fpath = os.path.join(path, "timeout")
        if os.path.isfile(fpath) and os.access(fpath, os.X_OK):
            timeout_cmd = "timeout"
            break

    # Build everything necessary
    if args.no_build is False:
        for bld_server in allBuilds:
            print("============ PMIx Build: "+bld_server.branch+" =====================")
            if args.quiet is True:
                with open(output_file, 'w') as logfile:
                    #logfile.write("============ PMIx Build: "+bld_server.branch+" =====================\n")
                    #logfile.flush()
                    ret = build_tree(bld_server, logfile)
                if 0 != ret and 1 != ret:
                    # Write the file to stdout so that CI can report it back to the user
                    with open(output_file, 'r') as logfile:
                        print logfile.read()
            else:
                ret = build_tree(bld_server)

            if 0 == ret:
                final_summary_build.append("Build PASS: "+bld_server.branch+" -> "+bld_server.build_base_dir)
            elif 1 == ret:
                final_summary_build.append("Build SKIP: "+bld_server.branch+" -> "+bld_server.build_base_dir)
            elif 2 == ret:
                final_summary_build.append("Build NWRK: "+bld_server.branch+" -> "+bld_server.build_base_dir)
            else:
                final_summary_build.append("Build ***FAILED***: "+bld_server.branch+" -> "+bld_server.build_base_dir)
                count_failed += 1

    # Run the cross-version test - Client
    if args.no_run is False and args.skip_client is False:
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
                    print("Server : %6s -> Client: %6s" % (bld_server.branch, bld_client.branch))
                    ret = run_test(bld_server, bld_client, test_client=True)
                    if 0 == ret:
                        final_summary_client.append("Run PASS: "+bld_server.branch+" -> "+bld_client.branch)
                    else:
                        final_summary_client.append("Run ***FAILED***: "+bld_server.branch+" -> "+bld_client.branch)
                        count_failed += 1

    # Run the cross-version test - Tool
    if args.no_run is False and args.skip_tool is False:
        for bld_server in allBuilds:
            if bld_server.branch not in servers:
                continue
            for bld_client in allBuilds:
                if bld_client.branch not in clients:
                    continue
                is_valid = True
                for pair in invalid_tool_pairs:
                    if bld_server.branch is pair[0] and bld_client.branch is pair[1]:
                        is_valid = False

                if is_valid:
                    print("="*70)
                    print("Server : %6s -> Tool: %6s" % (bld_server.branch, bld_client.branch))
                    ret = run_test(bld_server, bld_client, test_tool=True)
                    if 0 == ret:
                        final_summary_tool.append("Run PASS: "+bld_server.branch+" -> "+bld_client.branch+" (Tool)")
                    else:
                        final_summary_tool.append("Run ***FAILED***: "+bld_server.branch+" -> "+bld_client.branch+" (Tool)")
                        count_failed_tool += 1

    # Run the cross-version test - make check
    if args.no_run is False and args.make_check is True:
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
                    print("Server : %6s -> Client: %6s" % (bld_server.branch, bld_client.branch))
                    for test in make_check_tests:
                        valid_test = True
                        for tstpair in invalid_make_check_tests:
                            if bld_client.branch is tstpair[0] and tstpair[1] in test:
                                valid_test = False
                        if valid_test:
                            ret = run_test(bld_server, bld_client, test_check=test)
                            if 0 != ret:
                                final_summary_check.append("Run ***FAILED***: "+bld_server.branch+" -> "+bld_client.branch + "  [" + test + "]")
                                count_failed_check += 1

    final_len = len(final_summary_build) + len(final_summary_client) + len(final_summary_tool) + len(final_summary_check)
    if 0 < final_len:
        print("")
        print("="*70)
        if args.no_build is False:
            print("="*30 + " Summary (Build) " + "="*30)
            for line in final_summary_build:
                print line

        if args.no_run is False and args.skip_client is False:
            print("="*30 + " Summary (Client) " + "="*30)
            for line in final_summary_client:
                print line

        if args.no_run is False and args.skip_tool is False:
            print("="*30 + " Summary (Tool) " + "="*30)
            for line in final_summary_tool:
                print line

        if args.no_run is False and args.make_check is True:
            print("="*30 + " Summary (Make Check Failures) " + "="*30)
            for line in final_summary_check:
                print line

        print("")
        print("="*70)
    else:
        print("Tests completed OK")

    sys.exit(count_failed + count_failed_tool + count_failed_check)
