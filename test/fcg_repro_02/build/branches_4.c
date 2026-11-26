typedef void (*callback)(void);
__attribute__((noinline, used)) void target_0(void) { __asm__ volatile("" ::: "memory"); }
__attribute__((noinline, used)) void target_1(void) { __asm__ volatile("" ::: "memory"); }
__attribute__((noinline, used)) void target_2(void) { __asm__ volatile("" ::: "memory"); }
__attribute__((noinline, used)) void target_3(void) { __asm__ volatile("" ::: "memory"); }
int main(int argc, char **argv) {
    (void)argv;
    callback selected = target_0;
    if (argc == 2) selected = target_1;
    if (argc == 3) selected = target_2;
    if (argc == 4) selected = target_3;
    selected();
    return 0;
}
