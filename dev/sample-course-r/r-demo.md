# R code include

Pulls code, output, and a plot in from `demo.R` instead of pasting any
of them in by hand -- same idea as the Python `include=` examples in
`markdown-features-1.md`.

## Chunk selection, no output

```{.r include=demo.R chunk=summary-stats}
```

**Check:** only the `summary-stats` chunk's own two lines (the
`cat(...)` calls) are shown, syntax-highlighted as R -- not `setup`,
not the rest of the file.

## Output capture

```{.r include=demo.R chunk=summary-stats output=true}
```

**Check:** the highlighted `summary-stats` source, a "Taken from:
demo.R" link, an "Outputs:" label, and a code block showing:

```
Mean: 18
SD: 13.49
```

## Output transcript

```{.r include=demo.R chunk=summary-stats stout=true}
```

**Check:** the highlighted `summary-stats` source, a "Taken from:
demo.R" link, a "Prints:" label, and a code block showing the full
REPL-style transcript, each statement echoed with a `> ` prompt ahead
of its own output:

```
> cat("Mean:", mean(data), "\n")
Mean: 18
> cat("SD:", round(sd(data), 2), "\n")
SD: 13.49
```

## Plot output

```{.r include=demo.R chunk=make-plot plot=true}
```

**Check:** highlighted `make-plot` source, "Taken from: demo.R", a
"Plot:" label, and an inline image -- a line-and-point plot of
`4, 8, 15, 16, 23, 42` titled "Sample data".

## Second plot, same source file

```{.r include=demo.R chunk=distribution-plot plot=true}
```

**Check:** highlighted `distribution-plot` source, "Taken from:
demo.R", a "Plot:" label, and an inline image -- a histogram of the
same data, titled "Distribution of sample data". Confirms two
independently-named plots from the same `demo.R` don't collide.

## Crash and traceback

```{.r include=demo.R chunk=standalone-crash crash=true}
```

**Check:** highlighted `standalone-crash` source, "Taken from:
demo.R", a "Crashes:" label, and a code block showing R's own error:

```
Error in "5"/2 : non-numeric argument to binary operator
```
