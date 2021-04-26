## This module provides methods for finding configurations which fulfills
## deadline constraints for fiveg systems.

from ggggg.uml_to_uppaal import ToUPPAAL
from ggggg.run_uppaal import runUPPAAL
from ggggg.fiveg import *

import copy

# Returns True if sysdict with allocation and routing meets all deadlines
# PRE: sysdict should contain Executors and QueueLength
def verify(sysdict, allocation, routing, verifytaLocation):
    ## Generate UPPAAL model

    sysdict['Allocation'] = allocation
    sysdict['Routing'] = routing

    EXECUTORS = int(sysdict['Executors'])
    QUEUE = int(sysdict['QueueLength'])
    modelFileName = "tmp/verify.xml"
    ToUPPAAL(sysdict, modelFileName, EXECUTORS, QUEUE)

    ## Create query file
    queryFileName = "tmp/verify.q"
    f = open(queryFileName, "w")
    f.write("A[] not M0.MissedDeadline")
    f.close()

    ## Run UPPAAL
    outputFileName = "tmp/verify.out"
    answers = runUPPAAL(verifytaLocation, modelFileName, queryFileName, outputFileName)

    ret = answers[0][1]
    if (ret == "sat"):
        return True
    elif (ret == "unsat"):
        return False

    msg = "Unknown answer: " + ret
    raise Exception(msg)


# Generate all allocations possible for system in sysdict
def generate_allocations(sysdict):
    vnfs = sysdict['VNFs']
    hosts = sysdict['Hosts']

    options = []
    for vnf in vnfs:
        thisOptions = []
        for host in hosts:
            if (vnf.Type in host.capabilities):
                thisOptions.append(host)
        options.append(thisOptions)

    optCount = list(map(len, options))
    idx = [0]*len(vnfs)

    allAllocations = []
    totalOptions = 1
    for o in optCount:
        totalOptions *= o

    for _ in range(1, totalOptions):
        ii = copy.deepcopy(idx)
        allAllocations.append(ii)

        # Increase index
        increased = False
        i = 0
        while not increased:
            idx[i] += 1
            if (idx[i] == optCount[i]):
                idx[i] = 0
            else:
                increased = True
            i += 1
    allAllocations.append(idx)

    allocations = []
    for alloc in allAllocations:
        nextAlloc = {}
        for i in range(0, len(vnfs)):
            nextAlloc[vnfs[i]] = options[i][alloc[i]]
        allocations.append(Allocation(nextAlloc))

    return allocations


# Generate all possible routings given systme sysdict and allocation alloc
def generate_routings(sysdict, alloc):
    links = sysdict['Links']
    hosts = sysdict['Hosts']
    routing = sysdict['Routing']
    slices = sysdict['Slices']
    chains = sysdict['Chains']
    vnfs = sysdict['VNFs']
    userEquipments = sysdict['UserEquipments']

    # All "next steps" from host hId
    def allSteps(h):
        steps = []
        for l in links:
            if (l.begin == h):
                steps.append(l.end)
            if (l.end == h):
                steps.append(l.begin)
        # Remove duplicates
        return list(dict.fromkeys(steps))


    # All paths from host1 to host 2
    def allPaths(host1, host2):

        # If locations are the same, there is only one (the empty) possibility.
        # In contrast to the list of possibilities being empty.
        if (host1 == host2):
            return [[-1]]

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
            allpaths[(h1, h2)] = allPaths(h1, h2)
            allpaths[(h2, h1)] = allPaths(h2, h1)


    # routingOptions[i][j] contains all possible routes for slice i on step j
    routingOptions = []

    def getOpts(h1, h2):
        ret = allpaths[(h1, h2)]
        if not ret:
            print("No path from " + str(h1) + " to " + str(h2))
        return ret

    # optPerSlice[i][j] contains all the number of possible routes for slice i on step j
    optPerSlice = []
    for (s,c) in zip(slices, chains):
        optionSteps = []
        optCount = []
        for i in range(0, len(c.chain)-1):
            host1 = alloc.alloc[c.chain[i]]
            host2 = alloc.alloc[c.chain[i+1]]
            opts = getOpts(host1, host2)
            optionSteps.append(opts)
            optCount.append(len(opts))
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
            if l.end == h1 and l.begin == h2:
                return l


    # Transform a path to a list of links
    def listToLinks(l):
        ret = []
        for i in range(0, len(l)-1):
            ret.append(hostsToLink(l[i], l[i+1]))
        return ret

    # List of all resulting systems
    routings = []

    for opt in allOptions:
        rts = []

        # Translate for each slice to a routingtable
        for i in range(0, len(slices)):
            curRouting = []
            for j in range(0, slices[i].chainLength-1):
                route = Route(-1, listToLinks(routingOptions[i][j][opt[i][j]]))
                curRouting.append(route)
            rts.append(RoutingTable(curRouting))
        routings.append(rts)

    return routings


# API for verifying allocation
def VerifyAllocation(sysdict, allocation, verifytaLocation):
    routings = generate_routings(sysdict, allocation)
    for routing in routings:
        answer = verify(sysdict, allocation, routing, verifytaLocation)
        if (answer):
            return routing
    return None

# API For verifying system
def Verify(sysdict, verifytaLocation):
    allocations = generate_allocations(sysdict)
    i = 0
    for alloc in allocations:
        i += 1
        print(str(i) + "/" + str(len(allocations)))
        r = VerifyAllocation(sysdict, alloc, verifytaLocation)
        if r:
            return (alloc, r)
    return None

