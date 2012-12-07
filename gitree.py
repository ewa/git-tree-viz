#!/usr/bin/env python
import sys
import pygit2
import time
import os.path
import networkx as nx
import pygraphviz as pgv
import pprint
import math


def render_refs (reflist):

    def subst_prefix(str, pmap):
        for prefix in pmap.keys():
            if str.startswith(prefix):
                return pmap[prefix] + str[len(prefix):]
        #fell through
        return str
            

    shorter = [subst_prefix(s,{'refs/heads/':'',
                               'refs/remotes/origin/':'o-'}) for s in reflist]
    return pprint.pformat(shorter)
                            
    

def main(args):
    REPO_PATH = os.path.expandvars('/$HOME/emulator/.git')
    COMPACT = True
    SHORT_UID_LEN=10
    FORCE_TEMPORAL_ORDER=False
    TEMPORAL_ORDER_EQUIV=60*60*24*7     # 1 week, in seconds

    repo = pygit2.Repository(REPO_PATH)
    refs_str = repo.listall_references()
    #print refs_str
    heads_str = [r for r in refs_str if ("refs/heads/" in r or
                                         "refs/remotes/origin/" in r)]
    refs = [repo.lookup_reference(r) for r in heads_str]
    
    ## Build graph
    G = nx.DiGraph()
    roots = []
    heads = []
    
    for r in refs:
        print "Adding head: ", r.name
        ## First make sure all the vertices are there
        for commit in repo.walk(r.resolve().oid, pygit2.GIT_SORT_TIME):
            #print "\t" + commit.hex
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
    #     print r.name
    #     for entry in r.log():
    #         print entry.message, entry.oid_old, entry.oid_new
    #         try:
    #             u = repo[entry.oid_old].hex
    #             v = repo[entry.oid_new].hex
    #             G.add_edge(u,v,key=r.name,color='red')
    #         except KeyError:
    #             pass

    # B = nx.to_agraph(G)
    # B.draw('bar.pdf', format='pdf', prog='dot')
     
    ## Simplify!
    if COMPACT:
        ## XXX -- not sure why I'm not getting all basic blocks in 1st pass.  Need to think about this.
        needed_pruning = True
        passes = 0
        while (needed_pruning):
            passes = passes + 1
            print "Contracting basic blocks: pass %d"%passes
            needed_pruning = False
            for n in G.nodes():
                preds = G.predecessors(n)
                succs = G.successors(n)
                #print n, len(preds), len(succs)
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
                    #print in_e, out_e
                    ncommits=in_e['ncommits']+out_e['ncommits']+1
                    G.add_edge(predecessor, successor, key='ancestry', ncommits=ncommits)
                    G.remove_node(n)        # Implies removing in_edges and out_edges
                    ## Now copy over any other edges
                    for k in set(in_edges.keys()).union(set(out_edges.keys())):
                        if k != 'ancestry':
                            G.add_edge(predecessor, successor, key=k, ncommits=ncommits)
                        
                    needed_pruning = True
    
    print "Rendering graph with Dot"
    A = nx.to_agraph(G)
    A.graph_attr['root']=most_rooty
    head_num = 0
    for n in A.nodes_iter():
        n.attr['label']=n.name[0:SHORT_UID_LEN-1]
        if n.attr['head']:
            head_num = head_num+1
            n.attr['label']=render_refs(G.node[n]['refs'])
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
                #print time.ctime(old_date), time.ctime(date)
                A.add_edge(old_node, node, style="invis")
                ## Only update node relative to which order is forced if > TEMPORAL_ORDER_EQUIV time has passed
                if (date - old_date) > TEMPORAL_ORDER_EQUIV:
                    prev = (node, date)
        
    
    A.draw('foo.pdf', format='pdf', prog='dot')
    # print "HEAD: %s %s" % (head.hex, str(time.ctime(head.commit_time)))
    

if __name__ == '__main__':
    sys.exit(main(sys.argv))
