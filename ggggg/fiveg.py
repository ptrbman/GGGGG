# Classes to represent a 5G system. Methods to convert to UPPAAL.
# t-functions are used in creation of UPPAL models.

### uid = uppaal_id and has to be from 0 to |hosts|-1, etc.
### should be updated before model is generated

class VNF:
    def __init__(self, i, name, uid, BCET=-1, WCET=-1, Prio=-1, Type=''):
        self.i = i
        self.name = name
        self.uid = uid
        self.BCET = BCET
        self.WCET = WCET
        self.Prio = Prio
        self.Type = Type

    def t(self):
        return "{" + str(self.uid) + ", " + str(self.BCET) + ", " + str(self.WCET) + ", " + str(self.Prio) + "}"

    def __str__(self):
        return "VNF<" + str(self.i) + ", " + str(self.uid) + ", " + str(self.BCET) + ", " + str(self.WCET) + ", " + str(self.Prio) + ", " + str(self.Type) + ">"

class Host:
    def __init__(self, i, name, uid, cpu=-1, stor=-1, mec="", capabilities = []):
        self.i = i
        self.name = name
        self.uid = uid
        self.cpu = cpu
        self.stor = stor
        self.mec = mec
        self.capabilities = capabilities

    def __str__(self):
        return "HOST<" + self.name + ", " + str(self.i) + ", " + str(self.uid) + ", " + str(self.cpu) + ", " + str(self.stor) + ", " + str(self.mec) + ", " + str(self.capabilities) + ">"

    def t(self):
        return "{" + str(self.uid) + ", " + str(self.cpu) + ", " + str(self.stor) + ", " + str(self.mec) + "}"

class Link:
    def __init__(self, i, uid, begin, end, bw=-1, delay=-1):
        self.i = i
        self.begin = begin
        self.end = end
        self.uid = uid
        self.bw = bw
        self.delay = delay

    def __str__(self):
        return "Link<" + str(self.begin.name) + ", " + str(self.end.name) + ">"
    def t(self):
        return "{" + str(self.uid) + ", " + str(self.bw) + ", " + str(self.delay) + "}"


class Route:
    def __init__(self, i, route=[]):
        self.i = i
        self.route = route

    def len(self):
        return len(self.route)

    def __str__(self):
        if (not self.route):
            return "()"
        else:
            s = []
            for link in self.route:
                s.append(str(link))
            return '->'.join(s)

    def t(self, maxLinkStep):
        unpadded = list(map(lambda r : str(r.uid), self.route))
        padding = (['-1']*(maxLinkStep - len(unpadded)))
        padded = unpadded + padding
        return "{" + ', '.join(padded) + "}"

class UserEquipment:
    def __init__(self, i, maxInst=-1, actTime=-1, subscribedSlice=-1):
        self.i = i
        self.maxInst = maxInst
        self.actTime = actTime,
        self.subscribedSlice = subscribedSlice

class Slice:
    def __init__(self, i, uid, bw=-1, lat=-1, chainLength=-1):
        self.i = i
        self.uid = uid
        self.bw = bw
        self.lat = lat
        self.chainLength = chainLength

    def t(self):
        return "{" + str(self.uid) + ", " + str(self.bw) + ", " + str(self.lat) + ", " + str(self.chainLength) + "}"

class RoutingTable:
    def __init__(self, routingtable = []):
        self.routingtable = routingtable

    def maxLinkStep(self):
        if not self.routingtable:
            # We need 1 here, otherwise we generate a zero-length array in UPPAAL
            return 1
        else:
            res = max(map(lambda rs : rs.len(), self.routingtable))
            if res == 0:
                return 1
            else:
                return res

    def __str__(self):
        s = []
        for route in self.routingtable:
            s.append(">" + str(route))
        return '\n'.join(s)

    def t(self, maxChainLength, maxLinkStep):
        maxRouteLength = maxChainLength
        unpadded = list(map(lambda r : r.t(maxLinkStep), self.routingtable))
        p = "{" + ', '.join(['-1']*maxLinkStep) + "}"
        padding = ([p]*(maxRouteLength - len(unpadded)))
        padded = unpadded + padding
        return "{" + ', '.join(padded) + "}"

class SliceChain:
    def __init__(self, chain):
        self.chain = chain

    def len(self):
        return len(self.chain)

    def __str__(self):
        return "Chain<" + str(self.chain) + ">"

    def t(self, maxChainLength):
        ids = list(map(lambda c : str(c.uid), self.chain))
        padded = ids + (['-1']*(maxChainLength - len(ids)))
        return "{" + ', '.join(padded) + "}"


class Allocation:
    def __init__(self, alloc):
        self.alloc = alloc
    def t(self, vnfs):
        l = []
        for v in vnfs:
            l.append(self.alloc[v])
        return "{" + ', '.join(list(map(lambda c : str(c.uid), l))) + "}"

    def __str__(self):
        msg = []
        for vnf in self.alloc:
            msg.append(vnf.name + " --> " + self.alloc[vnf].name)
        return('\n'.join(msg))

# (Very) simple error checking of systems before outputting them
def checkSystem(hosts, vnfs, links, slices, chains, alloc, routing, queueLength, executorCount):
    if (not slices):
        return "No slices defined"
    else:
        return ""

# Gives the SYSTEM part to be inserted into template
def systemString(hosts, vnfs, links, slices, chains, alloc, routing, queueLength, executorCount):
    ### TODO: We have one extra element in chain!
    maxChainLength = max(map(lambda c : c.len(), chains))
    maxLinkStep = max(map(lambda r : r.maxLinkStep(), routing))
    return "const int HostCount = " + str(len(hosts)) + ";\n" +\
    "const int VNFCount = " + str(len(vnfs)) + ";\n"\
    "const int SliceCount = " + str(len(slices)) + ";\n" +\
    "const int MaxChainLength = " + str(maxChainLength) + ";\n" +\
    "const int MaxLinkStep = " + str(maxLinkStep) + ";\n"+\
    "const int QueueLength = " + str(queueLength) + ";\n"+\
    "const int ExecutorCount = " + str(executorCount) + ";\n"+\
    "const int MonitorCount = " + str(executorCount) + ";\n"+\
    "int AvailableExecutors = ExecutorCount;\n"+\
    "int AvailableMonitors = MonitorCount;\n"+\
    "\n"+\
    "host hosts[" + str(len(hosts)) + "] = {" + ', '.join(list(map(lambda h : h.t(), hosts))) + "};\n"+\
    "vnf vnfs[" + str(len(vnfs)) + "] = {" + ', '.join(list(map(lambda v : v.t(), vnfs))) + "};\n"+\
    "link links[" + str(len(links)) + "] = {" + ', '.join(list(map(lambda l : l.t(), links)))+ "};\n"+\
    "slice slices[" + str(len(slices)) + "] = { " + ', '.join(list(map(lambda s : s.t(), slices))) + "};\n"+\
    "int SliceChains[SliceCount][MaxChainLength] = {" + ', '.join(list(map(lambda c : c.t(maxChainLength), chains))) + "};\n"+\
    "int AllocV[VNFCount] = " + alloc.t(vnfs) + ";\n"+\
    "int RT[SliceCount][MaxChainLength][MaxLinkStep] = {" + ', '.join(list(map(lambda r : r.t(maxChainLength, maxLinkStep), routing))) + "};\n"


# Gives the INSTANCE part to be inserted into template
def instantiationString(hosts, userEquipments, executionCount):
    allTAs = "system "
    hostsString = ""

    i = 0
    for h in hosts:
        hostsString = hostsString + "\n" + "Host" + str(i) + " = Host(" + str(i) + ");"
        allTAs = allTAs + "Host" + str(i) + ", "
        i = i + 1

    uesString = ""
    i = 0
    for ue in userEquipments:
        uuee = "(" + str(i) + ", " + str(ue.subscribedSlice) + ", " + str(ue.maxInst) + ", " + str(ue.actTime) + ")"
        uesString = uesString + "\n" + "UE" + str(i) + " = UserEquipment" + uuee + ";"
        allTAs = allTAs + "UE" + str(i) + ", "
        i = i + 1

    executorString = ""
    for i in range(0, executionCount):
        executorString = executorString + "\n" + "E" + str(i) + " = Executor(" + str(i) + ");"
        allTAs = allTAs + "E" + str(i) + ", "

    monitorString = ""
    for i in range(0, executionCount):
        monitorString = monitorString + "\n" + "M" + str(i) + " = Monitor(" + str(i) + ");"
        allTAs = allTAs + "M" + str(i) + ", "

    allTAs = allTAs + " Generator;"

    return hostsString + "\n\n" + uesString + "\n\n" + executorString + "\n\n" + monitorString + "\n\n" + allTAs + "\n\n"



# Gives a complete string for a UPPAAL model consisting of all the parameters
def generateSystem(hosts, vnfs, links, slices, chains, alloc, routing, userEquipments, queueLength, executorCount):
    sysStr = systemString(hosts, vnfs, links, slices, chains, alloc, routing, queueLength, executorCount)
    instStr = instantiationString(hosts, userEquipments, executorCount)

    template = open("template.xml", "r")
    fullString = ''.join(template)
    fullString = fullString.replace('// --SYSTEM--', sysStr)
    fullString = fullString.replace('// --INSTANCE--', instStr)

    return fullString
