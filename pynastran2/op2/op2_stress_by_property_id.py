from six import iteritems
import numpy as np

def get_elements_by_property_id(types_to_consider):
    pid_to_eids = defaultdict(list)
    for eid, elem in iteritems(model.elements):
        pid = elem.pid # no xref
        pid_to_eids[pid].append(eid)
    return pid_to_eids

def get_stress_by_property_id(op2_geom):

    stress_by_property =
    get_elements_by_property_id()
    for pid, prop in op2_geom.properties:
