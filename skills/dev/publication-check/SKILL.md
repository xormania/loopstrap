---
name: publication-check
description: Check anything that is about to leave the machine for disclosure about work that is not this project. Use before every commit message, PR body, issue, published artifact, and — especially — before importing files from elsewhere into this tree.
---

# Before it leaves the machine

Everything in this repository is public the moment it is pushed, and permanent
after that. A commit message, a PR body, an issue, a code comment, a generated
document, a CI log. Removing a name from a PR body takes a minute; removing it
from git history takes a force-push and re-opens every downstream PR.

The question is not "does this contain a secret". It is:

> **Would a reader learn something about a project that is not this one?**

## Three ways this fails, all observed

**1. Naming it.** The obvious one. A private repository named in a commit
message.

**2. Describing it.** The one that survives a careful proofread. Removing the
name does not remove the disclosure:

> ~~"an earlier generation of this system ran four GitHub workflows including a
> pinned ShellCheck"~~

That sentence has no name in it and still tells a reader that other private
projects exist, that they are related, roughly when, and what their CI looked
like. **Anonymising the label does not anonymise the content.** If a sentence
exists to say "a prior project of mine did X", delete the sentence — the change
should justify itself on its own terms.

**3. Importing it.** The expensive one, and the one care about your own writing
cannot catch. Files copied in from elsewhere carry their origin's vocabulary:
paths, project names, internal terms. A kit imported into this tree contributed
five references across three files, and none of them was written here.

**Read every file you import, in full, before committing it.** Not a diff — the
file. If that is too much to read, it is too much to import.

## The check

The denylist cannot live in this repository, because the list *is* the
disclosure. It lives in `proj/private-terms.txt`, which is gitignored and
excluded from the seal at root.

```
# proj/private-terms.txt — one term per line, blank lines and # comments ignored
# Never commit this file. It is a list of things that must not appear publicly.
some-private-repo
another-project
an-internal-codename
~/some/personal/path
```

Then, before anything leaves:

```shell
# staged changes
git diff --cached | python3 artifacts/instance/tools/publication-check.py --stdin

# a commit message or PR body you are about to use
python3 artifacts/instance/tools/publication-check.py --file /tmp/msg.txt

# files you are importing, before you add them
python3 artifacts/instance/tools/publication-check.py --paths probe/
```

It is deliberately a **local** check. CI cannot run it: the runner is public and
the denylist is not.

## What the check cannot do

It catches failure 1 and it catches failure 3 when the imported text uses a known
term. **It cannot catch failure 2** — describing a project without naming it
produces no matching string. Nothing mechanical will.

So the mechanical check is the floor, not the ceiling. Before publishing, reread
your own prose and ask of each sentence explaining *why*: does this justify the
change, or does it justify it by appeal to work nobody can see? The second kind
is disclosure and it belongs in `proj/`, which is exactly what that directory is
for.

## If it already shipped

Order matters and the first step is not cleanup.

1. **Make the repository private.** One setting, immediate, reversible. Do this
   before anything else; cleanup done under time pressure goes wrong.
2. **Establish what actually leaked.** Names and structure are one thing;
   credentials are another entirely. Scan for both and say which it was, plainly.
3. **Then** decide between removing the files going forward, rewriting history,
   or starting a clean public repository — with the archaeology kept private.

Do not narrate the contents of the leak while fixing it. Repeating a private name
to explain that you should not have said it is still saying it.
