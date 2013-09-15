"""Utilities to support mtree_parse and tools"""
import hashlib


# TODO: inherit list? uglier?
class Filedata():
    """
    This class extends list to do various operations useful for file
    properties.
    """
    def __init__(self):
        self.mhash = hashlib.md5()
        self.property_list = []

    def append(self, item):
        self.property_list.append(item)

    def md5(self):
        """return a checksum of a list of checksums"""
        # TODO: is "".join(self.property_list) faster?
        for md5item in self.property_list:
            self.mhash.update(md5item)
        return self.mhash.hexdigest()

    def total(self):
        """take the sum of items in a list as integers"""
        return sum([int(x) for x in self.property_list])


# TODO: follow links
def decorate_with_aggregates(tree, leaves, in_field, out_field,
                             callback, level=0, include_dir=False):
    """go through each directory and aggregate information about all the files
    that they contain
    """
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


# TODO: save out entry = leaves[leafkey]; entry["leaf_number"] = leafkey
def make_hash_index(parent_tree, leaves):
    """make a dictionary which links a checksum to all its files:
        { md5 : [file1, file2, ...] }
    """
    md5dict = {}
    for leafkey in leaves.keys():
        if ((leaves[leafkey]['type'] == 'file') and
            ('md5digest' in leaves[leafkey])):
            item_md5 = leaves[leafkey]['md5digest']
            if item_md5 not in md5dict:
                md5dict[item_md5] = []

            entry = reconstruct_pathname(parent_tree, leaves, int(leafkey))
            md5dict[item_md5].append(entry)
            #print item_md5 + entry

    return md5dict


def make_parent_tree(tree):
    """convert a dictionary representing parent_ind: [branch_ind1,...] to a
    dictionary in the form branch_ind1 : parent_ind
    """
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
    """given the index of a file/directory leaf, find the nested list of its
    parents, not including itself
    """
    parent_index = int(parent_tree[nodenumber])
    path = []
    path.append(parent_index)
    if (parent_index != 0):
        path.append(reconstruct_path(parent_tree, parent_index))

    return path


# TODO: add handling if nodenumber is a file and not a directory
def dirs_under_path(tree, leaves, nodenumber):
    """Find directories under a path given the tree and names
    """
    dirlist = []
    for branch in tree[nodenumber]:
        entry = leaves[repr(branch)]
        if (entry['type'] == 'dir'):
            dirlist.append(repr(branch))
            dirlist.append(dirs_under_path(tree, leaves, repr(branch)))

    return dirlist


def flatten(list_in, ltypes=(list, tuple)):
    """see:
    http://rightfootin.blogspot.com/2006/09/more-on-python-flatten.html
    """
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


def reconstruct_pathname(parent_tree, leaves, nodenumber):
    """given the index of a directory/file leaf, reconstruct its full path
    """
    # append the path itself (on top of parent path)
    path = [nodenumber]
    path.append(reconstruct_path(parent_tree, nodenumber))
    path = flatten(path)
    path.reverse()

    named_path = []
    for path_ind in path:
        named_path.append(leaves[repr(path_ind)]["name"])

    pathname = "/".join(named_path)
    # TODO: do something with unicode
    pathname = pathname.replace(r"\040", "\\ ")
    pathname = pathname.replace(r"\043", "#")
    pathname = pathname.replace(r"\133", "\\[")
    for pattern in ["(", ")", "[", "]", r"'", "|", "&"]:
        if pattern in pathname:
            pathname = pathname.replace(pattern,"\\" + pattern)

    return pathname


def hashes_under_tree(tree, leaves, tree_index, verbose=False):
    """Find all the hashes under a directory given the tree and names
    """
    dirpath = dirs_under_path(tree, leaves, tree_index)
    dirpath = flatten(dirpath)
    hashlist = []
    if verbose:
        parent_tree = make_parent_tree(tree)
        print "-" * 80
        print dirpath
        print "from: " + reconstruct_pathname(parent_tree, leaves,
                                              int(tree_index))

    for diritem in dirpath:
        if verbose:
            print reconstruct_pathname(parent_tree, leaves, int(diritem))

        hashlist.append(leaves[diritem]["md5dir"])

    return hashlist
