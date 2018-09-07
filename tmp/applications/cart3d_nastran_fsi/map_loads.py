from __future__ import print_function
from six import iteritems
from six.moves import zip
import os
import sys
import multiprocessing as mp
import cPickle
from time import time

from numpy import argsort, mean, array, cross


from pyNastran.applications.cart3d_nastran_fsi.math_functions import pierce_plane_vector, shepard_weight, Normal, ListPrint
#from pyNastran.applications.cart3d_nastran_fsi.math_functions import get_triangle_weights
from pyNastran.applications.cart3d_nastran_fsi.structural_model import StructuralModel
from pyNastran.applications.cart3d_nastran_fsi.aero_model import AeroModel
from pyNastran.applications.cart3d_nastran_fsi.kdtree import KdTree

from pyNastran.converters.cart3d.cart3d import Cart3D
from pyNastran.bdf.bdf import BDF
from pyNastran.utils.log import get_logger

debug = True
log = get_logger(None, 'debug' if debug else 'info')


def entryExit(f):
    def new_f(*args, **kwargs):
        log.info("Entering", f.__name__)
        f(*args, **kwargs)
        log.info("Exited", f.__name__)
    return new_f

class LoadMapping(object):
    def __init__(self, aeroModel, structuralModel, configpath='', workpath=''):
        self.nCloseElements = 30

        self.configpath = configpath
        self.workpath = workpath
        self.aero_model = aeroModel
        self.structural_model = structuralModel

        self.mapping_matrix = {}
        self.mapfile = 'mapfile.in'
        self.bdffile = 'fem.bdf'

        self.centroid_tree = None
        self.nodal_tree = None
        self.pInf = None
        self.qInf = None
        self.load_case = None
        self.bdf = None
        self.load_cases = None

        self.Sref = 1582876. # inches
        self.Lref = 623.  # inch
        self.xref = 268.

    #@entryExit
    def set_output(self, bdffile='fem.bdf', load_case=1):
        self.bdffile = bdffile
        self.load_case = load_case

    #@entryExit
    def set_flight_condition(self, pInf=499.3, qInf=237.885):
        self.pInf = pInf
        self.qInf = qInf  #1.4/2.*pInf*Mach**2.

    #@entryExit
    def load_mapping_matrix(self):
        with open(self.mapfile, 'r') as infile:
            self.mapping_matrix = cPickle.loads(infile)

    #@entryExit
    def save_mapping_matrix(self):
        out_string = cPickle.dumps(self.mapping_matrix)
        with open(self.mapfile, 'wb') as outfile:
            outfile.write(out_string)

    #@entryExit
    def get_pressure(self, Cp):
        """
        Caculates the pressure based on:
           Cp = (p-pInf)/qInf
        """
        p = Cp * self.qInf + self.pInf
        #p = Cp*self.qInf # TODO:  for surface with atmospheric pressure inside
        return p

    #@entryExit
    def map_loads(self):
        """
        Loops thru the unitLoad mapping_matrix and multiplies by the
        total force F on each panel to calculate the PLOAD that will be
        printed to the output file.
        Also, performs a sum of Forces & Moments to verify the aero loads.
        """
        log.info("---starting map_loads---")
        self.bdf = open(self.bdffile, 'wb')
        #self.build_mapping_matrix()
        log.info("self.load_case = %s" % self.load_case)
        self.load_cases = {
            self.load_case : {},
        }

        #self.loadCases = {self.load_case={}, }
        moment_center = array([self.xref, 0., 0.])
        sum_forces = array([0., 0., 0.])
        sum_moments = array([0., 0., 0.])
        sys.stdout.flush()
        for aero_eid, distribution in iteritems(self.mapping_matrix):
            #print("aero_eid = ", aero_eid)
            #print("***distribution = ", distribution)
            sum_load = 0.
            area = self.aero_model.Area(aero_eid)
            normal = self.aero_model.Normal(aero_eid)
            Cp = self.aero_model.Cp(aero_eid)
            #print "Cp = ", Cp
            #print "area[%s]=%s" % (aero_eid, area)

            p = self.get_pressure(Cp)
            centroid = self.aero_model.Centroid(aero_eid)
            r = moment_center - centroid
            F = area * p
            Fn = F * normal
            sum_moments += cross(r, Fn)
            sum_forces += Fn
            for sNID, percent_load in sorted(iteritems(distribution)):
                sum_load += percent_load

                Fxyz = Fn * percent_load  # negative sign is to be consistent with nastran
                self.add_force(sNID, Fxyz)

                #print("Fxyz = ",Fxyz)
                #print("type(structuralModel) = ", type(self.structuralModel))

                #comment = 'percent_load=%.2f' % percent_load
                #self.structuralModel.write_load(self.bdf, self.loadCase, sNID,
                #                                Fxyz[0], Fxyz[1], Fxyz[2], comment)

            #msg = '$ End of aEID=%s sumLoad=%s p=%s area=%s F=%s normal=%s\n' % (aEID, sumLoad, p, area, F, normal)
            #self.bdf.write(msg)

        self.write_loads()  # short version of writing loads...
        self.bdf.close()

        log.info("pInf=%g [psi]; qInf= %g [psi]" % (self.pInf, self.qInf))
        log.info("sumForcesFEM  [lb]    = %s" % ListPrint(sum_forces))
        log.info("sumMomentsFEM [lb-ft] = %s" % ListPrint(sum_moments / 12.))  # divided by 12 to have moments in lb-ft

        Cf = sum_forces /(self.Sref * self.qInf)
        log.info("Cf = %s" % ListPrint(Cf))

        Cm = sum_moments / (self.Sref * self.qInf * self.Lref)
        log.info("Cm = %s" % ListPrint(Cm * 12.)) # multiply by 12 to nondimensionalize ???  maybe 144...

        #self.bdf.write('$***********\n')
        log.info("wrote loads to %r" % self.bdffile)
        log.info("---finished map_loads---")

    #@entryExit
    def write_loads(self):
        """writes the load in BDF format"""
        log.info("---starting writeLoads---")
        self.bdf.write('$ ***writeLoads***\n')
        self.bdf.write('$ nCloseElements=%s\n' % self.nCloseElements)
        for load_case, loads in sorted(iteritems(self.load_cases)):
            log.info("  load_case = %s" % load_case)
            for (sNID, Fxyz) in sorted(iteritems(loads)):
                self.structural_model.write_load(self.bdf, load_case, sNID, *Fxyz)

        log.info("finished writeLoads---")

    def add_force(self, sNID, Fxyz):
        try:
            self.load_cases[self.load_case][sNID] += Fxyz
        except KeyError:
            self.load_cases[self.load_case][sNID] = Fxyz

    #@entryExit
    def build_centroids(self, model, eids=None):
        centroids = {}
        if eids is None:
            eids = model.ElementIDs()
        for eid in eids:
            centroid = model.Centroid(eid)
            if centroid is not None:
                centroids[eid] = centroid
        return centroids

    #@entryExit
    def build_nodal_tree(self, sNodes):
        log.info("---start build_nodal_tree---")
        raise Exception('DEPRECATED...build_nodal_tree in mapLoads.py')
        sys.stdout.flush()
        #print "type(aCentroids)=%s type(sCentroids)=%s" %(type(aCentroids), type(sCentroids))
        self.nodal_tree = KdTree('node', sNodes, nclose=self.nCloseNodes)
        log.info("---finish build_nodal_tree---")
        sys.stdout.flush()

    #@entryExit
    def build_centroid_tree(self, structural_centroids):
        """
        structural_centroids - dict of structural centroids
        id:  element id
        """
        log.info("---start build_centroid_tree---")
        sys.stdout.flush()
        #print "type(aCentroids)=%s type(structural_centroids)=%s" %(type(aCentroids), type(structural_centroids))

        msg = 'Element '
        for eid, structural_centroid in sorted(iteritems(structural_centroids)):
            msg += "%s " % eid
        log.info(msg + '\n')

        self.centroid_tree = KdTree('element', structural_centroids, nclose=self.nCloseElements)
        log.info("---finish build_centroid_tree---")
        sys.stdout.flush()

    #@entryExit
    def parseMapFile(self, map_filename='mappingMatrix.new.out'):
        """
        This is used for rerunning an analysis quickly (cuts out building the mapping matrix ~1.5 hours).
        1 {8131: 0.046604568185355716, etc...}
        """
        log.info("---starting parseMapFile---")
        mapping_matrix = {}

        log.info('loading mapFile=%r' % map_filename)
        with open(map_filename, 'r') as map_file:
            lines = map_file.readlines()

        # dont read the first line, thats a header line
        for (i, line) in enumerate(lines[1:]):
            line = line.strip()
            #print "line = %r" % line
            (aEID, dict_line) = line.split('{') # splits the dictionary from the aEID
            aEID = int(aEID)
            #assert i == int(aEID)

            # time to parse a dictionary with no leading brace
            distribution = {}
            map_sline = dict_line.strip('{}, ').split(',')
            for pair in map_sline:
                (sEID, weight) = pair.strip(' ').split(':')
                sEID = int(sEID)
                weight = float(weight)
                distribution[sEID] = weight
            mapping_matrix[aEID] = distribution
        #log.info("mappingKeys = %s" %(sorted(mapping_matrix.keys())))
        self.run_map_test(mapping_matrix)
        log.info("---finished parseMapFile---")
        return mapping_matrix

    #@entryExit
    def run_map_test(self, mapping_matrix, map_test_filename='map_test.out'):
        """
        Checks to see what elements loads were mapped to.
        Ideally, all elements would have a value of 1.0, given equal area.
        Instead, each element should have a value of area[i].
        """
        map_test = {}
        for (aero_eid, distribution) in sorted(iteritems(mapping_matrix)):
            for sEID, weight in distribution.items():
                if sEID in map_test:
                    map_test[sEID] += weight
                else:
                    map_test[sEID] = weight

        with open(map_test_filename, 'wb') as map_out:
            map_out.write('# sEID  weight\n')
            for sEID, weight in sorted(iteritems(map_test)):
                map_out.write("%s %s\n" % (sEID, weight))

    def map_loads_mp_func(self, aero_eid, aero_model):
        aero_element = aero_model.Element(aero_eid)
        (aero_area, aero_centroid, aero_normal) = aero_model.get_element_properties(aero_eid)
        #percentDone = i / nAeroElements * 100

        pSource = aero_centroid
        distribution = self.pierce_elements(aero_centroid, aero_eid, pSource, aero_normal)
        #distribution = self.poorMansMapping(aero_centroid, aero_eid, pSource, aero_normal)
        self.mapping_matrix[aero_eid] = distribution

    #@entryExit
    def build_mapping_matrix(self, debug=False):
        """
        Skips building the matrix if it already exists
        A mapping matrix translates element ID to loads on the nearby
        strucutral nodes.

        eid,distribution
        """
        if self.mapping_matrix != {}:
            return self.mapping_matrix

        log.info("---starting build_mapping_matrix---")
        #print "self.mapping_matrix = ",self.mapping_matrix
        if os.path.exists('mappingMatrix.new.out'):
            self.mapping_matrix = self.parseMapFile('mappingMatrix.new.out')
            log.info("---finished build_mapping_matrix based on mappingMatrix.new.out---")
            sys.stdout.flush()
            return self.mapping_matrix
        log.info("...couldn't find 'mappingMatrix.new.out' in %r, so going to make it..." % os.getcwd())

        # this is the else...
        log.info("creating...")
        aero_model = self.aero_model
        structural_model = self.structural_model

        #aNodes = aero_model.getNodes()
        #sNodes = structural_model.getNodes()
        #treeObj = Tree(nClose=5)
        #tree    = treeObj.buildTree(aNodes,sNodes) # fromNodes,toNodes

        aElementIDs = aero_model.ElementIDs() # list
        sElementIDs = structural_model.getElementIDsWithPIDs() # list
        sElementIDs2 = structural_model.ElementIDs() # list

        msg = "there are no internal elements in the structural model?\n   ...len(sElementIDs)=%s len(sElementIDs2)=%s" % (
            len(sElementIDs), len(sElementIDs2))
        assert sElementIDs != sElementIDs2, msg
        log.info("maxAeroID=%s maxStructuralID=%s sElements=%s" % (max(aElementIDs), max(sElementIDs), len(sElementIDs2)))

        log.info("build_centroids - structural")
        sCentroids = self.build_centroids(structural_model, sElementIDs)
        self.build_centroid_tree(sCentroids)
        #self.buildNodalTree(sNodes)

        log.info("build_centroids - aero")
        aero_centroids = self.build_centroids(aero_model)

        with open('mappingMatrix.out', 'wb') as map_file:
            map_file.write('# aEID distribution (sEID:  weight)\n')

            t0 = time()
            nAeroElements = float(len(aElementIDs))
            log.info("---start piercing---")
            if debug:
                log.info("nAeroElements = %s" % nAeroElements)
            tEst = 1.
            tLeft = 1.
            percent_done = 0.

            if 1:
                num_cpus = 4
                pool = mp.Pool(num_cpus)
                result = pool.imap(self.map_loads_mp_func,
                                   [(aEID, aero_model) for aEID in aElementIDs])

                for j, return_values in enumerate(result):
                    aEID, distribution = return_values
                    #self.mappingMatrix[aEID] = distribution
                    map_file.write('%s %s\n' % (aEID, distribution))
                pool.close()
                pool.join()
            else:
                for (i, aero_eid) in enumerate(aElementIDs):
                    if i % 1000 == 0 and debug:
                        log.debug('  piercing %sth element' % i)
                        log.debug("tEst=%g minutes; tLeft=%g minutes; %.3f%% done" % (
                            tEst, tLeft, percent_done))
                        sys.stdout.flush()

                    aElement = aero_model.Element(aero_eid)
                    (aArea, aCentroid, aNormal) = aero_model.get_element_properties(aero_eid)
                    percentDone = i / nAeroElements * 100
                    if debug:
                        log.info('aEID=%s percentDone=%.2f aElement=%s aArea=%s aCentroid=%s aNormal=%s' %(
                            aero_eid, percentDone, aElement, aArea, aCentroid, aNormal))
                    pSource = aCentroid
                    (distribution) = self.pierce_elements(aCentroid, aero_eid, pSource, aNormal)
                    #(distribution)  = self.poorMansMapping(aCentroid, aero_eid, pSource, aNormal)
                    self.mapping_matrix[aero_eid] = distribution
                    map_file.write('%s %s\n' % (aero_eid, distribution))

                    dt = (time() - t0) / 60.
                    tEst = dt * nAeroElements / (i + 1)  # dtPerElement*nElements
                    tLeft = tEst - dt
                    percent_done = dt / tEst * 100.

        log.info("---finish piercing---")
        self.run_map_test(self.mapping_matrix)
        #print "mapping_matrix = ", self.mapping_matrix
        log.info("---finished build_mapping_matrix---")
        sys.stdout.flush()
        return self.mapping_matrix

    def poor_mans_mapping(self, aCentroid, aero_eid, pSource, normal):
        """
        distributes load without piercing elements
        based on distance
        """
        (sElements, sDists) = self.centroid_tree.getCloseElementIDs(aCentroid)
        log.debug("aCentroid = %s" % aCentroid)
        log.debug("sElements = %s" % sElements)
        log.debug("sDists    = %s" % ListPrint(sDists))

        setNodes = set([])
        structural_model = self.structural_model
        for structural_eid in sElements:
            sNodes = structural_model.get_element_nodes(structural_eid)
            setNodes.union(set(sNodes))

        nIDs = list(setNodes)
        sNodes = structural_model.getNodeIDLocations(nIDs)
        weights = self.get_weights(close_point, sNodes)
        distribution = self.create_distribution(nIDs, weights)
        return distribution

    def pierce_elements(self, aCentroid, aEID, pSource, normal):
        r"""
        Pierces *1* element with a ray casted from the centroid/pSource
        in the direction of the normal vector of an aerodynamic triangle

         A  1
          \/ \
          / * \
         2---\-3
               \
                B

        *P = A+(B-A)*t
        """
        #direction = -1. # TODO: direction of normal...?
        (sElements, sDists) = self.centroid_tree.getCloseElementIDs(aCentroid)
        log.info("aCentroid = %s" % aCentroid)
        log.info("sElements = %s" % sElements)
        log.info("sDists    = %s" % ListPrint(sDists))
        #(nearbySElements, nearbyDistances) = sElements
        pierced_elements = []

        for sEID, sDist in zip(sElements, sDists):
            #print "aEID=%s sEID=%s" % (aEID, sEID)
            sArea, sNormal, sCentroid = self.structural_model.get_element_properties(sEID)
            sNodes = self.structural_model.get_element_nodes(sEID)
            nNodes = len(sNodes)

            pEnd = pSource + normal * 10.
            #pEnd2 = pSource - normal * 10.
            if nNodes == 3:  # TODO:  is this enough of a breakdown?
                sA, sB, sC = sNodes
                #pEnd = pSource+normal*10.
                tuv = pierce_plane_vector(sA, sB, sC, pSource, pEnd, pierced_elements)
                #tuv2 = pierce_plane_vector(sA, sB, sC, pSource, pEnd2, pierced_elements)
            elif nNodes == 4:
                sA, sB, sC, sD = sNodes
                tuv = pierce_plane_vector(sA, sB, sC, pSource, pEnd, pierced_elements)
                #tuv2 = pierce_plane_vector(sA, sB, sC, pSource, pEnd2, pierced_elements)
                #self.pierceTriangle(sA, sB, sC, sCentroid, sNormal, pierced_elements)
                #self.pierceTriangle(sA, sC, sD, sCentroid, sNormal, pierced_elements)
            else:
                raise RuntimeError('invalid element; nNodes=%s' % nNodes)

            t1, u1, v1 = tuv
            #t2, u2, v2 = tuv2

            is_inside = False
            #if self.is_inside(u1, v1) or self.is_inside(u2, v2):
            if self.is_inside(u1, v1):
                is_inside = True
                #pIntersect = pSource + (pEnd - pSource) * t1
                pIntersect = pEnd * t1 +pSource * (1 - t1)
                #P = A + (B - A) * t
                tuv = pierce_plane_vector(sA, sB, sC, pSource, pIntersect, pierced_elements)
                #print "t,u,v=", tuv

                pierced_elements.append([sEID, pIntersect, u1, v1, sDist])

            #t = min(t1, t2)
            #print "t1=%6.3g t2=%6.3g" % (t1, t2)
            #if is_inside:
                #print "*t[%s]=%6.3g u1=%6.3g v1=%6.3g u2=%6.3g v2=%6.3g" %(sEID,t,u1,v1,u2,v2)
            #else:
                #print " t[%s]=%6.3g u1=%6.3g v1=%6.3g u2=%6.3g v2=%6.3g" %(sEID,t,u1,v1,u2,v2)

            #if is_inside:
                #print "*t[%s]=%6.3g u1=%6.3g v1=%6.3g d=%g" %(sEID,t1,u1,v1,sDist)
            #else:
                #print " t[%s]=%6.3g u1=%6.3g v1=%6.3g d=%g" %(sEID,t1,u1,v1,sDist)

        log.info("avgDist = %g" % mean(sDists))
        (pierced_elements, nPiercings) = self.fix_piercings(sElements, pierced_elements)
        distribution = self.distribute_unit_load(aEID, pierced_elements, nPiercings)

        return distribution

    def fix_piercings(self, sElements, pierced_elements):
        if len(pierced_elements) == 0:
            pierced_elements = sElements
            #for sEID in sElements:
                #pierced_elements.append([sEID, None])  # TODO: why a None?
            npiercings = 0
        else:
            dists = []
            for element in pierced_elements:
                log.info("element = %s" % element)
                dist = element[-1]
                log.info("dist = %s\n" % dist)
                dists.append(dist)
            iSort = argsort(dists)
            #print "iSort = ", iSort

            piercedElements2 = []
            for iElement in iSort:
                piercedElements2.append(pierced_elements[iElement])
            #piercedElements = piercedElements[iSort]

            #for element in pierced_elements:
                #print "element = ",element
                #print "dist = ",dist, '\n'

            npiercings = len(pierced_elements)
        return (pierced_elements, npiercings)

    def is_inside(self, u, v):
        if (0. <= u <= 1.) and (0. <= v <= 1.):
            return True
        return False

    def create_distribution(self, nIDs, weights):
        """
        Maps alist of structural nodes, and weights for a given aero element
        Takes the weights that are applied to a node and distributes them to the
        structural nodes
        """
        distribution = {}
        for nid, weight in zip(nIDs, weights):
            distribution[nid] = weight
        return distribution

    def get_weights(self, closePoint, nodes):
        # TODO: new weights?
        #n1, n2, n3 = list(setNodes)
        #n = piercedPoint
        #w1, w2, w3 = getTriangleWeights(n, n1, n2, n3)

        weights = shepard_weight(closePoint, nodes)
        return weights

    def distribute_unit_load(self, aero_eid, pierced_elements, npiercings):
        """
        distribute unit loads to nearby nodes
        pierced_elements is a list of piercings
        piercing = [sEID,P,u,v] or [sEID]
        where
          sEID - the structural element ID
          P    - point p was pierced
          u    - u coordinate
          v    - v coordinate
        if npiercings==0, all the nearby nodes will recieve load
        """
        aero_model = self.aero_model
        structural_model = self.structural_model
        #print("pierced_elements = ", pierced_elements)
        nIDs = []
        if npiercings == 0:
            #assert len(npiercings)==1,'fix me...'
            #print("npiercings=0 distributing load to closest nodes...u=%g v=%g" %(-1,-1))
            log.debug("npiercings=0 distributing load to closest nodes...")
            for structural_eid in pierced_elements:
                nIDs += structural_model.get_element_node_ids(structural_eid)
            #print("nIDs1 = ", nIDs)
            nIDs = list(set(nIDs))
            log.debug("nIDs2 = %s" % nIDs)
            aCentroid = aero_model.Centroid(aero_eid)
            nodes = structural_model.getNodeIDLocations(nIDs)

            #print "nodes = ", nodes
            weights = self.get_weights(aCentroid, nodes)
            distribution = self.create_distribution(nIDs, weights)

            log.debug("element aEID=%s sEID=%s weights=%s" % (aero_eid, structural_eid, ListPrint(weights)))
            #print("distribution = ", distribution)
            #print("nIDs         = ", nIDs)
            #print("weights      = ", weights)
            #print("nodes = ", nodes)
            #print("nPiercings = ", nPiercings)
        else:
            log.info("mapping load to actual element...")
            nclose = 3  # number of elements to map to
            close_elements = pierced_elements[:nclose]

            setCloseNodes = set([])
            for close_element in reversed(close_elements):
                log.info("close_element = %s" % close_element)
                #sEID, pIntersect, u1, v1, sDist
                structural_eid, P, u, v, sDist = close_element  # TODO:  bug here...???

                #close_point = close_element[1]
                #close_element = structural_eid
                close_point = P

                # get list of nearby structural nodes
                setElementNodes = set(structural_model.get_element_node_ids(structural_eid))
                setCloseNodes = setCloseNodes.union(setElementNodes)

            # setup for weighted average
            nIDs = list(setCloseNodes)
            sNodes = structural_model.getNodeIDLocations(nIDs)
            weights = self.get_weights(close_point, sNodes)
            distribution = self.create_distribution(nIDs, weights)

            log.info("element aEID=%s sEID=%s weights=%s" %(aero_eid, structural_eid, ListPrint(weights)))
        log.info("-------------------------\n")
        sys.stdout.flush()
        return distribution

    def Normal(self, A, B, C):
        a = B - A
        b = C - A
        normal = Normal(a, b)
        return normal

#------------------------------------------------------------------

def run_map_loads(inputs, cart3d_geom='Components.i.triq', bdf_model='fem.bdf',
                  bdf_model_out='fem.loads.out'):
    assert os.path.exists(bdf_model), '%r doesnt exist' % bdf_model

    t0 = time()
    aero_format = inputs['aero_format'].lower()

    # the property regions to map elements to
    property_regions = [
        1, 1101, 1501, 1601, 1701, 1801, 1901, 2101, 2501, 2601, 2701, 2801,
        2901, 10103, 10201, 10203, 10301, 10401, 10501, 10601, 10701, 10801,
        10901, 20103, 20203, 20301, 20401, 20501, 20601, 20701, 20801, 20901,
        701512, 801812,
    ]
    if inputs is None:
        pInf = 2116.  # sea level
        Mach = 0.8
        inputs = {
            'aero_format' : 'Cart3d',
            'Mach' : 0.825,
            # 'pInf' : 499.3,        # psf, alt=35k (per Schaufele p. 11)
            'pInf' : pInf / 144.,  # convert to psi
            'qInf' : 1.4 / 2. * pInf * Mach**2.,
            'Sref' : 1582876.,  # inch^2
            'Lref' : 623.,  # inch
            'xref' : 268.,  # inch
            'isubcase' : 1,
        }

    isubcase = inputs['isubcase']
    pInf = inputs['pInf']
    qInf = inputs['qInf']

    if aero_format == 'cart3d':
        mesh = Cart3D()
        half_model = cart3d_geom + '_half'
        result_names = ['Cp', 'rho', 'rhoU', 'rhoV', 'rhoW', 'E']

        if not os.path.exists(half_model):
            mesh.read_cart3d(cart3d_geom, result_names=result_names)
            (nodes, elements, regions, loads) = mesh.make_half_model(axis='y')
            mesh.nodes = nodes
            mesh.elements = elements
            mesh.regions = regions
            mesh.loads = loads
            #(nodes, elements, regions, Cp) = mesh.renumber_mesh(nodes, elements, regions, Cp)
            mesh.write_cart3d(half_model)
        else:
            mesh.read_cart3d(half_model, result_names=['Cp'])
        loads = mesh.loads['Cp']
        Cp = loads['Cp']
    else:
        raise NotImplementedError('aero_format=%r' % aero_format)

    aero_model = AeroModel(inputs, mesh.nodes, mesh.elements, Cp)
    log.info("elements[1] = %s" % elements[1])
    del elements, nodes, Cp


    fem = BDF(debug=True, log=log)
    fem.read_bdf(bdf_model)
    sys.stdout.flush()

    # 1 inboard
    # 1000s upper - lower inboard
    # 2000s lower - lower inboard
    # big - fin

    structural_model = StructuralModel(fem, property_regions)

    mapper = LoadMapping(aero_model, structural_model)
    t1 = time()
    mapper.set_flight_condition(pInf, qInf)
    mapper.set_output(bdffile=bdf_model_out, load_case=isubcase)
    log.info("setup time = %g sec; %g min" % (t1-t0, (t1-t0)/60.))

    mapper.build_mapping_matrix(debug=False)
    t2 = time()
    log.info("mapping matrix time = %g sec; %g min" % (t2-t1, (t2-t1)/60.))

    mapper.map_loads()
    t3 = time()
    log.info("map loads time = %g sec" % (t3 - t2))
    log.info("total time = %g min" % ((t3 - t0) / 60.))

def main():
    basepath = os.getcwd()
    configpath = os.path.join(basepath, 'inputs')
    workpath = os.path.join(basepath, 'outputs')
    cart3dGeom = os.path.join(configpath, 'Cart3d_35000_0.825_10_0_0_0_0.i.triq')

    bdf_model = os.path.join(configpath, 'aeroModel_mod.bdf')
    assert os.path.exists(bdf_model), '%r doesnt exist' % bdf_model
    os.chdir(workpath)
    log.info("basepath = %s" % basepath)

    bdf_model_out = os.path.join(workpath, 'fem_loads_3.bdf')
    inputs = None
    run_map_loads(inputs, cart3dGeom, bdf_model, bdf_model_out)


if __name__ == '__main__':
    main()
