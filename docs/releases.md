# Releases

## 0.2.0

- Shared Makefile includes (`tent_pole/make-rules/`, `tent_pole/bin/`),
  located via a new `tent-pole pkg-dir` command.
- `file dump --wait`.
- Non-destructive `module reorder` and a new `module dump`.
- `include-deps-filter`, auto-generating Make dependencies from a
  page's `include=`/image/link usage.
- `config api-url`.
- `page push`/`dump`/`update`/`verify` and `module reorder` resolve a
  page by its actual url rather than assuming it matches the page's
  name -- a page whose title has ever collided with a deleted page's
  (Canvas reserves that slug permanently) no longer crashes the build.
- Internal page-to-page markdown links resolve to the linked page's
  real url too, once known, instead of silently breaking after the
  same kind of url drift.
- The python output-capture rules (`%.out`/`%.crash`/`%.stout`/
  `%.test_out`) now run from the script's own directory, not whichever
  directory happened to invoke the rule.
- Quiet, Automake-style `make` output by default -- a short status
  line per recipe instead of the full command; `make V=1` for full
  command visibility.
- `module reorder`'s per-item message now describes adding a module
  item rather than misleadingly saying it's creating the page itself.

## 0.1.0

Initial release.
