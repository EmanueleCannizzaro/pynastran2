from six.moves import range
import os
from numpy import array_equal, allclose
import unittest

import pyNastran
from pyNastran.converters.dev.code_aster.nastran_to_code_aster import CodeAsterConverter

pkg_path = pyNastran.__path__[0]
model_path = os.path.join(pkg_path, '..', 'models')
test_path = os.path.join(pkg_path, 'converters', 'dev', 'code_aster')
test_path = os.path.join(pkg_path, 'converters', 'dev', 'code_aster')

class TestCodeAster(unittest.TestCase):

    def test_cart3d_io_01(self):
        bdf_filename = os.path.join(model_path, 'solid_bending', 'solid_bending.bdf')

        #bdf_filename = data['BDF_FILENAME']
        fname_base = os.path.basename(os.path.splitext(bdf_filename)[0])

        ca = CodeAsterConverter()
        ca.read_bdf(bdf_filename, encoding='ascii')
        ca.write_as_code_aster(fname_base)  # comm, py


if __name__ == '__main__':  # pragma: no cover
    import time
    t0 = time.time()
    unittest.main()
    print("dt = %s" % (time.time() - t0))
