'''
Parse mtree spec files -> a file tree dictionary with checksums and file sizes
Eric Switzer Aug. 5 2011
'''
import shelve
import utils
# TODO: document + unit tests
# TODO: add name_only flag to extract the name of the file/dir only
# TODO: add link handling to parser


# TODO: more efficient implementation using xreadlines?
def clean_mtree_spec(filename_in, filename_out):
    '''prepare the mtree spec file for single-line parser
    equivalent to:
    cat mtree_test.spec | \
        sed 'N;s/\\\n *//g;P;D;' | \
        sed 'N;s/\\\n *//g;P;D;' | \
        sed 'N;s/\n\.\./ ../g;P;D;' > mtree_test.spec_clean
    '''
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
    '''parse the file information in a line of the mtree spec'''
    fileitem_split = fileitem.split()
    if (len(fileitem_split) < 1):
        print "parse_filename: input error"
        return None

    outdict = {}
    outdict['name'] = fileitem_split[0]
    for info_item in fileitem_split:
        if "=" in info_item:
            info_split = info_item.split("=")
            outdict[info_split[0]] = info_split[1]

    return outdict


def parse_line(line):
    '''parse a single line in the mtree spec file'''
    line_split = line.split()
    (line_type, entry) = ('undetermined', 'undetermined')

    if (len(line_split) == 0):
        return ("blank", "blank")

    # diretory start and stop declaration lines begin with #
    if (line[0] == "#"):
        if (line_split[-1] == ".."):
            line_type = "pop"
            entry = " ".join(line_split[1:-1])
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


# TODO: make representation more compact (using strings to rep. md5s now)
def parse_mtree(filename):
    '''parse an mtree into a dictionary describing the branches at each node
    and a separate dictionary with information about each item
    '''
    filename_clean = filename + "_clean"
    clean_mtree_spec(filename, filename_clean)

    mtree_specfile = open(filename_clean, 'r')
    # a list of directories up to the current parse path
    direnvironment = []
    lookup = {}
    link_list = {}
    index = 0

    passed_header = False
    for line in mtree_specfile.xreadlines():
        (line_type, line_entry) = parse_line(line)

        # header lines look just like directory declarations
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
            lookup[index] = line_entry
            # give the directory a list of contents
            link_list[index] = []
            if (parent_index != None):
                link_list[parent_index].append(index)

            index += 1

        # pop the working directory
        if (line_type == "pop"):
            direnvironment.pop()

        # assign a file to the directory
        if (line_type == "file"):
            line_entry["type"] = "file"  # not in mtree spec
            parent_index = direnvironment[-1]
            link_list[parent_index].append(index)
            lookup[index] = line_entry

            index += 1

        # assign directory info to the directory
        if (line_type == "dir"):
            parent_index = direnvironment[-1]
            lookup[parent_index] = line_entry
            # the link_list is established in the "push"

    mtree_specfile.close()
    return link_list, lookup


# TODO: is it faster to index by integer and convert to string for shelve keys
# or to use strings as keys throughout?
def process_mtree(filename, tree_shelvename, leaves_shelvename):
    '''read an mtree spec file and convert it into a python representation,
    written out as shelve files
    '''
    print "parsing mtree file"
    (link_list, lookup) = parse_mtree(filename)

    print "adding cumulative checksums"
    utils.decorate_with_aggregates(link_list, lookup, "md5digest",
                                   "md5dir", "md5")

    print "adding tree sizes"
    utils.decorate_with_aggregates(link_list, lookup, "size", "tree_size",
                                   "total", include_dir=True)

    print "writing to shelve files"
    outtree = shelve.open(tree_shelvename, 'n')
    for nodekey in link_list.keys():
        outtree[repr(nodekey)] = link_list[nodekey]
    outtree.close()

    outleaves = shelve.open(leaves_shelvename, 'n')
    for leafkey in lookup.keys():
        outleaves[repr(leafkey)] = lookup[leafkey]
    outleaves.close()


# TODO: command-line utility
if __name__ == '__main__':
    #process_mtree("mtree.spec_5sept11", "mtree_tree.shelve",
    #                                  "mtree_leaves.shelve")
    process_mtree("mtree_2TB_mac.spec", "mtree_2TB_tree.shelve",
                                      "mtree_2TB_leaves.shelve")
