# Git Tree Visualization Tool

This is meant to help visualize large and/or complicated development
efforts, especially the patterns of merging and branching.

The main difference from standard history-viewing tools like gitk is
this tool will "collapse" linear sequences of commits into a single
edge, so you're left with the topology of roots, heads, and places
where development split or merged.


# Requirements

* [libgit2](http://libgit2.github.com/) and
  [Pygit2](https://github.com/libgit2/pygit2) to process your repository.
* [NetworkX](http://networkx.lanl.gov/) for graph transformations.
* [Graphviz](http://www.graphviz.org/) and
  [PyGraphviz](http://networkx.lanl.gov/pygraphviz/) for pretty
  pictures.
  
# Usage

There's no command-line interface yet.  Options (including the
location of the repository!) are hard-coded in the file at the
beginning of main().


