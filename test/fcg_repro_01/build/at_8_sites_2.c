typedef void (*callback)(void);
__attribute__((noinline, used)) void target_0(void) { __asm__ volatile("" ::: "memory"); }
__attribute__((noinline, used)) void target_1(void) { __asm__ volatile("" ::: "memory"); }
__attribute__((noinline, used)) void target_2(void) { __asm__ volatile("" ::: "memory"); }
__attribute__((noinline, used)) void target_3(void) { __asm__ volatile("" ::: "memory"); }
__attribute__((noinline, used)) void target_4(void) { __asm__ volatile("" ::: "memory"); }
__attribute__((noinline, used)) void target_5(void) { __asm__ volatile("" ::: "memory"); }
__attribute__((noinline, used)) void target_6(void) { __asm__ volatile("" ::: "memory"); }
__attribute__((noinline, used)) void target_7(void) { __asm__ volatile("" ::: "memory"); }
__attribute__((used)) callback candidates[] = {target_0, target_1, target_2, target_3, target_4, target_5, target_6, target_7};
int main(void) {
    callback volatile selected = candidates[0];
    selected();
    selected();
    return 0;
}
