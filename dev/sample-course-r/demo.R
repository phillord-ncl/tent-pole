#' # Summarising a numeric vector
#'
#' R stores a sequence of numbers in a *vector*, built with `c()`.
#' Here are six measurements from a short experiment.

#+ setup
data <- c(4, 8, 15, 16, 23, 42)

#' `mean()` and `sd()` give the average and spread of a numeric vector
#' directly, with no loop needed.

#+ summary-stats
cat("Mean:", mean(data), "\n")
cat("SD:", round(sd(data), 2), "\n")

#' A quick plot is often more useful than the numbers alone. `plot()`
#' on a plain numeric vector plots each value against its position;
#' `type = "b"` draws both the points and the lines joining them.

#+ make-plot
plot(data, main = "Sample data", type = "b")

#' Six points alone don't say much about the overall spread. A
#' histogram buckets the values into ranges, which is often a more
#' useful picture of the distribution than the raw sequence.

#+ distribution-plot
hist(data, main = "Distribution of sample data")

#' Mixing text and numbers is a common mistake. R keeps `"5"` as text
#' (a *character* value) unless you convert it with `as.numeric()`
#' first, so arithmetic on it fails rather than guessing what you meant.

#+ standalone-crash
"5" / 2
