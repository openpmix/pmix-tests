#define WAIT_WHILE_EQ(_a, _n)                   \
    while ((_n) == (_a)) {                      \
        usleep(100000);                         \
    }
