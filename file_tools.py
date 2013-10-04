"""common data management tasks"""
import shelve
import utils
import copy


def find_duplicates(tree_shelvename, leaves_shelvename):
    tree = shelve.open(tree_shelvename, 'r')
    leaves = shelve.open(leaves_shelvename, 'r')
    parent_tree = utils.make_parent_tree(tree)
    volhash = utils.make_hash_index(parent_tree, leaves)

    for key, filelist in volhash.iteritems():
        print key + "-" * 48
        for filename in filelist:
            print "%s" % filename


# TODO: output one file with duplicates, one with uniques
# TODO: output script to move uniques
def find_cross_duplicates(tree_shelvename, leaves_shelvename,
                   ctree_shelvename, cleaves_shelvename,
                   write_rm_list=None):
    """locate all of the checksums on one volume in a comparison volume
    write_rm_list optionally prints rm commands to delete anything that exists
    somewhere on the comparison volume. rm_list is only files, but to prune
    emtpy directories, issue:
    find <parent-dir> -depth -type d -empty -exec rmdir -v {} \;
    """
    tree = shelve.open(tree_shelvename, 'r')
    leaves = shelve.open(leaves_shelvename, 'r')
    parent_tree = utils.make_parent_tree(tree)
    ctree = shelve.open(ctree_shelvename, 'r')
    cleaves = shelve.open(cleaves_shelvename, 'r')
    parent_ctree = utils.make_parent_tree(ctree)

    volhash = utils.make_hash_index(parent_tree, leaves)
    cvolhash = utils.make_hash_index(parent_ctree, cleaves)
    if write_rm_list:
        rmlistfile = open(write_rm_list, 'w')

    for key, filelist in volhash.iteritems():
        if key in cvolhash:
            cfilelist = cvolhash[key]
            print key + "-" * 48

            for filename in filelist:
                print "%s" % filename

            print "has duplicate file(s) in the comparison volume: "
            for filename in cfilelist:
                print "%s" % filename

            if write_rm_list:
                for filename in filelist:
                    rmlistfile.write("rm -fv %s\n" % filename)

    if write_rm_list:
        rmlistfile.close()


# TODO: break this into smaller component functions
# TODO: make more efficient
# TODO: make exclude list
def find_largest_common_directories(tree_shelvename, leaves_shelvename,
                                    print_size_only=False,
                                    exclude_list=[]):
    """find the largest directories that share the same checksum of all data
    under them
    """
    tree = shelve.open(tree_shelvename, 'r')
    leaves = shelve.open(leaves_shelvename, 'r')
    parent_tree = utils.make_parent_tree(tree)

    md5dict = utils.make_hash_index(parent_tree, leaves,
                                    entry_type="dir")

    md5_size_dict = {}

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
            total_duplicated_size += (len(md5dict[key]) - 1) * value

            if print_size_only:
                print value
            else:
                print "-" * 80
                print "%s: %d" % (key, value)
                for entry in md5dict[key]:
                    full_pathname = utils.reconstruct_pathname(parent_tree,
                                                               leaves,
                                                 int(entry["leaf_number"]))
                    if not any(excluded in full_pathname
                               for excluded in exclude_list):
                        print full_pathname
                    #else:
                    #    print "#: " + full_pathname

    print "data volume in duplicated directories %d" % total_duplicated_size


# TODO: command-line utility
if __name__ == '__main__':
    find_duplicates("mtree_tree.shelve",
                    "mtree_leaves.shelve")

    #find_largest_common_directories("mtree_tree.shelve",
    #                                "mtree_leaves.shelve",
    #                                print_size_only=False,
    #                                exclude_list=["iPhoto", "Documents"])

    #find_cross_duplicates("mtree_tree_toaster.shelve",
    #                      "mtree_leaves_toaster.shelve",
    #                      "mtree_tree.shelve", "mtree_leaves.shelve",
    #                      write_rm_list="clean.bash")
