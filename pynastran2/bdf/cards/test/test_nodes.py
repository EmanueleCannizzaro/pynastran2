from __future__ import print_function, unicode_literals
import unittest

from pyNastran.bdf.bdf import GRID, SPOINTs as SPOINT, BDFCard

class TestNodes(unittest.TestCase):
    def test_grid_01(self):
        nid = 1
        cp = 2
        cd = 0
        ps = ''
        seid = 0
        datai = [nid, cp, 0., 0., 0., cd, ps, seid]
        n1 = GRID.add_op2_data(datai)
        #print n1

        msg = n1.write_card(size=8)
        #print(msg)
        msg = n1.write_card(size=16)
        #print(msg)
        msg = n1.write_card(size=16, is_double=True)
        #print(msg)
        if 0:
            msg = n1.write_card(size=8)
            #print('%r' % msg)
            # small field
            self.assertEqual(msg, 'GRID           1       2      0.      0.      0.                        \n')
            msg = n1.write_card(size=16)

            # large field
            card = ('GRID*                  1               2             .-0             .-0\n'
                    '*                    .-0                                                \n')
            print('%r' % msg)
            ref = 'ERROR\n'
            if card != msg:
                scard = card.split('\n')
                smsg = msg.split('\n')
                i = 0
                print(scard)
                print(smsg)
                for sc, sm in zip(scard, smsg):
                    if sc != sm:
                        ref += 'i=%s\ncard=%r\nmsg =%r\n' % (i, sc, sm)
                    i += 1
            print(ref)
            self.assertEqual(msg, card), ref

    def test_grid_02(self):
        nid = 1
        cp = 2
        cd = 0
        ps = '1'
        seid = 4
        datai = ['GRID', nid, cp, 0., 0., 0., cd, ps, seid]
        card = BDFCard(datai)
        n1 = GRID.add_card(card)

        x = 0.1
        y = 0.2
        z = 0.3
        self.assertEqual(n1.get_field(3), 0., msg='%s' % n1.get_field(3))
        self.assertEqual(n1.get_field(4), 0., msg='%s' % n1.get_field(4))
        self.assertEqual(n1.get_field(5), 0., msg='%s' % n1.get_field(5))

        self.assertEqual(n1.get_field(6), cd, msg='%s' % n1.get_field(6))
        self.assertEqual(n1.get_field(7), ps, msg='%s' % n1.get_field(7))
        self.assertEqual(n1.get_field(8), seid, msg='%s' % n1.get_field(8))
        n1.update_field(3, x)
        n1.update_field(4, y)
        n1.update_field(5, z)
        #print('ps = %r' % n1.ps)
        self.assertEqual(n1.xyz[0], x)
        self.assertEqual(n1.xyz[1], y)
        self.assertEqual(n1.xyz[2], z)
        self.assertEqual(n1.ps, ps)
        self.assertEqual(n1.cd, cd)
        self.assertEqual(n1.seid, seid)

        self.assertEqual(n1.get_field(3), x, msg='%s' % n1.get_field(3))
        self.assertEqual(n1.get_field(4), y, msg='%s' % n1.get_field(4))
        self.assertEqual(n1.get_field(5), z, msg='%s' % n1.get_field(5))

        self.assertEqual(n1.get_field(6), cd, msg='%s' % n1.get_field(6))
        self.assertEqual(n1.get_field(7), ps, msg='%s' % n1.get_field(7))
        self.assertEqual(n1.get_field(8), seid, msg='%s' % n1.get_field(8))


    def test_spoint_01(self):
        #      12345678 2345678 2345678 2345678 2345678 2345678
        msg = 'SPOINT         1       3       5\n'
        card = BDFCard(['SPOINT', 1, 3, 5])
        s1 = SPOINT.add_card(card)
        s1.write_card()
        assert list(s1.points) == [1, 3, 5], '\n%s' % list(s1.points)
        assert s1.write_card() == msg, '\n%s---\n%s' % (s1.write_card(), msg)

        #      12345678 2345678 2345678 2345678 2345678 2345678
        msg = 'SPOINT         1    THRU       5\n'
        card = BDFCard(['SPOINT', 1, 'THRU', 5])
        s2 = SPOINT.add_card(card)
        assert list(s2.points) == [1, 2, 3, 4, 5], '\n%s' % list(s2.points)
        #assert s2.write_card() == msg, '\n%s---\n%s' % (s2.write_card(), msg)

        #       12345678 2345678 2345678 2345678 2345678 2345678
        msg = 'SPOINT         7\n'
        msg += 'SPOINT         1    THRU       5\n'
        card = BDFCard(['SPOINT', 1, 2, 3, 4, 5, 7])
        s3 = SPOINT.add_card(card)
        assert list(s3.points) == [1, 2, 3, 4, 5, 7], '\n%s' % list(s3.points)
        #assert s3.write_card() == msg, '\n%s---\n%s' % (s3.write_card(), msg)

        #       12345678 2345678 2345678 2345678 2345678 2345678
        msg = 'SPOINT         7\n'
        msg += 'SPOINT         1    THRU       5\n'
        card = BDFCard(['SPOINT', 1, 'THRU', 5, 7])
        s4 = SPOINT.add_card(card)
        assert list(s4.points) == [1, 2, 3, 4, 5, 7], '\n%s' % list(s4.points)
        #assert s4.write_card() == msg, '\n%s---\n%s' % (s4.write_card(), msg)


        #       12345678 2345678 2345678 2345678 2345678 2345678
        msg = 'SPOINT         7\n'
        msg += 'SPOINT         1    THRU       5\n'
        card = BDFCard(['SPOINT', 1, 'THRU', 5, 7])
        s5 = SPOINT.add_card(card)
        assert list(s5.points) == [1, 2, 3, 4, 5, 7], '\n%s' % list(s5.points)
        assert s5.write_card() == msg, '\n%s---\n%s' % (s5.write_card(), msg)




if __name__ == '__main__':  # pragma: no cover
    unittest.main()
