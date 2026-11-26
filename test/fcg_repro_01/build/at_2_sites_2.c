typedef void (*callback)(void);
__attribute__((noinline, used)) void target_0(void) { __asm__ volatile("" ::: "memory"); }
__attribute__((noinline, used)) void target_1(void) { __asm__ volatile("" ::: "memory"); }
__attribute__((used)) callback candidates[] = {target_0, target_1};
int main(void) {
    callback volatile selected = candidates[0];
    selected();
    selected();
    return 0;
}
