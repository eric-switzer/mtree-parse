'''common data management tasks'''
import shelve
import utils
import sys
import copy

# TODO: break this into smaller component functions
def find_largest_common_directories(tree_shelvename, leaves_shelvename,
                                    print_size_only=False):
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


    cutcount = 0
    
    reduced_md5_size_dict = copy.deepcopy(md5_size_dict)
    for md5_key in md5_size_dict:
        if (len(md5dict[md5_key]) > 1):
            md5cutlist = []
            for entry in md5dict[md5_key]:
                md5under_path = utils.hashes_under_tree(tree, leaves, 
                                                        entry["leaf_number"])
                md5cutlist.append(set(md5under_path))

            combined_cutlist = md5cutlist[0]
            for md5list in md5cutlist:
                combined_cutlist.intersection(md5list)

            combined_cutlist = list(combined_cutlist)

            for cutmd5 in combined_cutlist:
                if cutmd5 in reduced_md5_size_dict:
                    cutcount += 1
                    del reduced_md5_size_dict[cutmd5]

    print "number of trees under a duplicate tree cut: %d" % (cutcount)
    total_duplicated_size = 0
    for key, value in sorted(reduced_md5_size_dict.iteritems(),
                             key=lambda (k, v): (v, k),
                             reverse=True):
        if (len(md5dict[key]) > 1):
            total_duplicated_size += (len(md5dict[key])-1)*value

            if print_size_only:
                print value
            else:
                print "-" * 80
                print "%s: %d" % (key, value)
                for entry in md5dict[key]:
                    full_pathname = utils.reconstruct_pathname(parent_tree, 
                                                               leaves,
                                                 int(entry["leaf_number"]))
                    print full_pathname

    print "data volume in duplicated directories %d" % total_duplicated_size

# TODO: command-line utility
if __name__ == '__main__':
    find_largest_common_directories("mtree_tree.shelve",
                                    "mtree_leaves.shelve",
                                    print_size_only=False)
