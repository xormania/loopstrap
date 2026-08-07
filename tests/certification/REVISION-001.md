# Certification revision 001

The original neutral-workspace witness treated any ancestor path named `.git`
as a repository. The Work Mode `/tmp` root contains an inert `.git` placeholder
that Git itself does not recognize, making the test environment-dependent.

The witness now asks Git whether the certification root belongs to a work tree.
It still requires the nested disposable probe repository to exist and still
fails if the runner is placed inside a real enclosing repository.
