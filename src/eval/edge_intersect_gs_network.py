from typing import Iterable, Set, Any
import argparse
import pandas as pd
import data_utils as du


def common_network(annot_file: str, gs_file: str, network_files: Iterable[str]):
    annot_df: pd.DataFrame = du.load_annotation(annot_file)
    gsnet_df: pd.DataFrame = du.load_gsnetwork(gs_file)
    gs_net = du.map_probes(gsnet_df, annot_df)
    common_df: pd.DataFrame = pd.DataFrame()
    for net_file in network_files:
        rv_net: pd.DataFrame = du.load_reveng_network(net_file)
        rv_net_nodes: Set[Any] = set(rv_net.source) | set(rv_net.target)
        if common_df.empty or common_df.shape[0] == 0:
            common_df = gs_net.loc[(gs_net.TFPROBE.isin(rv_net_nodes)) &
                                   (gs_net.TARGETPROBE.isin(rv_net_nodes)), :]
        else:
            common_df = common_df.loc[(common_df.TFPROBE.isin(rv_net_nodes)) &
                                      (common_df.TARGETPROBE.isin(rv_net_nodes)), :]
    return common_df.loc[:, ['TF', 'TARGET']]


def main(annotation_file: str, gs_network_file: str,
         network_files: Iterable[str], out_file: str) -> None:
    common_df = common_network(annotation_file, gs_network_file, network_files)
    common_df.to_csv(out_file, sep='\t', index=False)


if __name__ == "__main__":
    PROG_DESC = """
    Finds a common gold standard network as the intersection of input networks.
    Network intersection is computed as the intersection of edges of the input networks,
    after mapping to the annotation.
    """
    PARSER = argparse.ArgumentParser(description=PROG_DESC)
    PARSER.add_argument("annotation_file",
                        help="""annotation file
                                (a tab seperated file mapping probe to ids)""")
    PARSER.add_argument("gs_network_file",
                        help="""gold standard network
                                (tab seperated file of TF-TARGET interactions)""")
    PARSER.add_argument("network_files", nargs="+",
                        help="""network build from a reverse engineering methods
                                (currenlty supported: eda, tsv, adj)""")
    PARSER.add_argument("-o", "--out_file",
                        type=argparse.FileType(mode='w'), required=True,
                        help="output file in tab-seperated format")
    ARGS = PARSER.parse_args()
    main(ARGS.annotation_file, ARGS.gs_network_file, ARGS.network_files, ARGS.out_file)
