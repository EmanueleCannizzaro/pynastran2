from __future__ import print_function
import os
import sys
import traceback
from codecs import open as codec_open
from six.moves import urllib

import numpy as np
import pyNastran
from pyNastran.utils import _filename
from pyNastran.utils.numpy_utils import loadtxt_nice


def check_for_newer_version():
    """
    Checks to see if a newer version of pyNastran has been released.
    Only checks this for the GUI.

    Looks for:
        ## pyNastran v0.7.2 has been Released (4/25/2015)

    Specifically, it finds, 'has been released'
       then takes the the part that:
         - starts with 'v',
         - strips the 'v'
         - makes a version tuple:
           - (0,7,2)
       and compares that to the current version
    """
    is_newer = False
    version_current = pyNastran.__version__
    target_url = 'https://raw.githubusercontent.com/SteveDoyle2/pyNastran/master/README.md'
    try:
        # it's a file like object and works just like a file
        # import urllib2
        # data = urllib.request.urlopen(target_url)
        data = urllib.request.urlopen(target_url)
    except: #  urllib2.URLError
        #print(help(urllib))
        #raise
        return None, None, False
    for btye_line in data: # files are iterable
        line_lower = btye_line.lower().decode('utf-8')
        if 'has been released' in line_lower:
            sline = line_lower.split()
            version_latest = [slot for slot in sline if slot.startswith('v')][0][1:]
            break

    is_dev = False
    if 'dev' in version_current:
        is_dev = True

    try:
        major, minor, rev = version_current.split('+')[0].split('.')
    except ValueError:
        print('sline = %s' % sline)
        print('version_current = %s' % version_current)
        raise
    major = int(major)
    minor = int(minor)
    rev = int(rev)
    tuple_current_version = (major, minor, rev)

    try:
        major, minor, rev = version_latest.split('_')[0].split('.')
    except ValueError:
        print('sline = %s' % sline)
        print('version_latest = %s' % version_latest)
        raise

    major = int(major)
    minor = int(minor)
    rev = int(rev)
    tuple_latest_version = (major, minor, rev)
    #print('tuple_latest_version = %s' % str(tuple_latest_version))  # (0,7,2)
    #print('tuple_current_version = %s' % str(tuple_current_version))  # (0,8,0)

    #is_newer = True
    if (tuple_current_version < tuple_latest_version or
            (is_dev and tuple_current_version <= tuple_latest_version)):
        print('pyNastran %s is now availible; current=%s' % (version_latest, version_current))
        is_newer = True
    #print('*pyNastran %s is now availible; current=%s' % (version_latest, version_current))
    return version_latest, version_current, is_newer

def load_deflection_csv(out_filename, encoding='latin1'):
    """
    The GUI deflection CSV loading function.

    Considers:
      - extension in determining how to load a file (e.g. commas or not)
      - header line of file for information regarding data types
    """
    ext = os.path.splitext(out_filename)[1].lower()
    if ext not in ['.csv', '.dat', '.txt']:
        raise NotImplementedError('extension=%r is not supported (use .dat, .txt, or .csv)' % ext)

    with codec_open(_filename(out_filename), 'r', encoding=encoding) as file_obj:
        names, fmt_dict, dtype, delimiter = _load_format_header(file_obj, ext, force_float=False)
        nnames = len(names)

        try:
            #A = np.loadtxt(file_obj, dtype=dtype, delimiter=delimiter)
            A = loadtxt_nice(file_obj, delimiter=delimiter)
        except:
            traceback.print_exc(file=sys.stdout)
            msg = 'extension=%r nheaders=%s delimiter=%r dtype=%s' % (
                ext, len(names), delimiter, dtype)
            raise RuntimeError(msg)

        try:
            nrows, ncols = A.shape
        except ValueError:
            msg = 'A should be (nnodes, 3); A.shape=%s nnames*3=%s names=%s' % (
                str(A.shape), nnames*3, names)
            raise ValueError(msg)

        if ncols != (nnames * 3):
            msg = 'A.shape=%s ncols=%s nnames*3=%s names=%s' % (
                str(A.shape), ncols, nnames*3, names)
            raise RuntimeError(msg)
    B = {}
    for i, name in enumerate(names):
        B[name] = A[:, 3*i:3*i+3]
    return B, fmt_dict, names

def load_csv(out_filename, encoding='latin1'):
    """
    The GUI CSV loading function.

    Considers:
      - extension in determining how to load a file (e.g. commas or not)
      - header line of file for information regarding data types
    """
    ext = os.path.splitext(out_filename)[1].lower()
    if ext not in ['.csv', '.dat', '.txt']:
        raise NotImplementedError('extension=%r is not supported (use .dat, .txt, or .csv)' % ext)

    with codec_open(_filename(out_filename), 'r', encoding=encoding) as file_obj:
        names, fmt_dict, dtype, delimiter = _load_format_header(file_obj, ext, force_float=False)
        try:
            #A = loadtxt(file_obj, dtype=dtype, delimiter=delimiter)
            A = loadtxt_nice(file_obj, dtype=dtype, delimiter=delimiter)
        except:
            traceback.print_exc(file=sys.stdout)
            msg = 'extension=%r nheaders=%s delimiter=%r dtype=%s' % (
                ext, len(names), delimiter, dtype)
            raise RuntimeError(msg)
    return A, fmt_dict, names

def _load_format_header(file_obj, ext, force_float=False):
    header_line = file_obj.readline().strip()
    if not header_line.startswith('#'):
        msg = 'Expected file of the form:\n'
        if ext in ['.dat', '.txt']:
            msg += '# var1 var2\n'
            msg += '1 2\n'
            msg += '3 4\n'
            msg += '\nor:\n'
            msg += '# var1(%i) var2(%f)\n'
            msg += '1 2.1\n'
            msg += '3 4.2\n'
        elif ext == '.csv':
            msg += '# var1, var2\n'
            msg += '1, 2\n'
            msg += '3, 4\n'
            msg += '\nor:\n'
            msg += '# var1(%i), var2(%f)\n'
            msg += '1, 2.1\n'
            msg += '3, 4.2\n'
        else:
            msg = 'extension=%r is not supported (use .dat, .txt, or .csv)' % ext
            raise NotImplementedError(msg)
        raise SyntaxError(msg)

    header_line = header_line.lstrip('# \t').strip()
    if ext in ['.dat', '.txt']:
        headers = header_line.split()
    elif ext == '.csv':
        headers = header_line.split(',')
    else:
        msg = 'extension=%r is not supported (use .dat, .txt, or .csv)' % ext
        raise NotImplementedError(msg)
    headers = [header.strip() for header in headers if header.strip()]

    fmt_dict = {}
    names = []
    dtype_fmts = []
    for iheader, header in enumerate(headers):
        # TODO: works for making a \n, but screws up the sidebar
        #       and scale
        header2 = header.strip()#.replace('\\n', '\n')
        dtype_fmt = 'float'

        str_fmt = '%.3f'
        if header2.endswith(')') and '%' in header2:
            header2_temp, fmt_temp = header2[:-1].rsplit('(', 1)
            header2_temp = header2_temp.strip()
            fmt = fmt_temp.strip()
            #('S1', 'i4', 'f4')
            if '%' in fmt:
                #fmt_temp = fmt_temp.replace('%', '%%')
                if force_float and 'i' in fmt:
                    fmt % 5
                    dtype_fmt = 'float32'
                    str_fmt = '%.0f'
                elif 'i' in fmt:
                    fmt % 5
                    dtype_fmt = 'int32'
                    str_fmt = '%i'

                elif 'g' in fmt or 'e' in fmt or 'f' in fmt or 's' in fmt:
                    dtype_fmt = 'float32'
                    str_fmt = fmt
                else:
                    raise TypeError('iheader=%s header=%r fmt=%r' % (iheader, header2, fmt))
            else:
                # default to float32
                dtype_fmt = 'float32'
        else:
            dtype_fmt = 'float32'
            header2_temp = header2

        names.append(header2_temp)
        dtype_fmts.append(dtype_fmt)
        fmt_dict[header2_temp] = str_fmt

    if ext in ['.dat', '.txt']:
        delimiter = None
    elif ext == '.csv':
        delimiter = ','
    else:
        raise NotImplementedError('extension=%r is not supported (use .dat, .txt, or .csv)' % ext)

    dtype = {
        'names': tuple(names),
        'formats': tuple(dtype_fmts),
    }
    return names, fmt_dict, dtype, delimiter

def load_user_geom(fname, encoding='latin1'):
    """
    Loads a file of the form:

    # all supported cards
    #  - GRID
    #  - BAR
    #  - TRI
    #  - QUAD
    #
    # doesn't support:
    #  - solid elements
    #  - element properties
    #  - custom colors
    #  - coordinate systems
    #  - materials
    #  - loads
    #  - results

    #    id  x    y    z
    GRID, 1, 0.2, 0.3, 0.3
    GRID, 2, 1.2, 0.3, 0.3
    GRID, 3, 2.2, 0.3, 0.3
    GRID, 4, 5.2, 0.3, 0.3
    grid, 5, 5.2, 1.3, 2.3  # case insensitive

    #    ID, nodes
    BAR,  1, 1, 2

    #   eid, n1,n2,n3,n4
    TRI,  2, 1, 2, 3
    # this is a comment

    #   eid, n1,n2,n3,n4
    QUAD, 3, 1, 5, 3, 4
    QUAD, 4, 1, 2, 3, 4  # this is after a blank line
    """
    with codec_open(_filename(fname), 'r', encoding=encoding) as user_geom:
        lines = user_geom.readlines()

    grid_ids = []
    xyz = []
    bars = []
    tris = []
    quads = []
    #lines2 = []
    for line in lines:
        line2 = line.strip().split('#')[0].upper()
        if line2:
            sline = line2.split(',')
            if line2.startswith('GRID'):
                assert len(sline) == 5, sline
                grid_ids.append(sline[1])
                xyz.append(sline[2:])
            elif line2.startswith('BAR'):
                assert len(sline) == 4, sline
                bars.append(sline[1:])
            elif line2.startswith('TRI'):
                assert len(sline) == 5, sline
                tris.append(sline[1:])
            elif line2.startswith('QUAD'):
                assert len(sline) == 6, sline
                quads.append(sline[1:])
            else:
                print(sline)

    grid_ids = np.array(grid_ids, dtype='int32')
    xyz = np.array(xyz, dtype='float32')
    tris = np.array(tris, dtype='int32')
    quads = np.array(quads, dtype='int32')
    bars = np.array(bars, dtype='int32')
    return grid_ids, xyz, bars, tris, quads

import re

def natural_sort(l):
    convert = lambda text: int(text) if text.isdigit() else text.lower()
    alphanum_key = lambda key: [ convert(c) for c in re.split('([0-9]+)', key) ]
    return sorted(l, key = alphanum_key)

def num_sort():
    """
    in_values  = ['anti_main', 'main', 'Family 4', 'Family 3', 'Family 1', 'Patch 119', 'Patch 118', 'Patch 19', 'Patch 18']
    out_values = ['anti_main', 'main', 'Family 1', 'Family 3', 'Family 4', 'Patch 118', 'Patch 119', 'Patch 18', 'Patch 19']

    'Patch 19 cat 20' not handled
    """
    convert = lambda text: int(text) if text.isdigit() else text.lower()
    alphanum_key = lambda key: [ convert(c) for c in re.split('([0-9]+)', key) ]

if __name__ == '__main__':  # pragma: no cover
    check_for_newer_version()

