#!/usr/bin/python3

from subprocess import run, PIPE


def graph_for_bundle(bundle):
    s = _graph_string_for_bundle(bundle)
    p = run("graph-easy --as boxart", input=s, shell=True, stdout=PIPE,
            stderr=PIPE, universal_newlines=True)
    return p.stdout


def _graph_string_for_bundle(bundle):
    s = []
    for rel_src, rel_dst in bundle._bundle['relations']:
        def do_split(rel):
            ss = rel.split(":")
            if len(ss) == 1:
                return rel, ""
            else:
                return ss[0], ss[1]

        src, s_relname = do_split(rel_src)
        dst, d_relname = do_split(rel_dst)
        if s_relname != d_relname:
            relname = s_relname + "," + d_relname
        else:
            relname = s_relname
        s.append("[{}] - {} -> [{}]".format(src, relname, dst))
    return "\n".join(s)
