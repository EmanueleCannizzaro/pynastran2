from six.moves import StringIO
from numpy import array

#from pyNastran.bdf.field_writer_8 import print_card_8
#from pyNastran.bdf.field_writer_16 import print_card_16
#from pyNastran.bdf.bdf_interface.assign_type import (integer,
from pyNastran.bdf.dev_vectorized.cards.elements.property import Property


class PCOMPG(Property):
    type = 'PCOMPG'

    def __init__(self, model):
        self.n = 0

    def add(self, card, comment=''):
        pass

    def build(self):
        self.property_id = array([], dtype='int32')

    def write_card(self, f, size=8, property_ids=None):
        pass

    def __repr__(self):
        f = StringIO()
        f.write('<PCOMPG object> n=%s\n' % self.n)
        self.write_card(f)
        return f.getvalue()
