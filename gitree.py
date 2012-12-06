#!/usr/bin/env python
import sys
import pygit2
import time
import networkx as nx

def main(args):
    REPO_PATH = '/home/andersoe/sys3/.git'

    repo = pygit2.Repository(REPO_PATH)
    refs_str = repo.listall_references()
    print refs_str
    refs = [repo.lookup_reference(r) for r in refs_str]
    print refs

    G = nx.MultiDiGraph()

    print "HEAD: %s %s" % (head.hex, str(time.ctime(head.commit_time)))
    

if __name__ == '__main__':
    sys.exit(main(sys.argv))
