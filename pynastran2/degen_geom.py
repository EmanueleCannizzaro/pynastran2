from __future__ import print_function
from copy import deepcopy
from collections import defaultdict
from six import iteritems

import numpy as np
from pyNastran.bdf.field_writer_8 import print_card_8
from pyNastran.converters.panair.panair_grid import PanairGrid, PanairPatch


class Geom(object):
    def __init__(self, name, lifting_surface_xyz,
                 lifting_surface_nx, lifting_surface_ny):  # pragma: no cover
        self.name = name
        self.xyz = lifting_surface_xyz
        self.nx = lifting_surface_nx
        self.ny = lifting_surface_ny

    def write_bdf_file_obj(self, bdf_file, nid0=1, eid=1, pid=1):  # pragma: no cover
        nx = self.nx
        ny = self.ny
        nxy = nx * ny
        cp = None

        for ni in range(nxy):
            x, y, z = self.xyz[ni, :]
            card = ['GRID', nid0 + ni, cp, x, y, z]
            bdf_file.write(print_card_8(card))
        #print('ni', ni, self.xyz.shape)
        eidi = 0
        for i in range(nx - 1):
            for j in range(ny - 1):
                g1 = nid0 + i*ny + j
                g2 = nid0 + i*ny + j + 1
                g3 = nid0 + (i+1) * ny + j + 1
                g4 = nid0 + (i+1) * ny + j
                card = ['CQUAD4', eid + eidi, pid, g1, g2, g3, g4]
                bdf_file.write(print_card_8(card))
                eidi += 1
        nid0 += ni + 1
        eid += eidi + 1
        return nid0, eid, pid

    @property
    def elements(self):  # pragma: no cover
        nid0 = 1
        eidi = 0
        k = 0

        nx = self.nx
        ny = self.ny
        nxy = nx * ny
        elements = np.zeros((nxy, 4), dtype='int32')
        for i in range(nx - 1):
            for j in range(ny - 1):
                g1 = nid0 + i*ny + j
                g2 = nid0 + i*ny + j + 1
                g3 = nid0 + (i+1) * ny + j + 1
                g4 = nid0 + (i+1) * ny + j
                card = [g1, g2, g3, g4]
                elements[k, :] = card
                k += 1
        return elements

    def __repr__(self):
        msg = ('Geom(name=%s, lifting_surface_xyz, '
               'lifting_surface_nx, lifting_surface_ny)' % (self.name))
        return msg


class DegenGeom(object):
    def __init__(self, log=None, debug=False):  # pragma: no cover
        self.log = log
        self.debug = debug
        self.components = defaultdict(list)

    def write_bdf(self, bdf_filename):  # pragma: no cover
        bdf_file = open(bdf_filename, 'wb')
        bdf_file.write('$pyNastran: VERSION=NX\n')
        bdf_file.write('CEND\n')
        bdf_file.write('BEGIN BULK\n')

        nid = 1
        eid = 1
        pid = 1

        mid = 1
        t = 0.1
        E = 3.0e7
        G = None
        nu = 0.3
        card = ['MAT1', mid, E, G, nu]
        bdf_file.write(print_card_8(card))
        for name, comps in sorted(iteritems(self.components)):
            bdf_file.write('$ name = %r\n' % name)
            for comp in comps:
                card = ['PSHELL', pid, mid, t]
                bdf_file.write(print_card_8(card))
                nid, eid, pid = comp.write_bdf_file_obj(bdf_file, nid, eid, pid)
                pid += 1

    def write_panair(self, panair_filename, panair_case_filename):  # pragma: no cover
        pan = PanairGrid()
        pan.mach = 0.5
        pan.isEnd = True
        pan.ncases = 2
        pan.alphas = [0., 5.]


        i = 0
        pan.nNetworks = 1
        kt = 1
        cpNorm = 1
        for name, comps in sorted(iteritems(self.components)):
            #panair_file.write('$ name = %r\n' % name)
            for comp in comps:
                namei = name + str(i)
                x = deepcopy(comp.lifting_surface_xyz[:, 0])
                y = deepcopy(comp.lifting_surface_xyz[:, 1])
                z = deepcopy(comp.lifting_surface_xyz[:, 2])
                x = x.reshape((comp.lifting_surface_nx, comp.lifting_surface_ny))
                y = y.reshape((comp.lifting_surface_nx, comp.lifting_surface_ny))
                z = z.reshape((comp.lifting_surface_nx, comp.lifting_surface_ny))
                patch = PanairPatch(pan.nNetworks, namei, kt, cpNorm, x, y, z, self.log)
                pan.patches[i] = patch
                pan.nNetworks += 1
                i += 1

                if 'wing' in name.lower():  # make a wing cap
                    namei = 'cap%i' % i
                    #assert comp.lifting_surface_nx == 6, comp.lifting_surface_nx
                    assert comp.lifting_surface_ny == 33, comp.lifting_surface_ny
                    #print(x.shape)
                    xend = deepcopy(x[-1, :])
                    print(xend)
                    yend = deepcopy(y[-1, :])
                    zend = deepcopy(z[-1, :])
                    imid = comp.lifting_surface_ny // 2
                    x = np.zeros((imid+1, 2), dtype='float32')
                    y = np.zeros((imid+1, 2), dtype='float32')
                    z = np.zeros((imid+1, 2), dtype='float32')
                    print(imid, xend[imid], xend.min())
                    xflip = list(xend[0:imid+1])
                    yflip = list(yend[0:imid+1])
                    zflip = list(zend[0:imid+1])
                    x[:, 0] = xflip[::-1]
                    y[:, 0] = yflip[::-1]
                    z[:, 0] = zflip[::-1]
                    x[:, 1] = xend[imid:]
                    y[:, 1] = yend[imid:]
                    z[:, 1] = zend[imid:]
                    print(x)

                    #x = xend[0:imid:-1].extend(x[imid:])
                    #y = yend[0:imid:-1].extend(y[imid:])
                    #z = zend[0:imid:-1].extend(z[imid:])
                    #print(x)
                    x = x.reshape((2, imid+1))
                    y = y.reshape((2, imid+1))
                    z = z.reshape((2, imid+1))

                    #print(xend)
                    patch = PanairPatch(pan.nNetworks, namei, kt, cpNorm,
                                        x.T, y.T, z.T, self.log)
                    pan.patches[i] = patch
                    pan.nNetworks += 1
                    i += 1
                #i += 1
        pan.write_panair(panair_filename)
        #self.nNetworks = i

    def read_degen_geom(self, degen_geom_csv):  # pragma: no cover
        f = open(degen_geom_csv)
        for i in range(4):
            line = f.readline()
        ncomponents = int(line)
        f.readline()

        for i in range(ncomponents):
            line = f.readline().strip().split(',')
            lifting_surface, name = line
            if lifting_surface == 'LIFTING_SURFACE':
                #degenGeom, Type, nxsections, npoints/xsection
                # SURFACE_NODE,6,33
                # nnodes -> 6*33=198
                # nelements -> 160
                f.readline()

                line = f.readline.strip()
                surface_node, lifting_surface_nx, lifting_surface_ny = line.split(',')
                assert surface_node == 'SURFACE_NODE', surface_node
                lifting_surface_nx = int(lifting_surface_nx)
                lifting_surface_ny = int(lifting_surface_ny)
                npoints = lifting_surface_nx * lifting_surface_ny
                nelements = (lifting_surface_nx - 1) * (lifting_surface_ny - 1)
                print('npoints = %r' % npoints)
                lifting_surface_xyz = np.zeros((npoints, 3), dtype='float64')
                normals = np.zeros((nelements, 3), dtype='float64')
                area = np.zeros(nelements, dtype='float64')

                # x, y, z, u, v
                f.readline()
                for i in range(npoints):
                    line = f.readline()
                    x, y, z, u, v = line.split(',')
                    lifting_surface_xyz[i, :] = [x, y, z]

                # SURFACE_FACE,5,32
                surface_node, nx, ny = f.readline().strip().split(',')
                line = f.readline() # nx,ny,nz,area
                print(line)
                for i in range(nelements):
                    line = f.readline()
                    nx, ny, nz, areai = line.split(',')
                    normals[i, :] = [nx, ny, nz]
                    area[i] = areai

                # TODO: the plate is very unclear...it's 6 lines with 3 normals on each line
                #       but 6*17?
                # DegenGeom Type,nXsecs,nPnts/Xsec
                # PLATE,6,17
                # nx,ny,nz
                f.readline()
                plate, nx, ny = f.readline().strip().split(',')
                nx = int(nx)
                ny = int(ny)
                nxy = nx * ny
                f.readline()
                for i in range(nx):
                    f.readline()

                # x,y,z,zCamber,t,nCamberx,nCambery,nCamberz,u,wTop,wBot
                line = f.readline()
                for i in range(nxy):
                    f.readline()

                # DegenGeom Type, nXsecs
                # STICK_NODE, 6
                #(lex, ley, lez, tex, tey, tez, cgShellx, cgShelly, cgShellz,
                 #cgSolidx, cgSolidy, cgSolidz, toc, tLoc, chord,
                 #Ishell11, Ishell22, Ishell12, Isolid11, Isolid22, Isolid12,
                 #sectArea, sectNormalx, sectNormaly, sectNormalz,
                 #perimTop, perimBot, u,
                 #t00, t01, t02, t03, t10, t11, t12, t13,
                 #t20, t21, t22, t23, t30, t31, t32, t33,
                 #it00, it01, it02, it03, it10, it11, it12, it13,
                 #it20, it21, it22, it23, it30, it31, it32, it33)
                f.readline()
                stick_node, nx = f.readline().split(',')
                assert stick_node == 'STICK_NODE', stick_node
                nx = int(nx)
                f.readline()
                for i in range(nx):
                    f.readline()

                # DegenGeom Type, nXsecs
                # STICK_FACE, 5
                # sweeple,sweepte,areaTop,areaBot
                f.readline()
                stick_face, nx = f.readline().split(',')
                assert stick_face == 'STICK_FACE', stick_face
                nx = int(nx)
                f.readline()
                for i in range(nx):
                    f.readline()

                # DegenGeom Type
                # POINT
                #(vol, volWet, area, areaWet,
                 #Ishellxx, Ishellyy, Ishellzz, Ishellxy, Ishellxz, Ishellyz,
                 #Isolidxx, Isolidyy, Isolidzz, Isolidxy, Isolidxz, Isolidyz,
                 #cgShellx, cgShelly, cgShellz, cgSolidx, cgSolidy, cgSolidz)
                f.readline()
                point = f.readline().strip()
                assert point == 'POINT', point
                f.readline()
                cg_line = f.readline()
                f.readline()
            else:
                raise RuntimeError(line)
            component = Geom(name, lifting_surface_xyz,
                             lifting_surface_nx, lifting_surface_ny)
            self.components[name].append(component)


def main():  # pragma: no cover
    degen_geom_csv = 'model_DegenGeom.csv'
    d = DegenGeom()
    d.read_degen_geom(degen_geom_csv)
    d.write_bdf('model.bdf')

    panair_filename = 'panair.inp'
    panair_case_filename = 'model_DegenGeom.vspaero'
    d.write_panair(panair_filename, panair_case_filename)


if __name__ == '__main__':  # pragma: no cover
    main()
