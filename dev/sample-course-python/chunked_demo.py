#' # Working with a list of measurements
#'
#' Python stores a sequence of numbers as a list.

#+ setup
data = [4, 8, 15, 16, 23, 42]

#' `sum()`/`len()` give the total and count directly.

#+ summary-stats
total = sum(data)
count = len(data)
print("Total:", total)
print("Count:", count)

#' An average sometimes lives inside a small helper function -- this
#' chunk marker is nested inside one, picking out just its own body
#' rather than the whole function definition.

def average(values):
    #+ average-body
    return sum(values) / len(values)

#' Calling it is just ordinary code, not part of any chunk.

print(average(data))
