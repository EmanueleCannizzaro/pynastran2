"""
Defines how the GUI reads Abaqus files
"""
from __future__ import print_function
from six import iteritems
from six.moves import range

import os
import numpy as np

import vtk
from vtk import vtkLine, vtkTriangle, vtkQuad, vtkTetra
from vtk.util.numpy_support import numpy_to_vtk

from pyNastran.gui.gui_objects.gui_result import GuiResult
#from pyNastran.gui.qt_files.result import Result
from pyNastran.converters.abaqus.abaqus import Abaqus


class AbaqusIO(object):
    def __init__(self):
        pass

    def get_abaqus_wildcard_geometry_results_functions(self):
        """dynamic named method for loading abaqus input files"""
        data = ('Abaqus',
                'Abaqus (*.inp)', self.load_abaqus_geometry,
                None, None
                )
        return data

    def load_abaqus_geometry(self, abaqus_filename, dirname, name='main', plot=True):
        """loads abaqus input files into the gui"""
        skip_reading = self._remove_old_geometry(abaqus_filename)
        if skip_reading:
            return

        self.eid_map = {}
        self.nid_map = {}
        model = Abaqus(log=self.log, debug=False)
        self.model_type = 'abaqus'
        #self.model_type = model.model_type
        model.read_abaqus_inp(abaqus_filename)

        n_r2d2 = 0
        n_cpe3 = 0
        n_cpe4 = 0
        n_cpe4r = 0
        n_coh2d4 = 0
        n_c3d10h = 0

        n_cohax4 = 0
        n_cax3 = 0
        n_cax4r = 0

        nnodes = 0
        nelements = 0
        all_nodes = []
        for part_name, part in iteritems(model.parts):
            nids = part.nids - 1
            nodes = part.nodes

            nnodes += nodes.shape[0]
            if part.r2d2 is not None:
                n_r2d2 += part.r2d2.shape[0]
            if part.cpe3 is not None:
                n_cpe3 += part.cpe3.shape[0]
            if part.cpe4 is not None:
                n_cpe4 += part.cpe4.shape[0]
            if part.cpe4r is not None:
                n_cpe4r += part.cpe4r.shape[0]
            if part.coh2d4 is not None:
                n_coh2d4 += part.coh2d4.shape[0]

            if part.cohax4 is not None:
                n_cohax4 += part.cohax4.shape[0]
            if part.cax3 is not None:
                n_cax3 += part.cax3.shape[0]
            if part.cax4r is not None:
                n_cax4r += part.cax4r.shape[0]

            if part.c3d10h is not None:
                n_c3d10h += part.c3d10h.shape[0]

            all_nodes.append(nodes)
        nelements += n_r2d2 + n_cpe3 + n_cpe4 + n_cpe4r + n_coh2d4 + n_c3d10h + n_cohax4 + n_cax3 + n_cax4r
        assert nelements > 0, nelements
        #nodes = model.nodes
        #elements = model.elements


        self.nNodes = nnodes
        self.nElements = nelements

        self.grid.Allocate(self.nElements, 1000)

        points = vtk.vtkPoints()
        points.SetNumberOfPoints(self.nNodes)
        self.nid_map = {}

        assert nodes is not None
        nnodes = nodes.shape[0]

        if len(all_nodes) == 1:
            nodes = all_nodes[0]
        else:
            nodes = np.vstack(all_nodes)

        mmax = np.amax(nodes, axis=0)
        mmin = np.amin(nodes, axis=0)
        dim_max = (mmax - mmin).max()
        self.create_global_axes(dim_max)

        data_type = vtk.VTK_FLOAT
        points_array = numpy_to_vtk(
            num_array=nodes,
            deep=True,
            array_type=data_type
        )
        points.SetData(points_array)

        grid = self.grid
        nid_offset = -1
        for part_name, part in iteritems(model.parts):
            nnodesi = part.nodes.shape[0]

            n_r2d2 = 0
            n_cpe3 = 0
            n_cpe4 = 0
            n_cpe4r = 0
            n_coh2d4 = 0
            n_c3d10h = 0

            n_cohax4 = 0
            n_cax3 = 0
            n_cax4r = 0
            if part.r2d2 is not None:
                n_r2d2 += part.r2d2.shape[0]
            if part.cpe3 is not None:
                n_cpe3 += part.cpe3.shape[0]
            if part.cpe4 is not None:
                n_cpe4 += part.cpe4.shape[0]
            if part.cpe4r is not None:
                n_cpe4r += part.cpe4r.shape[0]

            if part.coh2d4 is not None:
                n_coh2d4 += part.coh2d4.shape[0]
            if part.cohax4 is not None:
                n_cohax4 += part.cohax4.shape[0]
            if part.cax3 is not None:
                n_cax3 += part.cax3.shape[0]
            if part.cax4r is not None:
                n_cax4r += part.cax4r.shape[0]

            # solids
            if part.c3d10h is not None:
                n_c3d10h += part.c3d10h.shape[0]

            if n_r2d2:
                eids = part.r2d2[:, 0]
                node_ids = part.r2d2[:, 1:] + nid_offset
                for eid, node_ids in zip(eids, node_ids):
                    elem = vtkLine()
                    elem.GetPointIds().SetId(0, node_ids[0])
                    elem.GetPointIds().SetId(1, node_ids[1])
                    grid.InsertNextCell(elem.GetCellType(), elem.GetPointIds())

            if n_cpe3:
                eids = part.cpe3[:, 0]
                node_ids = part.cpe3[:, 1:] + nid_offset
                for eid, node_ids in zip(eids, node_ids):
                    elem = vtkTriangle()
                    elem.GetPointIds().SetId(0, node_ids[0])
                    elem.GetPointIds().SetId(1, node_ids[1])
                    elem.GetPointIds().SetId(2, node_ids[2])
                    grid.InsertNextCell(5, elem.GetPointIds())

            if n_cpe4:
                eids = part.cpe4[:, 0]
                node_ids = part.cpe4[:, 1:] + nid_offset
                for eid, node_ids in zip(eids, node_ids):
                    elem = vtkQuad()
                    elem.GetPointIds().SetId(0, node_ids[0])
                    elem.GetPointIds().SetId(1, node_ids[1])
                    elem.GetPointIds().SetId(2, node_ids[2])
                    elem.GetPointIds().SetId(3, node_ids[3])
                    grid.InsertNextCell(elem.GetCellType(), elem.GetPointIds())

            if n_cpe4r:
                eids = part.cpe4r[:, 0]
                node_ids = part.cpe4r[:, 1:] + nid_offset
                for eid, node_ids in zip(eids, node_ids):
                    elem = vtkQuad()
                    elem.GetPointIds().SetId(0, node_ids[0])
                    elem.GetPointIds().SetId(1, node_ids[1])
                    elem.GetPointIds().SetId(2, node_ids[2])
                    elem.GetPointIds().SetId(3, node_ids[3])
                    grid.InsertNextCell(elem.GetCellType(), elem.GetPointIds())

            if n_coh2d4:
                eids = part.coh2d4[:, 0]
                node_ids = part.coh2d4[:, 1:] + nid_offset
                for eid, node_ids in zip(eids, node_ids):
                    elem = vtkQuad()
                    elem.GetPointIds().SetId(0, node_ids[0])
                    elem.GetPointIds().SetId(1, node_ids[1])
                    elem.GetPointIds().SetId(2, node_ids[2])
                    elem.GetPointIds().SetId(3, node_ids[3])
                    grid.InsertNextCell(elem.GetCellType(), elem.GetPointIds())

            if n_cohax4:
                eids = part.cohax4[:, 0]
                node_ids = part.cohax4[:, 1:] + nid_offset
                for eid, node_ids in zip(eids, node_ids):
                    elem = vtkQuad()
                    elem.GetPointIds().SetId(0, node_ids[0])
                    elem.GetPointIds().SetId(1, node_ids[1])
                    elem.GetPointIds().SetId(2, node_ids[2])
                    elem.GetPointIds().SetId(3, node_ids[3])
                    grid.InsertNextCell(elem.GetCellType(), elem.GetPointIds())

            if n_cax3:
                eids = part.cax3[:, 0]
                node_ids = part.cax3[:, 1:] + nid_offset
                for eid, node_ids in zip(eids, node_ids):
                    elem = vtkTriangle()
                    elem.GetPointIds().SetId(0, node_ids[0])
                    elem.GetPointIds().SetId(1, node_ids[1])
                    elem.GetPointIds().SetId(2, node_ids[2])
                    grid.InsertNextCell(5, elem.GetPointIds())

            if n_cax4r:
                eids = part.cax4r[:, 0]
                node_ids = part.cax4r[:, 1:] + nid_offset
                for eid, node_ids in zip(eids, node_ids):
                    elem = vtkQuad()
                    elem.GetPointIds().SetId(0, node_ids[0])
                    elem.GetPointIds().SetId(1, node_ids[1])
                    elem.GetPointIds().SetId(2, node_ids[2])
                    elem.GetPointIds().SetId(3, node_ids[3])
                    grid.InsertNextCell(elem.GetCellType(), elem.GetPointIds())

            # solids
            if n_c3d10h:
                eids = part.c3d10h[:, 0]
                node_ids = part.c3d10h[:, 1:] + nid_offset
                for eid, node_ids in zip(eids, node_ids):
                #for eid, node_ids in part.c3d10h:
                    elem = vtkTetra()
                    elem.GetPointIds().SetId(0, node_ids[0])
                    elem.GetPointIds().SetId(1, node_ids[1])
                    elem.GetPointIds().SetId(2, node_ids[2])
                    elem.GetPointIds().SetId(3, node_ids[3])
                    grid.InsertNextCell(elem.GetCellType(), elem.GetPointIds())
            nid_offset += nnodesi

        grid.SetPoints(points)
        grid.Modified()
        if hasattr(grid, 'Update'):
            grid.Update()

        # loadCart3dResults - regions/loads
        self.scalarBar.VisibilityOn()
        self.scalarBar.Modified()

        note = ''
        self.iSubcaseNameMap = {1: ['Abaqus%s' % note, '']}
        #form = []
        cases = {}
        ID = 1
        form, cases, icase = self._fill_abaqus_case(cases, ID, nodes, nelements, model)
        #self._fill_cart3d_results(cases, form, icase, ID, model)
        self._finish_results_io2(form, cases)

    def clear_abaqus(self):
        """does nothing"""
        pass

    def load_abaqus_results(self, cart3d_filename, dirname):
        """does nothing"""
        raise NotImplementedError()

    def _fill_abaqus_case(self, cases, ID, nodes, nelements, model):
        """creates the result objects for abaqus"""
        #return [], {}, 0
        #nelements = elements.shape[0]
        nnodes = nodes.shape[0]

        element_ids = np.arange(1, nelements + 1)
        node_ids = np.arange(1, nnodes + 1)
        #cnormals = model.get_normals(shift_nodes=False)
        #cnnodes = cnormals.shape[0]
        #assert cnnodes == nelements, len(cnnodes)

        #print('nnodes =', nnodes)
        #print('nelements =', nelements)
        #print('regions.shape =', regions.shape)
        subcase_id = 0
        labels = ['NodeID', 'ElementID']
        #cart3d_geo = Cart3dGeometry(subcase_id, labels,
                                    #nids, eids, regions, cnormals,
                                    #uname='Cart3dGeometry')

        nid_res = GuiResult(ID, header='NodeID', title='NodeID',
                            location='node', scalar=node_ids)
        eid_res = GuiResult(ID, header='ElementID', title='ElementID',
                            location='centroid', scalar=element_ids)

        cases = {
            0 : (nid_res, (0, 'NodeID')),
            1 : (eid_res, (0, 'ElementID')),
        }
        geometry_form = [
            ('NodeID', 0, []),
            ('ElementID', 1, []),
        ]
        form = [
            ('Geometry', None, geometry_form),
        ]
        icase = 2
        return form, cases, icase
