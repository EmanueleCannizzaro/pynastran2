from pyNastran.converters.cart3d.cart3d import Cart3D, read_cart3d
from pyNastran.converters.tecplot.tecplot import Tecplot

def cart3d_to_tecplot(cart3d_filename, tecplot_filename, log=None, debug=False):
    """
    Converts Cart3d to Tecplot
    """
    if isinstance(cart3d_filename, Cart3D):
        model = cart3d_filename
    else:
        model = read_cart3d(cart3d_filename, log=log, debug=debug)

    tecplot = Tecplot()
    tecplot.xyz = model.points
    tecplot.tri_elements = model.elements + 1
    tecplot.write_tecplot(tecplot_filename, adjust_nids=False)
    return tecplot
