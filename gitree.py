#!/usr/bin/env python

# Copyright 2012, 2013 Eric Anderson
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or (at
# your option) any later version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from __future__ import print_function
import sys
import pygit2
import time
import os.path
import networkx as nx
import pygraphviz as pgv
import pprint
import math
import argparse
import re
import subprocess

def eprint(*objs):
    print(*objs, end='\n', file=sys.stderr)

def render_refs (reflist):

    local_re = re.compile('^refs/heads/([^/]+)')
    remote_re = re.compile('^refs/remotes/([^/]+)/([^/]+)')

    local_names=set()
    full_remotes=set()

    for s in reflist:
        l = local_re.match(s)
        if l:            
            ##eprint(s, "local", l.groups())
            local_names.add(l.groups()[0])
        r = remote_re.match(s)
        if r:
            ##eprint(s, "remote", r.groups())
            full_remotes.add((r.groups()[0], r.groups()[1]))
    # Remotes with heads matching the local name of this ref
    matching_remotes = [r for (r,n) in full_remotes if n in local_names]
    # String representation (remote/name) of remote heads not matching the local name
    unmatch_remotes = ['{}/{}'.format(r,n) for (r,n) in full_remotes if n not in local_names]
    
    ##eprint(reflist, '=', local_names, matching_remotes, unmatch_remotes)
    ## XXX Don't bother listing remotes which match the local info
    labels=list(local_names)+unmatch_remotes
    return ",".join(labels)

            
                            

def parse(args):
    def GitableDir(path):

        """

        A directory in which you can do Git things -- i.e. a git
        repository or a subdirectory of a checked_out repository.

        Parameters:
          path (string): A path name.  \"~\"-expansion will be performed.

        Returns:
          Tuple (supplied path name, absolute path name) upon success

        Raises:
          argparse.ArgumentTypeError if no Git repository is found
        
        """
        
        realpath=os.path.abspath(os.path.expanduser(path))
        if not os.path.isdir(realpath):
            err_str = "'{}' does not exist or is not a directory".format(path)
            raise argparse.ArgumentTypeError(err_str)
        try:
            repo_path=pygit2.discover_repository(realpath)
            return(path,repo_path)
        except KeyError, e:
            err_str = "No Git repo found in {} or its parent dirs".format(e.args[0])
            raise argparse.ArgumentTypeError(err_str)

    def ExactGitDir(path):
        """        
        The path of a Git repository. Searching from working
        directories and subdirectories is _not_ performed.

        Parameters:
          path (string): A path name.  \"~\"-expansion will be performed.

        Returns:
          Tuple (supplied path name, absolute path name) upon success

        Raises:
          argparse.ArgumentTypeError if no Git repository is found        
        """

        realpath=os.path.abspath(os.path.expanduser(path))
        try:
            r = pygit2.Repository(realpath)
            return (path, realpath)
        except KeyError, e:
            err_str = "No git repo found in {}".format(e.args[0])
            raise argparse.ArgumentTypeError(err_str)
        

    #Very first thing we do, query dot for its supported output formats
    fmts=None
    fmt_info=" This script was unable to query Dot for its list of supported formats."
    try:
        dot = subprocess.Popen(['dot','-Txxx_no_way_this_format_exists'],
                               stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        (out,err)=dot.communicate()         # Expect error
        (junk,fmt_list)=err.split("Use one of:")
        fmts=fmt_list.strip().split()
        fmt_info=" Supported formats are {}".format(fmts)
    except OSError, e:
        pass            
    except ValueError, e:
        pass
    
    parser=argparse.ArgumentParser()


    out_opts=parser.add_argument_group('output arguments')
    out_opts.add_argument('outfile',type=argparse.FileType('w'),
                        help="Output file name, REQUIRED. '-' for stdout")
    
    out_opts.add_argument('-T',dest='format',
                        help="Dot output format (default: guessed from outfile)."+fmt_info)
    
    git_opts = parser.add_argument_group('Git options')
    dir_opts = git_opts.add_mutually_exclusive_group()
    ## "--repo" and "--path" both provide the same information, but
    ## use different handling/validation routines. Making them
    ## mutually_exclusive AND giving them the same 'dest' has the
    ## desired effect of ensuring that the DEFAULT "--path" doesn't
    ## get validated if "--repo" is supplied.
    
    dir_opts.add_argument('-p','--path',dest='repo',type=GitableDir,
                          default=".", metavar='DIR',
                          help="Starting path to look for repository (default: '%(default)s')")
    dir_opts.add_argument('-r','--repo',dest='repo',type=ExactGitDir,
                        metavar='DIR', help="Exact path to Git repository")
    git_opts.add_argument('-R','--remote', dest='remotes',action='append',
                          metavar='R',
                          help='Include branches from R.  May be repeated. (default: origin)')
    

    graph_opts=parser.add_argument_group('Graph options')
    
    compact_opts=graph_opts.add_mutually_exclusive_group()
    compact_opts.add_argument('-c','--compact',dest='compact',
                              action='store_true',default=True,
                              help="Compact basic blocks (default)")
    compact_opts.add_argument('-n','--no-compact',dest='compact',
                              action='store_false',
                              help="Do not compact basic blocks")
    graph_opts.add_argument('--abbrev',metavar="N",type=int, default=8,
                        help="Abbreviate hashes to N characters (0 for no abbreviation).  Default=%(default)d")
    graph_opts.add_argument('-t','--temporal',nargs='?', metavar='S',
                        const=60*60*24*7,     # 1 week, in seconds
                        help='Force temporal order for commits > S seconds apart (S=%(const)d if no argument)')


    args=parser.parse_args()

    ## Format is optional, unless it's not
    if args.format is None:
        guess_fmt=os.path.splitext(args.outfile.name)[-1].lower()[1:]
        if guess_fmt == '':
            parser.error("No format (-T) supplied, and cannot guess from outfile '{}'".format(args.outfile.name))
        else:
            args.format = guess_fmt
    # Check format
    dot = subprocess.Popen(['dot','-T',args.format],
                           stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    (out,err)=dot.communicate()         # Expect error
    if dot.returncode != 0:
        err_msg = "Dot doesn't like format '{}': {}".format(args.format,err)
        parser.error(err_msg)
    
    ## "Default" value of remotes is ['origin'], but "remotes" is an append option, so the default never gets replaced, only added to
    if args.remotes is None:
        args.remotes = ['origin']
    return args

def main(args):
    args = parse(args)
    eprint(args)
    
    REPO_PATH = args.repo[1]
    SHORT_UID_LEN=args.abbrev
    if args.temporal is None:
        FORCE_TEMPORAL_ORDER=False
    else:
        FORCE_TEMPORAL_ORDER=True
        TEMPORAL_ORDER_EQUIV=args.temporal

    repo = pygit2.Repository(REPO_PATH)
    refs_str = repo.listall_references()
    #eprint("all refs", refs_str)
    ref_filter_str="^(refs/heads/)|"+("|".join(['(refs/remotes/'+re.escape(remote)+'/)' for remote in args.remotes]))
    eprint(ref_filter_str)
    ref_filter=re.compile(ref_filter_str)
    heads_str = [r for r in refs_str if ref_filter.match(r)]
    #eprint("heads of interest", heads_str)
    refs = [repo.lookup_reference(r) for r in heads_str]
    #return -1
    
    ## Build graph
    G = nx.DiGraph()
    roots = []
    heads = []
    
    for r in refs:
        eprint("Adding head: ", r.name)
        ## First make sure all the vertices are there
        for commit in repo.walk(r.resolve().oid, pygit2.GIT_SORT_TIME):
            #eprint "\t" + commit.hex
            G.add_node(commit.hex)
        ## Then create edges
        for commit in repo.walk(r.resolve().oid, pygit2.GIT_SORT_TIME):
            for p in commit.parents:
                G.add_edge(p.hex, commit.hex, ncommits=1)
        
        ## Mark heads
        head_node = G.node[r.resolve().hex]
        head_node['head']=True
        heads.append(r.resolve().hex)
        try:
            head_node['refs'].append(r.name)
        except KeyError:
            head_node['refs']=[r.name]
        
    ##Find roots (commits w/o parents)
    for n in G.nodes():
        if len(G.in_edges(n)) == 0:
           G.node[n]['root']=True
           roots.append(n)

    ## Estimate the rootyness of each root
    max_tc = 0
    most_rooty = None
    for n in roots:
        lengths = nx.single_source_shortest_path_length(G,n)
        # Don't actually care what the lenghts are, just how many nodes I can reach
        tc_size = len(lengths)
        G.node[n]['tc_size']=tc_size
        if tc_size > max_tc:
            max_tc = tc_size
            most_rooty = n


    H = nx.MultiDiGraph()
    H.add_nodes_from(G.nodes(data=True))
    for (u,v,data) in G.edges_iter(data=True):
        H.add_edge(u,v,key='ancestry',attr_dict=data)
    G = H

    # ## Annotate with reflog-specific edges
    # for r in refs:
    #     eprint r.name
    #     for entry in r.log():
    #         eprint entry.message, entry.oid_old, entry.oid_new
    #         try:
    #             u = repo[entry.oid_old].hex
    #             v = repo[entry.oid_new].hex
    #             G.add_edge(u,v,key=r.name,color='red')
    #         except KeyError:
    #             pass

    # B = nx.to_agraph(G)
    # B.draw('bar.pdf', format='pdf', prog='dot')
     
    ## Simplify!
    if args.compact:
        ## XXX -- not sure why I'm not getting all basic blocks in 1st pass.  Need to think about this.
        needed_pruning = True
        passes = 0
        while (needed_pruning):
            passes = passes + 1
            eprint("Contracting basic blocks: pass %d"%passes)
            needed_pruning = False
            for n in G.nodes():
                preds = G.predecessors(n)
                succs = G.successors(n)
                #eprint n, len(preds), len(succs)
                if (len(preds) == 1 and
                    len(succs) == 1 and
                    not 'root' in G.node[n] and
                    not 'head' in G.node[n]):
                    predecessor =  preds[0]
                    successor = succs[0]
                    in_edges=G.edge[predecessor][n]
                    out_edges=G.edge[n][successor]
                    
                    # Just deal with the "ancestry" edges for everything important
                    in_e = G.edge[predecessor][n]['ancestry']
                    out_e = G.edge[n][successor]['ancestry']
                    ## Include the number of commits of the edges and node being replaced
                    #eprint in_e, out_e
                    ncommits=in_e['ncommits']+out_e['ncommits']+1
                    G.add_edge(predecessor, successor, key='ancestry', ncommits=ncommits)
                    G.remove_node(n)        # Implies removing in_edges and out_edges
                    ## Now copy over any other edges
                    for k in set(in_edges.keys()).union(set(out_edges.keys())):
                        if k != 'ancestry':
                            G.add_edge(predecessor, successor, key=k, ncommits=ncommits)
                        
                    needed_pruning = True
    
    eprint("Rendering graph with Dot")
    A = nx.to_agraph(G)
    A.graph_attr['root']=most_rooty
    head_num = 0
    for n in A.nodes_iter():
        if SHORT_UID_LEN >0:            
            n.attr['label']=n.name[0:SHORT_UID_LEN-1]
        else:
            n.attr['label']=n.name
        if n.attr['head']:
            head_num = head_num+1
            n.attr['label']=render_refs(G.node[n]['refs'])
            if len(n.attr['label']) > 80:
                eprint("Long label:", n.attr['label'], "length:", len(n.attr['label']))
            n.attr['shape']='box'
            n.attr['style']='bold,filled'
            n.attr['colorscheme']='set312'
            n.attr['color']=(head_num % 12)+1
            n.attr['fontsize']=20
        if n.attr['root']:
            n.attr['shape']='diamond'
            n.attr['style']='bold'
    for e in A.edges_iter():
        #e.attr['len']=math.log(int(e.attr['ncommits']))+1
        e.attr['label']=e.attr['ncommits']


    ## Add invisible order-forcing edges
    if FORCE_TEMPORAL_ORDER:
        node_date = []
        for n in A.nodes_iter():
            t = repo[n].commit_time
            node_date.append((n,t))
        node_date.sort(key=lambda x: x[1])
        prev = None
        for (node, date) in node_date:
            if prev is None:
                prev = (node, date)
            else:
                old_node, old_date = prev
                #eprint time.ctime(old_date), time.ctime(date)
                A.add_edge(old_node, node, style="invis")
                ## Only update node relative to which order is forced if > TEMPORAL_ORDER_EQUIV time has passed
                if (date - old_date) > TEMPORAL_ORDER_EQUIV:
                    prev = (node, date)
        
    A.draw(args.outfile, args.format, prog='dot')
    # eprint "HEAD: %s %s" % (head.hex, str(time.ctime(head.commit_time)))
    

if __name__ == '__main__':
    sys.exit(main(sys.argv))
