  //  This program reads test case output and replaces strings containing
  // namespace, pid, and hostname with uniform names representing those
  // strings, in order to allow testcase validation to handle test case
  // output that varies from run to run.
  //  As each string is matched, it is added to an array for that class of
  // string. The replacement string consists of a tag and the array index
  // of the string, for instance @NS<1>.
  //  This program uses regular expressions to perform matching, using
  // additional text around the candidate string for context to ensure 
  // only the expected string is matched.
  //  In some cases, the order that regcomp calls are made is important so that
  //  a shorter expression that will match a substring of a longer expression
  //  must run after the attempt to match the linger expression.
#include <regex.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/types.h>

#define ARRAY_MAX 100

  // Regex to match strings like 'pid 141379:' or 'pid 141379'
static char *pid_pattern = "pid ([0-9]+):?";
static regex_t pid_regex;
  // Regex to match strings like 'prte-f8n07139407.12'
  // or 'prte-f8n07139407@12'
static char *namespace_pattern =
            "([a-zA-Z]+[a-zA-Z0-9_.\\-]+[@.][0-9]+)";
static regex_t namespace_regex;
static char *namespace_pattern2 =
            "namespace=([a-zA-Z]+[a-zA-Z0-9_@.\\-]+)";
static regex_t namespace_regex2;
  // Regex to match strings like 'prte-f8n07139407.12:141379'
  // or 'prte-f8n07139407@12:141379'.
  // To avoid ambiguity with ranks and pids, assume a pid is always > 100
  // and a rank is always < 100. This may need to be revisited if tests are
  // run in a container environment and the first application pid is < 100
static char *nspace_pid_pattern = 
            "([a-zA-Z]+[a-zA-Z0-9_.\\-]+[@.][0-9]+):([0-9]{2,8})";
static regex_t nspace_pid_regex;
  // Regex to match strings like 'prte-f8n07139407.12:0:141379'
  // or 'prte-f8n07139407@12:0:141379'
static char *nspace_rank_pid_pattern = 
            "([a-zA-Z]+[a-zA-Z0-9_@.\\-]+[@.][0-9]+):-?[0-9]+:([0-9]+)";
static regex_t nspace_rank_pid_regex;
  // Regex to match hostnames
static char *host_pattern = "on host ([0-9a-zA-Z][a-zA-Z0-9.\\-]+)";
static regex_t host_regex;
  // Regex to match strings like f8n07:53120:1@2
static char * host_pid_ns_pattern =
            "([a-zA-Z0-9_.\\-]+):([0-9]+):([0-9]+@[0-9]+)";
static regex_t host_pid_ns_regex;
  // Regex to match strings like f8n07:53120:1@2:0:58103
static char * host_pid_ns_rank_pid_pattern =
            "([a-zA-Z0-9_.\\-]+):([0-9]+):([0-9]+)@[0-9]+:-?[0-9]:([0-9]+)";
static regex_t host_pid_ns_rank_pid_regex;
  // Regex to match strings like "ns f8n07:64028"
  // 'ns ' is included in match so this regex does not incorrectly match to
  // longer host/namespace variations
static char * unconnected_tool_ns_pattern = "ns ([a-zA-Z0-9_.\\-]+:[0-9]+)";
static regex_t unconnected_tool_ns_regex;
  // Regex to match the URI in testcase output, for example
  // DEBUGGER URI: f8n07:62706.0;tcp
static char *uri_pattern = "([0-9a-zA-Z][a-zA-Z0-9.\\-]+:[0-9]+\\.[0-9]+);tcp";
static regex_t uri_regex;
  // Regex to match namespaces, for instance  [f8n07:62706:1:0]
static char *release_ns_pattern =
            "\\[([0-9a-zA-Z][a-zA-Z0-9.\\-]+:[0-9]+:[0-9]+:[0-9]+)\\]";
static regex_t release_ns_regex;
  // Regex to match TCP4 connections, for example tcp4://127.0.0.1:53453
static char *tcp4_connect_pattern =
            "tcp4://([0-9]+\\.[0-9]+\\.[0-9]+\\.[0-9]+:[0-9]+)";
static regex_t tcp4_connect_regex;
  // Regex to match namespace specs like f8n07:117240:1
static char *indirect_ns_pattern =
            "([0-9a-zA-Z][a-zA-Z0-9.\\-]+:[0-9]+:[0-9]+)";
static regex_t indirect_ns_regex;

static char regex_error[256];
static char input[1024];
static char output[1024];
static char *pid_array[ARRAY_MAX];
static char *namespace_array[ARRAY_MAX];
static char *host_array[ARRAY_MAX];
static int num_pids;
static int num_namespaces;
static int num_hosts;

  //  Maintain an array of unique strings. Replace the string in the original
  //  text with a string in the format @xx<n> where xx identifies the type
  //  of string, pid, host or namespace, and n is the array index for the
  //  string. This ensures that pid, host or namespace is unique from run to run
  //  as long as strings appear in the same order in the input text.
void replace_text(regmatch_t *match, char *prefix, char **unique_strings,
                  int *current_size) {
    char match_text[512];
    char replace_text[512];
    int i;
    int text_length = match->rm_eo - match->rm_so;

    if (ARRAY_MAX == *current_size) {
        fprintf(stderr,
                "Maximum number of elements for %s array exceeded\n", prefix);
        exit(1);
    }
      // Get the matching string
    strncpy(match_text, &input[match->rm_so], text_length);
    match_text[text_length] = '\0';
      // Copy input up to the matching text
    if (0 != match->rm_so) {
        strncpy(output, input, match->rm_so);
        output[match->rm_so] = '\0';
    }
    else {
        output[0] = '\0';
    }
      // Look up the matching text and add new entry if no match
    for (i = 0; i < *current_size; i++) {
        if (0 == strcmp(match_text, unique_strings[i])) {
            break;
        }
    }
    if (i >= *current_size) {
        if (i >= ARRAY_MAX) {
            fprintf(stderr, "String array is full\n");
            exit(1);
        }
        unique_strings[*current_size] = strdup(match_text);
        *current_size = *current_size + 1;
    }
      // Copy the replacement string to output string
    sprintf(replace_text, "@%s<%d>", prefix, i);
    strcat(output, replace_text);
      // Copy remaining input text after pid
    strcat(output, &input[match->rm_eo]);
      // Copy output back to input for rescan
    strcpy(input, output);
}

void regex_parse_error(int rc, regex_t *expr, char *label) {
        regerror(rc, &pid_regex, regex_error, sizeof regex_error - 1);
        fprintf(stderr, "Error compiling %s: %s\n", label, regex_error);
        exit(1);
}

int main(int argc, char *argv[]) {
    regmatch_t matches[6];
      // Compile regular expressions needed to process testcase output
    int rc = regcomp(&pid_regex, pid_pattern, REG_EXTENDED);
    if (0 != rc) {
        regex_parse_error(rc, &pid_regex, "pid_regex");
    }
    rc = regcomp(&namespace_regex, namespace_pattern, REG_EXTENDED);
    if (0 != rc) {
        regex_parse_error(rc, &namespace_regex, "namespace_regex");
    }
    rc = regcomp(&namespace_regex2, namespace_pattern2, REG_EXTENDED);
    if (0 != rc) {
        regex_parse_error(rc, &namespace_regex2, "namespace_regex2");
    }
    rc = regcomp(&nspace_rank_pid_regex, nspace_rank_pid_pattern,
                 REG_EXTENDED);
    if (0 != rc) {
        regex_parse_error(rc, &nspace_rank_pid_regex, "nspace_rank_pid_regex");
    }
    rc = regcomp(&nspace_pid_regex, nspace_pid_pattern, REG_EXTENDED);
    if (0 != rc) {
        regex_parse_error(rc, &nspace_pid_regex, "nspace_pid_regex");
    }
    rc = regcomp(&host_regex, host_pattern, REG_EXTENDED);
    if (0 != rc) {
        regex_parse_error(rc, &host_regex, "host_regex");
    }
    rc = regcomp(&host_pid_ns_regex, host_pid_ns_pattern, REG_EXTENDED);
    if (0 != rc) {
        regex_parse_error(rc, &host_pid_ns_regex, "host_pid_ns_regex");
    }
    rc = regcomp(&host_pid_ns_rank_pid_regex, host_pid_ns_rank_pid_pattern,
                 REG_EXTENDED);
    if (0 != rc) {
        regex_parse_error(rc, &host_pid_ns_rank_pid_regex,
                          "host_pid_ns_rank_pid_regex");
    }
    rc = regcomp(&unconnected_tool_ns_regex, unconnected_tool_ns_pattern,
                 REG_EXTENDED);
    if (0 != rc) {
        regex_parse_error(rc, &unconnected_tool_ns_regex,
                          "unconnected_tool_ns_regex");
    }
    rc = regcomp(&uri_regex, uri_pattern, REG_EXTENDED);
    if (0 != rc) {
        regex_parse_error(rc, &uri_regex, "uri_regex");
    }
    rc = regcomp(&release_ns_regex, release_ns_pattern, REG_EXTENDED);
    if (0 != rc) {
        regex_parse_error(rc, &release_ns_regex, "release_ns_regex");
    }
    rc = regcomp(&tcp4_connect_regex, tcp4_connect_pattern, REG_EXTENDED);
    if (0 != rc) {
        regex_parse_error(rc, &tcp4_connect_regex, "tcp_connect4_regex");
    }
    rc = regcomp(&indirect_ns_regex, indirect_ns_pattern, REG_EXTENDED);
    if (0 != rc) {
        regex_parse_error(rc, &indirect_ns_regex, "indirect_ns_regex");
    }
      // Read testcase output from stdin and write converted text to stdout
    char *p = fgets(input, sizeof input - 1, stdin);
    while (NULL != p) {
        // Remove sequence numbers from stdout/stderr file since they cause all
        // following lines to fail comparison to baseline when a line is added or
        // deleted in output for current execution. That masks the real
        // difference in output.
        memmove(&input[10], &input[14], strlen(&input[14]));
        int rescan;
          // Get rid of newline since puts() will add a newline to output string
        p = strchr(input, '\n');
        if (NULL != p) {
            *p = '\0';
        }
          // Search for and replace pid and namespace strings in the current
          // line one at a time. If text is replaced, then rescan the modified
          // input in case there are more matches.
        rescan = 1;
        while (1 == rescan) {
            rc = regexec(&pid_regex, input, 2, matches, 0);
            if (0 == rc) {
                replace_text(&matches[1], "PID", pid_array, &num_pids);
                continue;
            }
              // Look for namespace and pid pairs first since a stand-alone
              // namespace, if matched, will be processed before we can deal 
              // with the pid.
              // We need to look for strings with and without rank specified
            rc = regexec(&nspace_rank_pid_regex, input, 3, matches, 0);
            if (0 == rc) {
                  // Pid follows namespace. By processing pid first, we don't
                  // have to recompute offsets for the namespace string.
                replace_text(&matches[2], "PID", pid_array, &num_pids);
                replace_text(&matches[1], "NS", namespace_array,
                             &num_namespaces);
                continue;
            }
            rc = regexec(&nspace_pid_regex, input, 3, matches, 0);
            if (0 == rc) {
                  // Pid follows namespace. By processing pid first, we don't
                  // have to recompute offsets for the namespace string.
                replace_text(&matches[2], "PID", pid_array, &num_pids);
                replace_text(&matches[1], "NS", namespace_array,
                             &num_namespaces);
                continue;
            }
              // There are two expressions to match namespace, to handle
              // the attach cases and anything else. In the attach case,
              // the task rank is not part of the namespace string, making it
              // a simple alpha numeric string which is impossible to parse
              // with no ambiguity without additional context.
              // So the attach testcase reports the namespace as 
              // 'namespace=xxx' and the regex tries to match to that.
            rc = regexec(&namespace_regex, input, 2, matches, 0);
            if (0 == rc) {
                replace_text(&matches[1], "NS", namespace_array,
                             &num_namespaces);
                continue;
            }
            rc = regexec(&namespace_regex2, input, 2, matches, 0);
            if (0 == rc) {
                replace_text(&matches[1], "NS", namespace_array,
                             &num_namespaces);
                continue;
            }
            rc = regexec(&host_regex, input, 2, matches, 0);
            if (0 == rc) {
                replace_text(&matches[1], "HOST", host_array, &num_hosts);
                continue;
            }
              // Try match for host,pid,ns,rank,pid strings before trying to match
              // for host, pid, ns so that the host, pid, ns scan does not partially
              // replace the host, pid, ns, rank, pid string
            rc = regexec(&host_pid_ns_rank_pid_regex, input, 5, matches, 0);
            if (0 == rc) {
                  // Text to replace is host, pid and namespace tag. Perform
                  // replacements in reverse order so match offsets in original
                  // text don't need to be recomputed for 2nd, 3rd & 4th replace.
                replace_text(&matches[4], "PID", pid_array, &num_pids);
                replace_text(&matches[3], "NS", namespace_array, &num_namespaces);
                replace_text(&matches[2], "PID", pid_array, &num_pids);
                replace_text(&matches[1], "HOST", host_array, &num_hosts);
                continue;
            }
            rc = regexec(&host_pid_ns_regex, input, 4, matches, 0);
            if (0 == rc) {
                  // Text to replace is host, pid and namespace tag. Perform
                  // replacements in reverse order so match offsets in original
                  // text don't need to be recomputed for 2nd and 3rd replace.
                replace_text(&matches[3], "NS", namespace_array,
                             &num_namespaces);
                replace_text(&matches[2], "PID", pid_array, &num_pids);
                replace_text(&matches[1], "HOST", host_array, &num_hosts);
                continue;
            }
            rc = regexec(&unconnected_tool_ns_regex, input, 2, matches, 0);
            if (0 == rc) {
                  // Text to replace is tool namespace
                replace_text(&matches[1], "NS", namespace_array,
                             &num_namespaces);
                continue;
            }
            rc = regexec(&uri_regex, input, 2, matches, 0);
            if (0 == rc) {
                  // Text to replace is debugger URI. Store it in namespace
                  // table instead of creating a special table for one URI.
                replace_text(&matches[1], "NS", namespace_array,
                             &num_namespaces);
                continue;
            }
            rc = regexec(&release_ns_regex, input, 2, matches, 0);
            if (0 == rc) {
                  // Text to replace is debugger URI. Store it in namespace
                  // table instead of creating a special table for one URI.
                replace_text(&matches[1], "NS", namespace_array,
                             &num_namespaces);
                continue;
            }
            rc = regexec(&tcp4_connect_regex, input, 2, matches, 0);
            if (0 == rc) {
                  // Text to replace is TCP connection. Store it in host
                  // table instead of creating a special table for one 
                  // connection
                replace_text(&matches[1], "HOST", host_array, &num_hosts);
                continue;
            }
            rc = regexec(&indirect_ns_regex, input, 2, matches, 0);
            if (0 == rc) {
                  // Text to replace is debugger URI. Store it in namespace
                  // table instead of creating a special table for one URI.
                replace_text(&matches[1], "NS", namespace_array,
                             &num_namespaces);
                continue;
            }
              // No more matches in current line so end the scan loop.
            rescan = 0;
        }
        puts(input);
        p = fgets(input, sizeof input - 1, stdin);
    }
}
