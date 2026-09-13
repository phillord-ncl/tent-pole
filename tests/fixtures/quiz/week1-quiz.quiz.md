---
title: "Week 1 Quiz"
quiz_type: graded_survey
points_possible: 3
allowed_attempts: 1
---

## List comprehension output {.question points="1"}

Suppose you're reviewing a colleague's code and want to work out what
it does before running it yourself. Below is a short function that
builds a list using a list comprehension over a range, followed by a
loop that prints each value the function returns. Read the code
carefully, work through what each line does, and then decide which of
the following options correctly describes what actually gets printed
when the code runs.

```{.python include=demo.py}
```

```{include=demo.out}
```

- [ ] `1 2 3 4 5`
- [x] `1`, `4`, `9`, `16`, `25`, each on its own line
- [ ] `[1, 4, 9, 16, 25]`
- [ ] A syntax error

## Division by zero {.question points="1"}

What happens when the following code runs?

```{.python include=crash_demo.py}
```

```{include=crash_demo.crash}
```

- [ ] It prints `0`
- [x] It raises `ZeroDivisionError`
- [ ] It prints `10`
- [ ] Nothing happens

## Explaining ZeroDivisionError {.question type="essay" points="1"}

Explain, in your own words, why `divide(10, 0)` fails but
`divide(10, 2)` doesn't.
