## This module provides methods for finding configurations which fulfills
## deadline constraints for fiveg systems.

from ggggg.uml_to_uppaal import ToUPPAAL
from ggggg.run_uppaal import runUPPAAL
from ggggg.fiveg import *
from ggggg.smt import verify_smt

import copy

OUTPUT_DEBUG = True

checks = 0

## Solvers
SOLVER_UPPAAL = 1
SOLVER_Z3 = 2
SOLVER_BOTH = 3

def solveUPPAAL(sysdict, binLocation):
    global checks

    ## Generate UPPAAL model
    EXECUTORS = int(sysdict['Executors'])
    QUEUE = int(sysdict['QueueLength'])
    modelFileName = "tmp/verify.xml"
    if OUTPUT_DEBUG:
        modelFileName = "debug/verify_" + str(checks) + ".xml"
    ToUPPAAL(sysdict, modelFileName, EXECUTORS, QUEUE)

    ## Create query file
    queryFileName = "tmp/verify.q"
    if OUTPUT_DEBUG:
        queryFileName = "debug/verify_" + str(checks) + ".q"
    f = open(queryFileName, "w")
    f.write("A[] not M0.MissedDeadline")
    f.close()

    ## Run UPPAAL
    outputFileName = "tmp/verify.out"
    answers = runUPPAAL(binLocation, modelFileName, queryFileName, outputFileName)
    ret = answers[0][1]
    if (ret == "sat"):
        return True
    elif (ret == "unsat"):
        return False
    else:
        msg = "Unknown answer: " + ret
        raise Exception(msg)


# Returns True if sysdict with allocation and routing meets all deadlines
# PRE: sysdict should contain Executors and QueueLength
def verify(sysdict, mappings, routing, solver, binLocation):
    global checks
    checks = checks + 1

    sysdict['Mappings'] = mappings
    sysdict['Routing'] = routing

    if solver == SOLVER_UPPAAL:
        return solveUPPAAL(sysdict, binLocation)
    elif solver == SOLVER_Z3:
        return verify_smt(sysdict, mappings, routing, binLocation)
    elif solver == SOLVER_BOTH:
        uppaalanswer = solveUPPAAL(sysdict, binLocation)
        smtanswer = verify_smt(sysdict, mappings, routing, binLocation)

        if smtanswer == uppaalanswer:
            msg = "Same answer (smt/uppaal): " + str(smtanswer) + "/" + str(uppaalanswer)
            print("\t", msg)
            return smtanswer
        else:
            msg = "Different answer (smt/uppaal): " + str(smtanswer) + "/" + str(uppaalanswer)
            raise Exception(msg)

# Depth == 2
def inc_idx(idx, counts):
    increased = False
    i = 0
    while not increased and i < len(counts):
        j = 0
        while not increased and j < len(counts[i]):
            idx[i][j] += 1
            if (idx[i][j] == counts[i][j]):
                idx[i][j] = 0
                j += 1
            else:
                increased = True
        i += 1
    if increased:
        return idx
    else:
        return None


# Generate all mappings possible for system in sysdict
def generate_mappings(sysdict):
    vnfs = sysdict['VNFs']
    hosts = sysdict['Hosts']
    chains = sysdict['Chains']
    alloc = sysdict['Allocation']



    options = []
    optCount = []
    idx = []
    for chain in chains:
        subMap = []
        subCount = []
        subIdx = []
        for t in chain.types:
            thisOptions = []
            thisCount = []
            for vnf in vnfs:
                if (vnf.Type == t):
                    thisOptions.append(vnf)
            if not thisOptions: # If any VNF has zero options, no allocations will work
                return []
            subMap.append(thisOptions)
            subCount.append(len(thisOptions))
            subIdx.append(0)
        options.append(subMap)
        optCount.append(subCount)
        idx.append(subIdx)


    allMappings = []
    while idx:
        mapping = []
        for chidx in range(0, len(chains)):
            subMap = []
            for vnfidx in range(0, len(idx[chidx])):
                subMap.append(options[chidx][vnfidx][idx[chidx][vnfidx]])
            mapping.append(Mapping(subMap))
        allMappings.append(mapping)
        idx = inc_idx(idx, optCount)

    return allMappings

# Generate all possible routings given systme sysdict and a mapping
def generate_routings(sysdict, mappings):
    links = sysdict['Links']
    hosts = sysdict['Hosts']
    routing = sysdict['Routing']
    slices = sysdict['Slices']
    chains = sysdict['Chains']
    vnfs = sysdict['VNFs']
    userEquipments = sysdict['UserEquipments']
    allocation = sysdict['Allocation']

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
        # print("No path from " + str(h1) + " to " + str(h2))
        return ret

    # optPerSlice[i][j] contains all the number of possible routes for slice i on step j
    optPerSlice = []
    index = 0
    for (s,c) in zip(slices, chains):
        optionSteps = []
        optCount = []
        for i in range(0, len(c.chain)-1):
            # host1 = alloc.alloc[c.chain[i]]
            host1 = allocation.host(mappings[index].mapping[i])
            # host2 = alloc.alloc[c.chain[i+1]]
            host2 = allocation.host(mappings[index].mapping[i+1])
            opts = getOpts(host1, host2)
            # If there is no path from host1 to host2, there is no routing possible
            if not opts:
                return []
            optionSteps.append(opts)
            optCount.append(len(opts))
        routingOptions.append(optionSteps)
        optPerSlice.append(optCount)
        index += 1


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
def VerifyAllocation(sysdict, mapping, solver, binLocation):
    routings = generate_routings(sysdict, mapping)
    j = 0
    for routing in routings:
        j += 1
        print('.', end='', flush=True)
        # print("\tRouting " + str(j) + "/" + str(len(routings)))
        answer = verify(sysdict, mapping, routing, solver, binLocation)
        if (answer):
            return routing
    return None

# API For verifying system
def Verify(sysdict, solver, binLocation):
    global checks
    checks = 0
    mappings = generate_mappings(sysdict)
    if not mappings:
        raise Exception("No mappings for system")
    i = 0
    for m in mappings:
        i += 1
        print("Mapping " + str(i) + "/" + str(len(mappings)))
        r = VerifyAllocation(sysdict, m, solver, binLocation)
        if r:
            print("Checks: " + str(checks))
            return (m, r)
    print("Checks: " + str(checks))
    return None


# API For verifying system
def VerifySingle(sysdict, solver, binLocation):
    global checks
    checks = 0
    mappings = generate_mappings(sysdict)
    if not mappings:
        raise Exception("No mappings for system")
    mapping = mappings[0]
    routings = generate_routings(sysdict, mapping)
    routing = routings[0]
    answer = verify(sysdict, mapping, routing, solver, binLocation)
    if (answer):
        return (mapping, routing)
    else:
        return None



