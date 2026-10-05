# Hello, World!

This example develops the same program over two lecture stages. Each
stage has its own source directory, so both downloadable files can be
named `HelloWorld.java` and compile as ordinary Java source.

## 1. The first version

Start with the smallest complete Java program. The class name and file
name match, as Java expects.

```{.java include=01-first-version/HelloWorld.java}
```

## 2. Add a personal greeting

Now change the program to greet a named student. This is a separate
version of the same class, not a second class with a suffix in its name.

```{.java include=02-personal-greeting/HelloWorld.java output=true}
```

The rendered page should show the captured program output after the source.

## 3. Read a compiler error

This version deliberately contains a syntax error. Mark the failure as
expected so the page can show the compiler diagnostic as part of the
lesson, rather than presenting it as an unexpected runtime crash.

```{.java include=03-compile-fail/HelloWorld.java compile-fail=true}
```
