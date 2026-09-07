### Build and run tests 

```
make
```

The test suite checks how `syspart` reports symbol and library relationships in a few small examples:

- `hello/` verifies that a direct call to `printHello` is linked to `libhello.so`, and that `libhello.so` is linked to `libstdc++.so.6`.
- `helloIndirect/` checks the same library chain, but expects the `printHello` link to stay indirect.
- `helloDynamic/` runs the dynamic analysis helper and confirms that `dlsym_static.txt` contains `printHello` and `dlopen_static.txt` contains `libhello.so`.

