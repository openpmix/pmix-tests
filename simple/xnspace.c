#include <stdlib.h>
#include <stdio.h>
#include <pmix.h>

int main(int argc, char *argv[]) {

  pmix_proc_t proc, myproc;
  char child_nspace[PMIX_MAX_NSLEN];
  char cwd[1024];
  pmix_value_t *val1, *val2;
  int rc;

  pmix_app_t app;

  rc = PMIx_Init(&myproc, NULL, 0);

  app.cmd = strdup("/bin/sleep");
  app.argv = (char**) malloc(sizeof(char*) * 3);
  app.argv[0] = strdup("/bin/sleep");
  app.argv[1] = strdup("60");
  app.argv[2] = NULL;
  app.env = NULL;
  app.cwd = getcwd(cwd, 1024);
  app.maxprocs = 1;
  app.info = NULL;
  app.ninfo = 0;

  PMIx_Spawn(NULL, 0, &app, 1, child_nspace);

 fprintf(stderr, "Created a child with nspace name '%s'\n", child_nspace);

  strcpy(proc.nspace, child_nspace);
  proc.rank = 0;   // hangs

  rc = PMIx_Get(&myproc, PMIX_HOSTNAME, NULL, 0, &val1);
  fprintf(stderr, "rc of my proc HOSTNAME: %d with value %s\n", rc, (rc ? "" : val1->data.string));

  rc = PMIx_Get(&proc, PMIX_HOSTNAME, NULL, 0, &val2);
  fprintf(stderr, "rc of CHILD proc HOSTNAME: %d with value %s\n", rc, (rc ? "" : val2->data.string));

  PMIx_Finalize(NULL, 0);
}

