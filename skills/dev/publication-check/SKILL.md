---
name: publication-check
description: Check anything about to leave the machine for disclosure the operator did not choose to publish. Use before every commit message, PR body, issue, comment and published artifact, and before importing files from elsewhere into a tracked tree.
---

# Before it leaves the machine

An agent publishing on an operator's behalf is publishing under their name, from
their machine, with access to material they never chose to make public. A commit
message, a PR body, an issue, a code comment, a generated document, a CI log —
all of it leaves, and most of it is permanent. Removing a name from a PR body
takes a minute; removing it from git history takes a force-push and re-opens
every downstream PR.

The question is not "does this contain a secret". Secrets are the easy case and
scanners already find them. The question is:

> **Would a reader learn something about work the operator has not published?**

## Three ways this fails

**1. Naming it.** A private repository, an employer, a codename, a person. The
obvious case, and the only one most people check for.

**2. Describing it.** The one that survives a careful proofread, because removing
the name does not remove the disclosure:

> *"an earlier generation of this system ran four CI workflows including a pinned
> linter"*

No name in it. It still discloses that other private projects exist, that they
are related, roughly when, and how they were built. **Anonymising the label is
not anonymising the content.**

The tell: a sentence whose only job is to say *a prior project did X*. Delete it.
A change should justify itself on its own terms — if it cannot, the justification
was never available to the reader anyway.

**3. Importing it.** The expensive one, and the one that care about your own
writing cannot catch. Files copied in from elsewhere carry their origin's
vocabulary: paths, project names, internal terms, dated decision logs. An agent
scanning its own prose while copying someone else's wholesale will produce a
clean-looking commit that leaks on every line it did not write.

**Read every file you import, in full, before committing it.** Not the diff — the
file. If it is too long to read, it is too long to import unreviewed.

## The check

The denylist cannot live in the repository being checked, because the list *is*
the disclosure. It is operator-supplied and found in this order:

```
--denylist PATH
$PUBLICATION_DENYLIST
./proj/private-terms.txt        untracked working notes
./.private-terms                untracked
~/.config/publication-denylist  per-operator, all repositories
```

The per-operator location is usually right: the same names must not leak from
*any* repository, so the list should outlive any single project.

```shell
publication-check.py --file /tmp/commit-message.txt
git diff --cached | publication-check.py --stdin      # scans ADDED lines only
publication-check.py --paths imported-kit/            # before you commit an import
```

Two properties worth knowing:

- **Fail-closed.** No denylist is exit 2, never exit 0. *"I could not check"* and
  *"I checked and it was clean"* are different answers, and conflating them is
  how a check becomes decorative.
- **Diff-aware.** Removing a reference puts it in the diff as a deleted line, so
  a raw diff scan flags the act of fixing the problem. Only additions can leak.

Because the denylist is private, hosted CI generally cannot run this. Local
preflight by design.

## What the check cannot do

It catches failure 1, and failure 3 when the imported text uses a known term.

**It cannot catch failure 2.** A description that avoids every term produces no
match. This is not a gap to be closed later — there is no string to search for.

So the scan is the floor, not the ceiling. Before publishing, reread your own
prose and ask of every sentence that explains *why*: does this justify the change
on its own terms, or by appeal to work the reader cannot see? The second kind is
disclosure, and it belongs in an untracked note.

## If it already shipped

Order matters, and the first step is not cleanup.

1. **Make it private, or take it down.** One setting, immediate, reversible.
   Before anything else — cleanup under time pressure goes wrong.
2. **Establish what actually left.** Names and structure are one thing;
   credentials are another entirely. Scan for both and say which it was, plainly
   and once.
3. **Then** choose: remove going forward, rewrite history, or start a clean
   public repository with the history kept private.

And while fixing it: **do not narrate the contents.** Repeating a private name to
explain that it should not have been said is still saying it. Report counts,
paths and severity — not quotes.
