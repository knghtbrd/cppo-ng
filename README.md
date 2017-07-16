# BlocksFree and cppo-ng

This project began as cppo-ng, an attempt to begin evolving cppo, a script
written by Ivan Drucker, to be more pythonic.  It's growing into something a
bit bigger than that, however.  See [HISTORY.md][] if you want details about
where it started and how it's gotten here.

The goal is no longer simply to clean up the `cppo` script!


## What we actually want

TL;DR:

* A scriptable AppleCommander-ac-like tool
* `cppo` with all of its present external interface.
* The features of CiderPress from the command line
* Native feel on Windows, Mac, and Linux at the minimum
* Future: A GUI tool that can display characters natively

It should be quite doable to build a tool like AppleCommander-ac with the
ability to read, write, convert, dump, and other things that one currently does
with AppleCommander.  Moreover, it should be no major thing to have it be able
to output data in a mechanical format that can be processed by shell scripts or
JSON that can be processed by anything more functionally complete.  That will
resolve the issues of the thing being written in Python if you need something
else for the majority of cases.  It's not a perfect solution for Windows
outside of development tools, but development tools are the primary application
for this.

We have tools that need `cppo` and we cannot assume that we're the only ones
who do.  We could maintain the existing script, but it has both bugs and
limitations.  Better to emulate the old cppo using a new interface.  You can do
this with a runner that provides the old interface alongside the modern one.
That's the plan.

The possibility of using [urwid][] exists to provide a textual interface.  It's
probably desirable for any GUI to be abstract enough to have multiple
implementations, but the idea that you might want a textual interface should be
considered.


## Documentation

If you'd like to write some.  :)


## Contributions

Yes please!

[HISTORY.md]: HISTORY.md
[urwid]: http://urwid.org/
