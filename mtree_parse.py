'''
Parse mtree spec files -> a file tree dictionary with checksums and file sizes
Eric Switzer Aug. 5 2011
'''
import hashlib
import shelve
# TODO: write mtree output pre-processor
# TODO: write full path reconstruction
# TODO: document + unit tests
# TODO: split into utils, parser and tools


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

    return (line_type, entry)


# TODO: make representation more compact (using strings to rep. md5s now)
def parse_mtree(filename):
    '''parse an mtree into a dictionary describing the branches at each node
    and a separate dictionary with information about each item
    '''
    mtree_specfile = open(filename, 'r')
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


# TODO: inherit list? uglier?
class Filedata():
    '''
    This class extends list to do various operations useful for file
    properties.
    '''
    def __init__(self):
        self.mhash = hashlib.md5()
        self.property_list = []

    def append(self, item):
        self.property_list.append(item)

    def md5(self):
        '''return a checksum of a list of checksums'''
        # TODO: is "".join(self.property_list) faster?
        for md5item in self.property_list:
            self.mhash.update(md5item)
        return self.mhash.hexdigest()

    def total(self):
        '''take the sum of items in a list as integers'''
        return sum([int(x) for x in self.property_list])


# TODO: follow links
def decorate_with_aggregates(tree, leaves, in_field, out_field,
                             callback, level=0, include_dir=False):
    '''go through each directory and aggregate information about all the files
    that they contain
    '''
    agg_list = Filedata()
    for leaf_ind in tree[level]:
        leaf_info = leaves[leaf_ind]
        if (leaf_info['type'] == 'file'):
            # also include (leaf_info['size'] == '0')?
            if 'link' in leaf_info:
                print "link not treated: ", leaf_info
            else:
                try:
                    #print "**", leaf_ind, leaf_info[in_field]
                    agg_list.append(leaf_info[in_field])
                except KeyError:
                    print "file has no key " + in_field, leaf_info
        if (leaf_info['type'] == 'dir'):
            agg_item = decorate_with_aggregates(tree, leaves, in_field,
                                                out_field, callback,
                                                level=leaf_ind,
                                                include_dir=include_dir)
            agg_list.append(agg_item)
            #print "***", leaf_ind, agg_list.property_list

    if include_dir:
        agg_list.append(leaves[level][in_field])

    result = getattr(agg_list, callback)()
    leaves[level][out_field] = result
    #print "****", leaf_ind, agg_list.property_list, result
    return result


# TODO: is it faster to index by integer and convert to string for shelve keys
# or to use strings as keys throughout?
def process_mtree(filename, tree_shelvename, leaves_shelvename):
    '''read an mtree spec file and convert it into a python representation,
    written out as shelve files
    '''
    print "parsing mtree file"
    (link_list, lookup) = parse_mtree(filename)

    print "adding cumulative checksums"
    decorate_with_aggregates(link_list, lookup, "md5digest", "md5dir", "md5")

    print "adding tree sizes"
    decorate_with_aggregates(link_list, lookup, "size", "tree_size", "total",
                             include_dir=True)

    print "writing to shelve files"
    outtree = shelve.open(tree_shelvename, 'n')
    for nodekey in link_list.keys():
        outtree[repr(nodekey)] = link_list[nodekey]
    outtree.close()

    outleaves = shelve.open(leaves_shelvename, 'n')
    for leafkey in lookup.keys():
        outleaves[repr(leafkey)] = lookup[leafkey]
    outleaves.close()


def make_parent_tree(tree):
    '''convert a dictionary representing parent_ind: [branch_ind1,...] to a
    dictionary in the form branch_ind1 : parent_ind
    '''
    parent_tree = {}
    for tree_ind in tree.keys():
        branches = tree[tree_ind]
        for branch in branches:
            if branch in parent_tree:
                print "confused: branch has two parents?"
            else:
                parent_tree[branch] = tree_ind

    return parent_tree


def reconstruct_path(parent_tree, nodenumber):
    '''given the index of a file/directory leaf, find the nested list of its
    parents
    '''
    parent_index = int(parent_tree[nodenumber])
    path = []
    path.append(parent_index)
    if (parent_index != 0):
        path.append(reconstruct_path(parent_tree, parent_index))

    return path


def flatten(list_in, ltypes=(list, tuple)):
    '''see:
    http://rightfootin.blogspot.com/2006/09/more-on-python-flatten.html
    '''
    ltype = type(list_in)
    list_in = list(list_in)
    i = 0
    while i < len(list_in):
        while isinstance(list_in[i], ltypes):
            if not list_in[i]:
                list_in.pop(i)
                i -= 1
                break
            else:
                list_in[i:i + 1] = list_in[i]
        i += 1
    return ltype(list_in)


def reconstruct_pathname(parent_tree, leaves, nonumber):
    '''given the index of a directory/file leaf, reconstruct its full path'''
    path = reconstruct_path(parent_tree, nonumber)
    path = flatten(path)
    path.reverse()
    named_path = []
    for path_ind in path:
        named_path.append(leaves[repr(path_ind)]["name"])

    return "/".join(named_path)


# TODO: prune common subdirectories to largest encompassing directory
def find_largest_common_directories(tree_shelvename, leaves_shelvename):
    '''find the largest directories that share the same checksum of all data
    under them'''
    tree = shelve.open(tree_shelvename, 'r')
    leaves = shelve.open(leaves_shelvename, 'r')
    parent_tree = make_parent_tree(tree)

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
                full_pathname = reconstruct_pathname(parent_tree, leaves,
                                                     int(entry["leaf_number"]))
                print full_pathname


# TODO: command-line utility
if __name__ == '__main__':
    #process_mtree("mtree.spec_clean", "mtree_tree.shelve",
    #                                  "mtree_leaves.shelve")
    find_largest_common_directories("mtree_tree.shelve",
                                      "mtree_leaves.shelve")
