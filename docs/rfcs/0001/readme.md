Rabbit Request For Comment Process
==================================

Rabbit software must be designed in close collaboration with our end-users. Part of this process involves open discussion in the form of Request For Comment (RFC) documents. The remainder of this document presents the RFC process for Rabbit.

History & Philosophy
-------------------

NNF RFC documents are modeled after the long history of IETF RFC documents that describe the internet. The philosophy is captured best in [RFC 3](https://www.rfc-editor.org/rfc/rfc3)

> The content of a [...] note may be any thought, suggestion, etc. related to
the HOST software or other aspect of the network.  Notes are encouraged to
be timely rather than polished.  Philosophical positions without examples
or other specifics, specific suggestions or implementation techniques
without introductory or background explication, and explicit questions
without any attempted answers are all acceptable.  The minimum length for
a [...] note is one sentence.
>
> These standards (or lack of them) are stated explicitly for two reasons.
First, there is a tendency to view a written statement as ipso facto
authoritative, and we hope to promote the exchange and discussion of
considerably less than authoritative ideas.  Second, there is a natural
hesitancy to publish something unpolished, and we hope to ease this
inhibition.


When to Create an RFC
---------------------
New features, improvements, and other tasks that need to source feedback from multiple sources are to be written as Request For Comment (RFC) documents.

Metadata
--------
At the start of each RFC, there must include a short metadata block that contains information useful for filtering and sorting existing documents. This markdown is not visible inside the document.

```
---
authors: John Doe <john.doe@company.com>, Jane Doe <jane.doe@company.com>
state: prediscussion|ideation|discussion|published|committed|abandoned
discussion: (link to PR, if available)
----
```

Creation
---------

An RFC should be created at the next freely available 4-digit index the GitHub RFC folder. Create a folder for your RFC and write your RFC document as `readme.md` using standard Markdown. Include additional documents or images in the folder if needed.

Add an entry to `/docs/rfcs/index.md`

Add an entry to `/mkdocs.yml` in the `nav[RFCs]` section

Push
----
Push your changes to your RFC branch

```
git add --all
git commit -s -m "[####]: Your Request For Comment Document"
git push origin ####
```

Pull Request
------------
Submit a PR for your branch. This will open your RFC to comments. Add those individuals who are interested in your RFC as reviewers.

Merge
-----
Once consensus has been reached on your RFC, merge to main origin. 

