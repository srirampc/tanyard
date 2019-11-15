import argparse
from typing import List
import numpy as np
import pandas as pd
import networkx as nx
from mpi4py import MPI
import data_utils as du


def block_low(rank, size, array_length):
    return (rank*array_length) / size


def block_high(rank, size, array_length):
    return  (((rank+1)*array_length)/size) - 1


def block_size(rank, size, array_length):
    return block_low((rank+1), size, array_length) - block_low(rank, size, array_length)


def block_owner(idx, size, array_length):
    return ((size) * ((idx)+1)-1)/(array_length)


def select_edges(net_df: pd.DataFrame, wt_attr_name: str = 'wt',
                 max_edges: int = None):
    if max_edges is None or max_edges >= net_df.shape[0]:
        return net_df
    cur_cols = net_df.columns
    maxwt_attr_name = wt_attr_name + '_max'
    net_df[maxwt_attr_name] = net_df[wt_attr_name].abs()
    net_df = net_df.nlargest(n=max_edges, columns=maxwt_attr_name)
    #print(net_df.iloc[0, :])
    return net_df.loc[:, cur_cols]


def rand_label_distribution(nsize: int,
                            nrank: int,
                            network_file: str,
                            wt_attr_name: str = 'wt',
                            max_edges: int = None) -> List[int]:
    net_df: pd.DataFrame = select_edges(du.load_reveng_network(network_file),
                                        wt_attr_name, max_edges)
    rev_net: nx.Graph = nx.from_pandas_edgelist(net_df, edge_attr=wt_attr_name)
    n_nodes = nx.number_of_nodes(rev_net)
    #node_names_map = {y:x for x, y in zip(range(n_nodes), nx.nodes(rev_net))}
    #print(node_names_list[0], node_names_map['249052_at'])
    rev_net_nx = nx.convert_node_labels_to_integers(rev_net)
    if nsize is None or nrank is None:
        proc_nodes = n_nodes
        proc_nodes_begin = 0
        # proc_nodes_end = n_nodes - 1
    else:
        proc_nodes_begin = block_low(nrank, nsize, n_nodes)
        proc_nodes = block_size(nrank, nsize, n_nodes)
        # proc_nodes_end = block_high(nrank, nsize, n_nodes)
    sp_results = np.zeros((proc_nodes, n_nodes), dtype='i')
    for vdx in range(proc_nodes):
        idx = proc_nodes_begin + vdx
        spx_dict = nx.single_source_shortest_path_length(rev_net_nx, idx)
        for tgt, slength in spx_dict.items():
            sp_results[vdx, tgt] = slength
    return n_nodes, sp_results

def main(network_file, max_edges, out_file):
    comm = MPI.COMM_WORLD
    rank = comm.Get_rank()
    size = comm.Get_size()
    n_nodes, prop_data = rand_label_distribution(size, rank, network_file,
                                                 'wt', max_edges)
    recv_arr = None
    if rank == 0:
        recv_arr = np.empty([n_nodes, n_nodes], dtype='i')
    comm.Gather(prop_data, recv_arr, root=0)
    if rank == 0:
        #for i in range(size):
        #    assert np.allclose(recv_arr[i,:], i)
        if out_file:
            np.savetxt(out_file, recv_arr)
        else:
            print(recv_arr)

if __name__ == "__main__":
    PROG_DESC = """Shortest Path distribution"""
    ARGPARSER = argparse.ArgumentParser(description=PROG_DESC)
    ARGPARSER.add_argument("-x", "--max_edges", type=int,
                           help="""maximum number of edges""")
    ARGPARSER.add_argument("-o", "--out_file",
                           type=str,
                           help="output file in text format")
    ARGPARSER.add_argument("network_file")
    CMDARGS = ARGPARSER.parse_args()
    main(CMDARGS.network_file, CMDARGS.max_edges, CMDARGS.out_file)
