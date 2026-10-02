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

## Plot output

```{.r include=demo.R chunk=make-plot plot=true}
```

**Check:** highlighted `make-plot` source, "Taken from: demo.R", a
"Plot:" label, and an inline image -- a line-and-point plot of
`4, 8, 15, 16, 23, 42` titled "Sample data".

## Crash and traceback

```{.r include=demo.R chunk=standalone-crash crash=true}
```

**Check:** highlighted `standalone-crash` source, "Taken from:
demo.R", a "Crashes:" label, and a code block showing R's own error:

```
Error in "5"/2 : non-numeric argument to binary operator
```
