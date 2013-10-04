"""
Parse mtree spec files -> a file tree dictionary with checksums and file sizes
Eric Switzer Aug. 5 2011
"""
import shelve
import utils


def clean_mtree_spec(filename_in, filename_out):
    """prepare the mtree spec file for single-line parser
    equivalent to:
    cat mtree_test.spec | \
        sed 'N;s/\\\n *//g;P;D;' | \
        sed 'N;s/\\\n *//g;P;D;' | \
        sed 'N;s/\n\.\./ ../g;P;D;' > mtree_test.spec_clean
    """
    mtree_rawspecfile = open(filename_in, 'r')
    mtree_specfile = open(filename_out, 'w')

    with open(filename_in) as sequence_file:
        mtree_sequence = sequence_file.read()  # read the rest

    replacement = {"\\\n": "", " " * 16: "", "\n..": " ..", "\n ..": ""}
    for i, j in replacement.iteritems():
        mtree_sequence = mtree_sequence.replace(i, j)

    mtree_specfile.write(mtree_sequence)

    mtree_rawspecfile.close()
    mtree_specfile.close()


def parse_fileitem(fileitem):
    """parse the file information in a line of the mtree spec
    [filename] mode=0644 size=0 time=... md5digest=...
    """
    fileitem_split = fileitem.split()
    if (len(fileitem_split) < 1):
        print "parse_filename: input error"
        return None

    outdict = {}
    outdict['name'] = fileitem_split[0]
    # now grab the mode, size, time, md5digest
    for info_item in fileitem_split:
        if "=" in info_item:
            info_split = info_item.split("=")
            outdict[info_split[0]] = info_split[1]

    return outdict


def parse_line(line):
    """parse a single line in the mtree spec file
    return the entry and its type

    Traversal of the file structure is indicated with #

    Example entry:
    # ./your_path
    your_path type=dir ...
    a_file_1 ...
    a_file_2 ...
    # ./your_path ..

    push = entering a new directory, e.g. # ./your_path
    pop = leaving a directory, e.g. # ./your_path ..
    file = a file entry
    dir = entry is a directory e.g. your_path type=dir ...
    link = a file entry is a link

    An mtree entry may be blank or undetermined
    """
    line_split = line.split()
    # default: line can not be parsed
    (line_type, entry) = ('undetermined', 'undetermined')

    if (len(line_split) == 0):
        return ("blank", "blank")

    # parse a directory declaration
    if (line[0] == "#"):
        # leaving a directory environment
        if (line_split[-1] == ".."):
            line_type = "pop"
            entry = " ".join(line_split[1:-1])
        # entering a directory environment
        else:
            line_type = "push"
            entry = " ".join(line_split[1:])
    else:
        entry = parse_fileitem(line)
        line_type = "file"

        if line_split[0] == "/set":
            line_type = "set"

        if "type" in entry:
            if (entry["type"] == "dir"):
                line_type = "dir"

            if (entry["type"] == "link"):
                line_type = "link"

    return (line_type, entry)


def parse_mtree(filename):
    """parse an mtree into a dictionary describing the branches at each node
    and a separate dictionary with information about each item

    tree_leaves: dict containing directory/file information
    file_tree: represent the file tree in a flat dictionary of pointers
    """
    # tighten up the native mtree format
    filename_clean = filename + "_clean"
    clean_mtree_spec(filename, filename_clean)

    mtree_specfile = open(filename_clean, 'r')

    # a list of directories up to the current parse path
    # (this is just recordkeeping as the mtree file is parsed)
    direnvironment = []

    # every directory/file is assigned a numerical index
    index = 0

    # tree_leaves translates the index to the directory/file
    tree_leaves = {}

    # key = directory/file index, value = indicies in that dir
    file_tree = {}

    passed_header = False
    for line in mtree_specfile.xreadlines():
        (line_type, line_entry) = parse_line(line)

        # NOTE: header lines start with #, which looks like a dir. declaration
        # wait for a blank line to start parsing the tree
        if passed_header == False:
            if (line_type == "blank"):
                passed_header = True
            else:
                continue

        # push a new working directory
        if (line_type == "push"):
            # does this directory have a parent?
            if (len(direnvironment) > 0):
                parent_index = direnvironment[-1]
            else:
                parent_index = None

            direnvironment.append(index)

            # assign a number to the directory
            tree_leaves[index] = line_entry
            # give the directory a list of contents
            file_tree[index] = []
            if (parent_index != None):
                file_tree[parent_index].append(index)

            index += 1

        # pop the working directory
        if (line_type == "pop"):
            direnvironment.pop()

        # assign a file to the directory
        if (line_type == "file"):
            # the mtree spec only gives a "type" if it is a dir or link
            # add a "type" entry for files, to be explicit
            line_entry["type"] = "file"
            parent_index = direnvironment[-1]
            file_tree[parent_index].append(index)
            tree_leaves[index] = line_entry

            index += 1

        # assign directory info to the directory
        if (line_type == "dir"):
            parent_index = direnvironment[-1]
            tree_leaves[parent_index] = line_entry
            # the file_tree is established in the "push"

    mtree_specfile.close()
    return file_tree, tree_leaves


# TODO: is it faster to index by integer and convert to string for shelve keys
# or to use strings as keys throughout?
def process_mtree(filename, tree_shelvename, leaves_shelvename):
    """read an mtree spec file and convert it into a python representation,
    written out as shelve files

    add cumulative checksums (checksum of all checksums under a directory)
    add up all files under a directory for total tree size
    """
    print "parsing mtree file"
    (file_tree, tree_leaves) = parse_mtree(filename)

    print "adding cumulative checksums, md5dir in tree_leaves table"
    utils.decorate_with_aggregates(file_tree, tree_leaves, "md5digest",
                                   "md5dir", "md5")

    print "adding tree sizes, tree_size in tree_leaves table"
    utils.decorate_with_aggregates(file_tree, tree_leaves, "size", "tree_size",
                                   "total", include_dir=True)

    print "writing to shelve files"
    outtree = shelve.open(tree_shelvename, 'n')
    for nodekey in file_tree.keys():
        outtree[repr(nodekey)] = file_tree[nodekey]

    outtree.close()

    outleaves = shelve.open(leaves_shelvename, 'n')
    for leafkey in tree_leaves.keys():
        outleaves[repr(leafkey)] = tree_leaves[leafkey]

    outleaves.close()


# TODO: command-line utility
if __name__ == '__main__':
    process_mtree("mtree_2013Sept15.spec", "mtree_tree.shelve",
                                         "mtree_leaves.shelve")
    #process_mtree("mtree.toaster.spec_17Jun12", "mtree_tree_toaster.shelve",
    #                                            "mtree_leaves_toaster.shelve")
    #process_mtree("mtree_2TB_mac.spec", "mtree_2TB_tree.shelve",
    #                                  "mtree_2TB_leaves.shelve")
