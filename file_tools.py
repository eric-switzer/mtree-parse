'''common data management tasks'''
import shelve
import utils

# TODO: prune common subdirectories to largest encompassing directory
def find_largest_common_directories(tree_shelvename, leaves_shelvename):
    '''find the largest directories that share the same checksum of all data
    under them'''
    tree = shelve.open(tree_shelvename, 'r')
    leaves = shelve.open(leaves_shelvename, 'r')
    parent_tree = utils.make_parent_tree(tree)

    md5dict = {}
    md5_size_dict = {}
    for leafkey in leaves.keys():
        if (leaves[leafkey]['type'] == 'dir'):
            item_md5 = leaves[leafkey]['md5dir']
            if item_md5 not in md5dict:
                md5dict[item_md5] = []

            entry = leaves[leafkey]
            entry["leaf_number"] = leafkey

            md5dict[item_md5].append(entry)

    for md5_key in md5dict.keys():
        file_size = []
        for entry in md5dict[md5_key]:
            file_size.append(entry["tree_size"])

        file_size = list(set(file_size))
        if (len(file_size) > 1):
            print "ERROR: accounting for size of directories " +\
                  "with with hash %s failed" % md5_key

        file_size = file_size[0]
        md5_size_dict[md5_key] = file_size

    for key, value in sorted(md5_size_dict.iteritems(),
                             key=lambda (k, v): (v, k),
                             reverse=True):
        if (len(md5dict[key]) > 1):
            print "-" * 80
            print "%s: %d" % (key, value)
            for entry in md5dict[key]:
                full_pathname = utils.reconstruct_pathname(parent_tree, leaves,
                                                     int(entry["leaf_number"]))
                print full_pathname


# TODO: command-line utility
if __name__ == '__main__':
    find_largest_common_directories("mtree_tree.shelve",
                                    "mtree_leaves.shelve")
