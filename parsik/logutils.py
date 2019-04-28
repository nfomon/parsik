"""Some generic logging helper utilities."""

def indent(depth):
    return "  " * depth

def squish(s, n):
    """Cut out the middle of a string s so that it fits within length n."""

    if len(s) > n:
        if n > 30:
            s = "{} ... {}".format(s[0:int(n/2)-2], s[-int(n/2)+2:])
        else:
            s = "{}…{}".format(s[0:int(n/2)], s[-int(n/2)+1:])
    return s

def stringify(x, sep=1):
    """Format a structure of lists/tuples/strings into a nice string."""

    if isinstance(x, list) or isinstance(x, tuple):
        delim = ',' + (' ' * sep)
        return '[' + delim.join(stringify(y) for y in x) + ']'
    return str(x)

