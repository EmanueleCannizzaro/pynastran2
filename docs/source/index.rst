Welcome to pynastran
====================
The pynastran software interfaces to Nastran's complicated input and output
files and provides a simplified interface to read/edit/write the various files.
The software is compatible currently being used on Windows, Linux, and Mac.

The **BDF reader/editor/writer** supports about 230 cards including coordinate
systems. Card objects have methods to access data such as Mass, Area, etc.
The BDF writer writes a small field formatted file, but makes full use of
the 8-character Nastran field. The OpenMDAO BDF parametrization syntax
is also supported.

The **OP2 reader** supports static/transient results, which unless you
analyzing frequency response data should be good enough. It also supports
**F06 Writing** for most of the objects. Results include: displacement,
velocity, acceleration, temperature, eigenvectors, eigenvalues, SPC forces,
MPC forces, grid point forces, load vectors, applied loads, strain energy,
as well as stress and strain.

The **F06 reader/writer** works for simple problems, but it's still
preliminary. At this point, you should just use the OP2 reader. It's faster,
more robust, and supports more results. The F06 reader is more used as
a verification tool for the OP2 reader.

The **Python OP4** reader/writer supports reading ASCII/binary sparse and dense
matrices, and writing ASCII matrices..

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`


.. toctree::
   :maxdepth: 2
   :caption: Introduction

   introduction

.. toctree::
   :maxdepth: 2
   :caption: Quick Start

   quick_start

.. toctree::
   :maxdepth: 2
   :caption: Manual

   manual

.. toctree::
   :maxdepth: 2
   :caption: Code

   api

.. toctree::
   :maxdepth: 2
   :caption: Installation

   installation
