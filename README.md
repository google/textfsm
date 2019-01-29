TextFSM
=======

Python module which implements a template based state machine for parsing
semi-formatted text. Originally developed to allow programmatic access to
information returned from the command line interface (CLI) of networking
devices.

The engine takes two inputs - a template file, and text input (such as command
responses from the CLI of a device) and returns a list of records that contains
the data parsed from the text.

A template file is needed for each uniquely structured text input. Some examples
are provided with the code and users are encouraged to develop their own.

By developing a pool of template files, scripts can call TextFSM to parse useful
information from a variety of sources. It is also possible to use different
templates on the same data in order to create different tables (or views).

TextFSM was developed internally at Google and released under the Apache 2.0
licence for the benefit of the wider community.

[**See documentation for more details.**](https://github.com/google/textfsm/wiki/TextFSM)

Before contributing
-------------------
If you are not a Google employee, our lawyers insist that you sign a Contributor
Licence Agreement (CLA).

If you are an individual writing original source code and you're sure you own
the intellectual property, then you'll need to sign an
[individual CLA](https://cla.developers.google.com/about/google-individual).
Individual CLAs can be signed electronically. If you work for a company that
wants to allow you to contribute your work, then you'll need to sign a
[corporate CLA](https://cla.developers.google.com/clas).
The Google CLA is based on Apache's. Note that unlike some projects
(notably GNU projects), we do not require a transfer of copyright. You still own
the patch.

Sadly, even the smallest patch needs a CLA.
