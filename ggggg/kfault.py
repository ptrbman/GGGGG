## K-fold validation functions

from ggggg.fiveg import *
from ggggg.solver import *
import copy

def removeHost(name, sysdict):
    print("\t\t\tREMOVING HOST " + name)
    allocation = sysdict['Allocation']
    newHosts = list(filter(lambda x : x.name != name, sysdict['Hosts']))
    sysdict['Hosts'] = newHosts
    newLinks = list(filter(lambda x : x.begin.name != name and x.end.name != name, sysdict['Links']))
    sysdict['Links'] = newLinks
    newVNFs = list(filter(lambda x : allocation.host(x).name != name, sysdict['VNFs']))
    sysdict['VNFs'] = newVNFs


    def updateUID(ls):
        for i, e in enumerate(ls):
            e.uid = i

    ### UPDATE uis
    for ll in ["Hosts", "Links", "VNFs"]:
        updateUID(sysdict[ll])

def kfaulthosts(k, sysdict, vtaloc):
    if k != 1:
        raise Exception("Only 1-fold supported")
    results = []
    for h in sysdict['Hosts']:
        newDict = copy.deepcopy(sysdict)
        removeHost(h.name, newDict)
        result = Verify(newDict, vtaloc)
        results.append((h, result, newDict))
    return results




