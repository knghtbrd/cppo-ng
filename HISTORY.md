# cppo and the history of BlocksFree

When Ivan Drucker began writing A2SERVER, he needed tools that ran under Linux,
not Windows.  One of these exists in the form of AppleCommander, originally
written by Rob Greene and others and currently maintained by David Schmidt who
uses it as a library as part of ADTPro, the Apple Disk Transfer utility for
ProDOS.  There were a couple of issues with AppleCommander though, namely that
it was not written to handle Apple IIgs resource forks the way that worked with
netatalk, nor did it create things like AppleDouble files.  He needed a tool
that did, and so he wrote one for bash, the common Linux default shell script
interpreter.

It got a simple rewrite in Python because the code was extremely slow on
devices like the Raspberry Pi.  This code is effectively "Bash in Python", but
it solved the immediate problem.  Ivan made it a to-do list item to revisit
this if he ever got time and rewrite the code properly.


## Why did Ivan write something new?

Given the existence of AppleCommander which already exists, even if it lacks
the specific AppleDouble features we want and CiderPress, why not fix what we
want instead of writing something new?

Regarding CiderPress, it's effectively the standard tool which many great
features, but it's a Windows only program, and a GUI program to boot.  There
are some command-line test programs and they're even portable, but they don't
expose the functions we need, and the author isn't interested in rewriting
things for Linux.

AppleCommander didn't write AppleDouble files and didn't handle IIgs resource
forks the way Ivan needed it to.  To date it still doesn't build on Linux
without patching its build system.  And while A2SERVER doesn't use it (as it
pulls in the full JDK on Raspberry Pi to do so), A2CLOUD includes it as part of
ADTPro and even includes a convenience script to "make it feel native".


## A brief opinion Oracle and its effect on Java

If you understand this, you may wish to skip to the next section.

We have no desire to spend one more second of our time with Java than is
absolutely minimally essential.  This is not because of Java's flaws.  No,
these are largely irrelevant.  Rather, Java is regarded as a pariah because of
parent company Oracle.

The basic details are in [this InfoWorld article][oracle-v-google].

A concrete example in C:

```c
int
main(const int argc, const char *argv[])
{
	return 0;
}
```

Every C program has something like that.  If you're not a programmer, I'll
explain.  That declares a (do-nothing) function named "main" which receives a
number we're calling "argc" and an array of strings (character arrays) we call
"argv".  It simply returns 0 (an integer).  The names "argc" and "argv" are
convention, but that there's a thing called "main" that takes an integer and an
array of strings and returns an integer...  That's part of the standard.

If you don't have that, it's not C.

Oracle claims they own that.  Not the compiler or their own libraries--those
they do own, unequivocally.  They say that the own the *concept* of something
that must be named main and must take an integer and a string array, and must
return an integer.  And if you do that without their permission, you owe them
millions of dollars.

Sun made it a freely-licensed standard.  Oracle says that you must
retroactively pay for the privilege of having used it now that you depend on
having it, if they don't like what you did with it.  It is this reason why we
have no interest in further development using Java, beyond the minimum effort
necessary to continue using it until such time as we no longer require it.


## Why did BlocksFree start rewriting cppo?

Originally plans were to clean up cppo a bit around the edges, and leave it.
Then, the plan was to separately port AppleCommander to Python so that cppo,
A2SERVER's GS/OS network boot volume installer, cross-development toolchains,
and whatever else could just use it.  When complete enough, we'd just rewrite
cppo to use the "Apple-Pi-Commander" framework to do what it does now for
compatibility.

The thing is that AppleCommander is a big software package, porting it one
class at a time is not a trivial task in any way you can test it, and cppo
works now for what it does.  Both cppo and AppleCommander have bugs (and so
does CiderPress for that matter), but it made more sense to begin building
"proper" disk image handling in parallel with cppo's existing code so that the
new implementation could be tested against the old.


## Why was Python 2 support dropped?

In part because it's very hard to de-shellify the code on one hand and worry
about avoiding breaking either Python 2.7 or 3.x.  Also in part because if we
accept a dependency on a reasonably modern Python 3.x, lots of things become
easier.

In part because it doesn't make sense to begin writing new code for Python 2.7
in 2017.  It was to be declared end-of-life in 2015, then in 2017, and now
finally in 2020.  There are very good reasons why Python 2.x needs to be
retired now.  The entire world has learned to accept Unicode, and Python 2.7 at
best cannot effectively cope with that reality.

In part because the only thing keeping Python 2.7 from being abandoned two
years ago was that there were several major holdouts that had not yet made the
leap to Python 3.x, such as Django, wxPython, and any operating system released
by Apple.  And by mid-2017, all of those save Apple have been resolved, with
wxPython finally having an alpha release of wxPython 4, reflecting a complete
rewrite of the code, but one that is already deemed to be a pretty solid
release.

In part because the lone holdout, Apple, appears poised to NEVER accept Python
3.x on their system, just like they have refused any modern version of GNU bash
nor any other tool or software using the GNU GPL version 3.

This last point was a major reason *not* to use Python 3.x when Ivan ported
cppo to Python, but the inevitablility that everyone else was moving there made
him decide to expend the effort to ensure forward-compatibility.  But it does
not really hold up anymore.

Installing Python 3.6 (the current version) is more easily done than installing
the latest version of Java.


## The legal history of this project

The cppo source code refers you here for why the license is now the GNU GPL.

Nobody involved with this project has a law degree and thus nothing here is or
should be regarded as legal advice.  Programmers and technical people think
like lawyers in many ways, but they've got training, experience, and access to
piles of common law court decisions we haven't.  If you feel you need legal
advice, find one.

That said, technical people often play fast and loose with Copyright, and that
can really cause problems when pedantically paranoid eyes examine these things
(hello Debian!), it's best to have covered your bases.  You're not paranoid if
they're actually out to get you, and intellectual property trolls *are*.

When Ivan Drucker wrote cppo in Bash, he didn't feel a need for a license for
simple shell scripts.  Sure cppo was clever, but it was a shell script
nonetheless.  It's part of A2SERVER and A2CLOUD which are larger sets of
scripts, but still.  When pressed for a license, Ivan chose "WTFPL", probably
the strongest statement you'll likely find rejecting Copyright that still
provides an effective license: <http://www.wtfpl.net/>

So why change it?  Well, Joseph Carter hasn't so much as looked at a hex dump
of a raw Apple II filesystem since about 1994.  When he began rewriting cppo in
2017, he read every electronic resource he could find.  And some of those are
source code, which is particularly important to know how to gracefully handle
software which produces technically invalid but still recoverable output.

If you're Debian, Joseph, a Copyright attorney, or just paranoid, your reaction
to that last line may have been, "Uh oh."  Because while you cannot Copyright
an algorithm (and any patents will be long expired by now), you *do* own
Copyright to your expression of them.  Truly there's a finite number of ways to
access a binary data format, but to be truly safe examining someone else's
code, you need a clean room process: Someone reads the code and documents what
it does algorithmically (since that's not subject to Copyright.)  Someone ELSE
writes code that implements the algorithm.

That safety precaution didn't happen here.  But that means that if we aren't
following the licenses of the software examined without precaution, you'd have
potential for problems.  So we'll take precautions at the other end: On
information and belief, the licenses of each software package involved allow
for derived works licensed under the GNU General Public License, version 2 or
later.  Works for us--as long as others can see it, take it, use it, fix it,
etc., it meets the project goal.

We will try to be liberal with crediting other software authors.  That's right
and proper.  We benefit from cool things they did.  And honestly, if we got
nothing more than time saved testing a couple hundred gigabytes of disk images
to find out how other people's software produced technically invalid but usable
disk images and how to salvage them, we owe them immeasurable gratitude!

[oracle-v-google]: http://www.infoworld.com/article/2617268/java/oracle-vs--google--who-owns-the-java-apis-.html
