import re
import copy
from ggggg.fiveg import *

# Generate one model for each possible routing
def AllRoutings(sysdict, executorCount, queueLength, verbose=False):
    links = sysdict['Links']
    hosts = sysdict['Hosts']
    routing = sysdict['Routing']
    alloc = sysdict['Allocation']
    slices = sysdict['Slices']
    chains = sysdict['Chains']
    vnfs = sysdict['VNFs']
    userEquipments = sysdict['UserEquipments']

    # All "next steps" from host hId
    def allSteps(hId):
        steps = []
        for l in links:
            if (l.begin == hId):
                steps.append(l.end)
        return steps


    # All paths from host1 to host 2
    def allPaths(host1, host2):

        # If locations are the same, there is only one (the empty) possibility.
        # In contrast to the list of possibilities being empty.
        if (host1 == host2):
            return [[]]

        todo = []
        for s in allSteps(host1):
            todo.append([host1, s])

        paths = []
        while (todo):
            next = todo.pop()
            last = next[-1]
            if (last == host2):
                paths.append(next)
            else:
                for s in allSteps(last):
                    if s not in next:
                        newTodo = next.copy()
                        newTodo.append(s)
                        todo.append(newTodo)
        return paths



    # We create a dictionary containing all the paths
    allpaths = {}
    for h1 in hosts:
        for h2 in hosts:
            allpaths[(h1.i, h2.i)] = allPaths(h1.i, h2.i)

    # routingOptions[i][j] contains all possible routes for slice i on step j
    routingOptions = []

    # optPerSlice[i][j] contains all the number of possible routes for slice i on step j
    optPerSlice = []
    for (s,c) in zip(slices, chains):
        optionSteps = []
        optCount = []
        for i in range(0, len(c.chain)-1):
            optionSteps.append(allpaths[(alloc.alloc[c.chain[i].uid], alloc.alloc[c.chain[i+1].uid])])
            optCount.append(len(allpaths[(alloc.alloc[c.chain[i].uid], alloc.alloc[c.chain[i+1].uid])]))
        routingOptions.append(optionSteps)
        optPerSlice.append(optCount)

    # Compute total number of routing options and create index
    totalOptions = 1

    # Index looks like [[0,0], [0,0,0]] -> [[1,0], [0,0,0]] -> [[0,1], [0,0,0]] -> [[1,1], [0,0,0]] -> [[0,0], [1,0,0]]
    idx = []
    for sopt in optPerSlice:
        tmpidx = []
        for o in sopt:
            totalOptions *= o
            tmpidx.append(0)
        idx.append(tmpidx)

    # The list of all possible options (expressed as indices)
    allOptions = []

    for _ in range(1, totalOptions):
        ii = copy.deepcopy(idx)
        allOptions.append(ii)

        # Increase index
        increased = False
        i = 0
        while not increased:
            j = 0
            while not increased and j < len(optPerSlice[i]):
                idx[i][j] += 1
                if (idx[i][j] == optPerSlice[i][j]):
                    idx[i][j] = 0
                    j += 1
                else:
                    increased = True
            i += 1

    # We add final index possibility as well
    allOptions.append(idx)

    # Since options are expressed as sequential hosts, we need to go from pair of hosts to the link between them
    def hostsToLink(h1, h2):
        for l in links:
            if l.begin == h1 and l.end == h2:
                return l

    # Transform a path to a list of links
    def listToLinks(l):
        ret = []
        for i in range(0, len(l)-1):
            ret.append(hostsToLink(l[i], l[i+1]))
        return ret

    # List of all resulting systems
    systems = []

    for opt in allOptions:
        rts = []

        # Translate for each slice to a routingtable
        for i in range(0, len(slices)):
            curRouting = []
            for j in range(0, slices[i].chainLength-1):
                route = Route(-1, listToLinks(routingOptions[i][j][opt[i][j]]))
                curRouting.append(route)
            rts.append(RoutingTable(curRouting))

        # Simple error checking, we probably need to handle this more gracefully
        error = checkSystem(hosts, vnfs, links, slices, chains, alloc, rts, queueLength, executorCount)

        if not (error == ""):
            print("ERRORS")
            return (error, None)
        else:
            outstring = generateSystem(hosts, vnfs, links, slices, chains, alloc, rts, userEquipments, queueLength, executorCount)
            systems.append(outstring)

    return systems
