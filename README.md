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

    usage: gitree.py [-h] [-T FORMAT] [-p DIR | -r DIR] [-R R] [-c | -n]
		     [--abbrev N] [-t [S]]
		     outfile
    
    optional arguments:
      -h, --help            show this help message and exit
    
    output arguments:
      outfile               Output file name, REQUIRED. '-' for stdout
      -T FORMAT             Dot output format (default: guessed fromm outfile)
    
    Git options:
      -p DIR, --path DIR    Starting path to look for repository (default: '.')
      -r DIR, --repo DIR    Exact path to Git repository
      -R R, --remote R      Include branches from R. May be repeated. (default:
			    origin)
    
    Graph options:
      -c, --compact         Compact basic blocks (default)
      -n, --no-compact      Do not compact basic blocks
      --abbrev N            Abbreviate hashes to N characters (0 for no
			    abbreviation). Default=8
      -t [S], --temporal [S]
			    Force temporal order for commits > S seconds apart
			    (S=604800 if no argument)
