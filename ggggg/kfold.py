## K-fold validation functions

from ggggg.fiveg import *
from ggggg.solver import *
import copy

def removeHost(name, sysdict):
    newHosts = list(filter(lambda x : x.name != name, sysdict['Hosts']))
    sysdict['Hosts'] = newHosts
    newLinks = list(filter(lambda x : x.begin.name != name and x.end.name != name, sysdict['Links']))
    sysdict['Links'] = newLinks

    def updateUID(ls):
        for i, e in enumerate(ls):
            e.uid = i

    ### UPDATE uis
    for ll in ["Hosts", "Links"]:
        updateUID(sysdict[ll])

def kfoldhosts(k, sysdict, vtaloc):
    if k != 1:
        raise Exception("Only 1-fold supported")
    results = []
    for h in sysdict['Hosts']:
        newDict = copy.deepcopy(sysdict)
        removeHost(h.name, newDict)
        result = Verify(newDict, vtaloc)
        results.append((h, result, newDict))
    return results




