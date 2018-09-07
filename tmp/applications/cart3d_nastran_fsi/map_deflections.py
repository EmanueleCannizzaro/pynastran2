from __future__ import print_function
from six import iteritems
import os
import sys
import copy
from time import time
#from cPickle import loads,dumps

from numpy import argsort
from numpy.linalg import norm

#from pyNastran.applications.cart3d_nastran_fsi.delauney.premorph import runPremorph
from pyNastran.applications.cart3d_nastran_fsi.delauney_reader import Tet4, DelauneyReader
from pyNastran.applications.cart3d_nastran_fsi.math_functions import ListPrint
#from f06Reader import f06Reader

from pyNastran.op2.op2 import OP2
from pyNastran.converters.cart3d.cart3d import Cart3D

from pyNastran.utils.log import get_logger
debug = True
log = get_logger(None, 'debug' if debug else 'info')


class DeflectionReader(object):
    def __init__(self, op2_filename='fem.op2', isubcase=1):
        log.info('---starting deflectionReader.init of %s---' % op2_filename)
        op2 = OP2()
        op2.set_results('displacements')
        op2.read_op2(op2_filename)
        self.deflections = op2.displacements[isubcase].data
        log.info('---finished deflectionReader.init of %s---' % op2_filename)

    def get_deflections(self, ID, n0, n1, n2, n3):
        defs = [
            self.get_deflection(n0),
            self.get_deflection(n1),
            self.get_deflection(n2),
            self.get_deflection(n3),
        ]
        #print "defs[%s]-[%s,%s,%s,%s] = %s" %(ID, n0, n1, n2, n3, defs)
        return defs

    def get_deflection(self, grid_id):
        if grid_id in self.deflections:
            return self.deflections[grid_id]
            #return [float(grid_id),] * 3 # test
        else:
            return [0., 0., 0.]

#------------------------------------------------------------------

class DeflectionMapper(object):
    def __init__(self, aeroNodes, tets, deflectionReader):  #structural_model
        self.aeroNodes = aeroNodes
        self.tets = tets
        self.deflectionReader = deflectionReader
        #self.structural_model = structural_model
        #self.set_aero_infile()
        #self.set_structural_outfile()
        #self.structural_outfile = structural_outfile

    #def set_aero_infile(self, infile='cart3d.i.tri'):
    #    self.aero_infile = infile

    #def set_structural_outfile(self, outfile='fem.f06'):
    #    self.structural_outfile = outfile

    def build_tetrahedralization(self):
        """runs regtet"""
        pass


    def find_closest_tet(self, m, closest_tet=None):
        """
        Finds the closest tet.  Has the potential to fail, but until then, skipping.
        Solution to failure:  brute force method.
        m = aeroNode
        tets =
        """
        tets = self.tets
        if closest_tet is None:
            closest_tet = tets[1]

        #startingTet = tets[1]
        #closest_tet = self.findClosestTet_recursion(m, startingTet, tets)
        #print "found tet = ", closest_tet.ID
        #v1 = array([1.,0.,0.])

        #tet, tet_id = self.bruteForce(m, tets)
        #return tet
        log.info("starting tet = %s" % (closest_tet))
        tet_id = closest_tet.ID
        excluded = []
        log.info("working on point = %s" % (ListPrint(m)))
        counter = 0
        counterMax = 100
        broken = False

        is_internal, local_vol = closest_tet.is_internal_node(m)
        if is_internal:
            log.info("***already Internal")
        while is_internal is False:
            log.info("excluding ID=%s" % tet_id)
            excluded.append(tet_id)
            new_tet, min_value = self.find_closer_tet(m, closest_tet, tets, excluded)
            closest_tet = copy.deepcopy(new_tet)
            tet_id = closest_tet.ID
            #print("excluded = ", len(excluded))

            counter += 1
            if counter == counterMax:
                break

            if tet_id in excluded:
                log.info("ERROR***ID=%s was already excluded...excluded=%s" % (tet_id, excluded))
                broken = True
                break
            else:
                pass
                #print("ID=%s dist=%s" % (tet_id, minValue))

            is_internal, local_vol = closest_tet.is_internal_node(m)

        if broken:
            closest_tet, tet_id = self.brute_force(m, tets, excluded)
        else:
            log.info("*findClosestTet worked!!!")

        #print("*tet[%s]=%s" % (tetID, closestTet))
        #print("nodes = ", closestTet.nodes)

        return closest_tet, closest_tet.ID

    def brute_force(self, m, tets, excluded=None):
        """
        m is the point
        tets is the list of tets
        excluded is a list of tet ID's to skip

        Basically, loop thru the tets and put the point m in each tet.
        The tet thtat is the least bad (ideally perfect) is the one that
        will be used.

        If a localVol (localVolume) is negative, then the point is outside.
        However, currently localVol is actually the zeta natural coordinate, so
        0.<zeta<1.

        If a point isnt found, the least bad point is taken (the one with the lowest
        optValue (optimization value) and a 'test' is performed to check how bad it is.
        """
        if excluded is None:
            excluded = []
        log.info("brute Forcing...")

        local_vols = []
        counter = []
        #print "m = [%g %g %g]" % (m[0], m[1], m[2])
        found_internal_node = False
        for i, tet in tets.items():
            #if tet.ID in excluded:
            #    pass
            #else:
            found_internal_node, local_vol = tet.is_internal_node(m)
            local_vols.append(local_vol)
            counter.append(i)
            #print "tet[%4s].internal=%s" % (i, foundInternalNode)
            if found_internal_node:
                found_id = tet.ID
                log.info("*found_id = %s" % (found_id))
                #print self.findCloserTet(m, tets[excluded[-1]], tets)
                #print self.findCloserTet(m, tets[found_id], tets)

                return tet, found_id
                #raise Exception('unhandled success!')
                #break
        max_i = local_vols.index(max(local_vols))

        local_i = argsort(local_vols)
        local_vols.sort()
        #for i, local_vol in zip(localI, local_vols):
        #    log.info("local_vol[%s]=%s" % (i, local_vol))
        log.info("guessing...closeID = %s" % (tet.ID))

        tet_out = tets[max_i]
        log.info('tet_out = %s' % (tet_out))
        is_internal, opt_value = tet_out.is_internal_node(m)
        log.info("isInternalNode=%s optVal=%g" % (is_internal, opt_value))
        return tet_out, tet_out.ID


    def find_closer_tet(self, m, tet0, tets, excluded=None):
        """
        Makes an assumption that there is a direct line from the starting tet
        to the final tet that can be minimized with nearly every subsequent tet.
        At worst, it will get the starting node one tet closer to the solution.

        m = starting point (mid point)
        """
        if excluded is None:
            excluded = []
        #print "findCloserTet"
        #print "working on tet = ", tet0.ID

        cent = tet0.centroid()
        dist = m-cent
        #faces = [tet0.face0, tet0.face1, tet0.face2, tet0.face3]
        dists = [9.e9] * 4
        for i, neighbor in enumerate(tet0.neighbors):
            #print "i=%s neighbor=%s centroid=%s" %(i,neighbor,tets[neighbor].centroid())
            if neighbor > 0:
                dists[i] = self.distance(m, tets[neighbor].centroid())
        #dists[0] = 9.e9
        #print "dists = ",dists

        #print dists
        min_value = min(dists)
        i = dists.index(min_value)
        neighbors = tet0.neighbors
        #print "neighbors = ",neighbors
        #print "tet0.neightbors[%s] = %s" %(i,tet0.neighbors[i])
        tet_new = tets[tet0.neighbors[i]]
        #print "tet_new = ", tet_new

        #closestTet = self.findClosestTet_recursion(m, tet_new, tets, excluded)
        return tet_new, min_value


    def distance(self, p1, p2):
        return norm(p1 - p2)

    def map_deflections(self, properTets=None):
        """
        Loops thru all the aero nodes, finds the tet it's in, interpolates
        on the deflections at the nodes and maps the deflection to the aero node
        """
        if properTets is None:
            properTets = {}
        sys.stdout.flush()
        #reader = f06Reader(self.structuralOutfile)
        #d = reader.readDeflections()
        aeroNodes = self.aeroNodes
        #tets = self.tets
        d = self.deflectionReader
        tets = self.tets

        #tets = self.buildTetrahedralization()

        #aeroNodes = [array([0.0,0.,0.])]
        aeroNodes2 = []
        tet = tets[1]
        log.info("-" * 80)
        #print("type(aeroNodes)=%s" % type(aeroNodes))

        for i, aeroNode in iteritems(aeroNodes):
            if aeroNode[1] < 0:
                log.info('skipping aeroNode=%s bc y<0.' % i)
                continue
            log.info("aeroNode[%s]  = %s" % (i, ListPrint(aeroNode)))

            #print("aeroNode  = ",aeroNode)
            #continue

            if i in properTets:
                tet = tets[properTets[i]]
            else:
                tet, ID2 = self.find_closest_tet(aeroNode, tet)

            #(isInternal, localVol) = closeTet.isInternalNode(aeroNode)
            #assert isInternal==True
            #print("isInternal?  = %s" % isInternal)

            #print("***tet = %s" % (tet))
            (n0, n1, n2, n3) = tet.nodes
            ID = tet.ID
            deflectionsTet = d.get_deflections(ID, n0, n1, n2, n3)
            aeroNode2 = tet.map_deflections(deflectionsTet, aeroNode)
            log.info("aeroNode2 = %s" % (ListPrint(aeroNode2)))
            properTets[i] = ID
            aeroNodes2.append(aeroNode2)

            #for tet in tets:  # should select in certain order based on centroids
            #    if tet.isInternalNode(aeroNode):
            #        n0,n1,n2,n3 = tet.nodes
            #
            #        deflectionsTet = [d[n0], d[n1], d[n2], d[n3]]
            #        aeroNode2 = tet.mapDeflections(deflectionsTet, aeroNode)
            #break # uncomment to run one aeroNode
            log.info("-" * 80)
            sys.stdout.flush()
        #return aeroNode2
        #for key,value in properTets.items():
        #    print("pointID=%s  -> tetID=%s" % (key, value))
        sys.stdout.flush()
        return aeroNodes2, properTets

    #def writeAeroInfile(self):
        #self.aeroModel.updateNodes(nodes)
        #self.aeroModel.write(self.aeroFile)

#------------------------------------------------------------------

def load_proper_tets(properTetFilename='properTets.in'):
    properTets = {}

    if os.path.exists(properTetFilename):
        log.info("loading tets from %r..." % properTetFilename)
        infile = open(properTetFilename, 'r')
        lines = infile.readlines()
        for line in lines[1:]:
            #print
            pointID, properTet = line.strip().split()
            properTets[int(pointID)] = int(properTet)
    else:
        log.info("couldnt find tetFile %r..." % properTetFilename)
    return properTets

def write_proper_tets(workpath, properTets):
    outfilename = os.path.join(workpath, 'properTets.in')
    if not os.path.exists(outfilename):
        log.info("writing tets...")
        msg = '#PointID    tetID\n'
        for key, value in iteritems(properTets):
            msg += "%5s  %5s\n" % (key, value)
        with open(outfilename, 'wb') as outfile:
            outfile.write(msg)

def test_Tet():
    b = [10., 0., 0.]
    a = [0., 10., 0.]
    c = [0., 0., 10.]
    d = [0., 0., 0.]
    m1 = [1., 1., 1.]
    m2 = [2., 2., 2.]
    tet = Tet4(a, b, c, d)
    #print("volume = ", tet.volume())
    log.info("isInternal = \n%s\n" % (tet.is_internal_node(m1)))
    log.info("isInternal = \n%s"   % (tet.is_internal_node(m2)))

def test_deflections():
    infilename = os.path.join('op2reader', 'solid_shell_bar.op2')
    deflections = {}
    op2 = DeflectionReader(infilename)
    #op2.printDisplacement()
    displacements = op2.convert_displacements()

    #for gridID, disp in sorted(displacements.items()):
    #    print("gridID=%s disp=%s" % (gridID, disp))

#------------------------------------------------------------------

#def makeGeometryMorphIn(basepath, bdf_model):
    #args = ['junk', bdfModel, 4, 4, 4, -10, 10, -20, 20, -30, 30]
    #premorph_path = os.path.join(basepath, 'delauney', 'm4_premorph.exe')
    #runPremorph(args, bdf_model, premorph_path)


def mapDeflectionsStructures_Aero(bdf_model='test_tet10.bdf', op2_filename='test_tet10.op2',
                                  tet_filename='geometry.morph.in',
                                  cart3d_geom_filename='bJet.a.tri', cart3d_out_filename='bJet.a.tri2',
                                  proper_tet_filename='properTets.in',
                                  workpath=''):
    t0 = time()
    proper_tets = load_proper_tets(proper_tet_filename)
    #makeGeometryMorphIn(basepath, bdfModel)


    # loading tetrahedra
    dr = DelauneyReader(tet_filename) # geometry.morph.in
    tets, nodes, elements, volume = dr.build_tets()
    sys.stdout.flush()

    #print "type(tets) = ",type(tets)
    #for i,tet in sorted(tets.items()):
        #print("tet[%4s]=%s" % (i, tet))

    # loading op2 displacements
    defreader = DeflectionReader(op2_filename) # test_tet10.op2
    sys.stdout.flush()
    #deflections = defreader.convertDisplacements()
    #deflections = {1:[1.,2.,3.]}
    #for key, d in deflections.items():
        #print("d = ", d)

    # loading aero nodes
    cart = Cart3D()  # bJet.a.tri
    cart.read_cart3d(cart3d_geom_filename)
    #(cartPoints, elements, regions, Cp) = cart.makeHalfModel(cartPoints, elements, regions, Cp)
    sys.stdout.flush()


    #cart_outfile = os.path.join(workpath, 'bJet.a.tri_test')   # test code
    #cart.writeInfile(cart_outfile, cart_points, elements, regions)
    #for point in cart_points:
    #    print("point = ", point)


    # deflect the aero nodes
    dmap = DeflectionMapper(cart.points, tets, defreader)
    t1 = time()
    log.info("setup time = %g sec" %(t1-t0))

    aero_nodes2, proper_tets = dmap.map_deflections(proper_tets)
    write_proper_tets(workpath, proper_tets)


    # write out the deflected aero nodes
    cart.nodes = aero_nodes2
    cart.write_cart3d(cart3d_out_filename) #bJet.a.tri_new
    log.info("done with deflection mapping!")

    #for aeroNode in aeroNodes2:
    #    print("aeroNode = ", aeroNode)
    t2 = time()
    log.info("total mapDeflections.py time = %g sec" % (t2-t0))

#------------------------------------------------------------------

def main():
    basepath = os.getcwd()
    configpath = os.path.join(basepath, 'inputs')
    workpath = os.path.join(basepath, 'outputs')
    bdf_model = os.path.join(configpath, 'fem3.bdf')
    assert os.path.exists(bdf_model), '%r doesnt exist' % bdf_model

    os.chdir(workpath)
    log.info("basepath = %r" % basepath)
    tet_filename = os.path.join(configpath, 'geometry.morph.in')
    op2_filename = os.path.join(configpath, 'fem3.op2')
    cart3dGeom = os.path.join(configpath, 'Cart3d_bwb.i.tri')
    cart3dOut = os.path.join(workpath, 'Cart3d_bwb.i.tri2')
    proper_tet_filename = os.path.join(configpath, 'properTets.in')  # not required to exist...

    mapDeflectionsStructures_Aero(bdf_model, op2_filename, tet_filename,
                                  cart3dGeom, cart3dOut, proper_tet_filename,
                                  workpath=workpath)

    #mapDeflectionsStructures_Aero()
    #test_Tet()
    #test_deflections()

    #model = 'test_tet10' # bdf, op2, triq, tri

    sys.exit('finished mapDeflections.py')

def map_old(aero_model, structural_model):
    iteration = [1, 2, 3]
    def_mapper = DeflectionMapper(aero_model, tets, structural_model)
    for i in iteration:
        #def_mapper.set_structural_outfile('fem.f06')
        aero_file = 'cart3d_%s.tri' % i
        #def_mapper.set_aero_infile(aero_file)
        def_mapper.build_tetrahedralization()
        #def_mapper.buildMappingMatrix()
        def_mapper.map_deflections()
        #def_mapper.writeAeroInfile()


if __name__ == '__main__':
    main()
