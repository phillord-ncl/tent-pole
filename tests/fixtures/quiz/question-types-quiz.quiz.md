---
title: "Tent-Pole quiz: main markdown features, practice quiz"
quiz_type: practice_quiz
allowed_attempts: 1
---

Source: `question-types-quiz.quiz.md`.

Practice quiz (`quiz_type: practice_quiz`). Demonstrates question
types, code rendering, question groups: real questions in one group;
a mock question in a separate group; a third, empty group.

Front page settings: allowed attempts 1, explicit. Points possible (8)
computed -- sum of each group's pick_count x question_points (6+1+1).
Everything else (time limit, shuffle answers, etc): Canvas default,
not set here.

## Real Questions {.group pick="6" points="1"}

### Multiple Choice Question with Code {.question points="1"}

Question 1. Hello world program, syntax highlighted. Four answers:
three code (fixed-width font), one plain text.

```{.python}
print("Hello, World!")
```

- [x] `Hello, World!`
- [ ] `Hello World`
- [ ] `print("Hello, World!")`
- [ ] A syntax error occurs

### Multiple Answers Question {.question points="1"}

Question 2. Allows multiple correct answers -- inferred from more than
one checked box (not multiple choice).

- [x] Red
- [x] Blue
- [ ] Chair
- [ ] Tuesday

### Essay Question {.question type="essay" points="1"}

Question 3. No answer options, free text only. Type set explicitly
(`type="essay"`) -- never inferred.

### Multiple Choice Question with Included Code, No Output Shown {.question points="1"}

Question 4. `include=` alone, no `output=`. Code only, no output
block. Compare next question.

```{.python include=demo.py}
```

- [x] No, no output is shown below the code
- [ ] Yes, output is shown below the code

### Multiple Choice Question with Included Code and Output {.question points="1"}

Question 5. `include=`+`output=` on one code block: code from
`demo.py`, real output from `demo.out`, plus a "Taken from:" link.
Correct answer matches shown output -- demonstrates rendering, not
recall.

```{.python include=demo.py output="true"}
```

- [x] `1`, `4`, `9`, `16`, `25`, each on its own line
- [ ] `1 2 3 4 5`
- [ ] `[1, 4, 9, 16, 25]`
- [ ] A syntax error

### Multiple Choice Question with Included Code and Crash Output {.question points="1"}

Question 6. `include=`+`crash=` on one code block: code from
`crash_demo.py`, real traceback from `crash_demo.crash`. Correct
answer matches shown traceback -- demonstrates rendering, not recall.

```{.python include=crash_demo.py crash="true"}
```

- [x] It raises `ZeroDivisionError`
- [ ] It prints `10`
- [ ] It prints `0`
- [ ] Nothing happens

## Separate Group {.group pick="1" points="1"}

### Mock Question in a Separate Group {.question points="1"}

Question 7. Confirms this group is separate from "Real Questions"
above.

- [x] Yes, this is in a separate group
- [ ] No

## Empty Group {.group pick="1" points="1"}
