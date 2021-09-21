from ggggg.fiveg import Route

import copy
import itertools
import subprocess

nextActionID = 0

class Action():
    def setID(self):
        global nextActionID
        self.ID = nextActionID
        nextActionID += 1

    def name(self):
        return self.prefix + "_" + str(self.ID)

    def zero(self):
        return self.prefix + "_" + str(self.ID) + "_0"

    def begin(self):
        return self.prefix + "_" + str(self.ID) + "_b"

    def end(self):
        return self.prefix + "_" + str(self.ID) + "_e"

    def declarations(self):
        declarations = []
        declarations.append("(declare-fun " + self.zero() + " () Int)")
        declarations.append("(declare-fun " + self.begin() + " () Int)")
        declarations.append("(declare-fun " + self.end() + " () Int)")
        return declarations

    def __str__(self):
        return self.prefix + "[" + str(self.ID) + "]"

class HostAction(Action):
    def __init__(self, host, BCET, WCET):
        self.prefix = "H" + str(host.uid)
        self.host = host
        self.BCET = BCET
        self.WCET = WCET
        self.duration = WCET

    def instantiate(self):
        newAction = HostAction(self.host, self.BCET, self.WCET)
        newAction.setID()
        return newAction

    def __str__(self):
        return "HOST_" + str(self.host)

class LinkAction(Action):
    def __init__(self, link, duration, bandwidth):
        self.prefix = "L" + str(link.uid)
        self.link = link
        self.duration = duration
        self.bandwidth = bandwidth

    def instantiate(self):
        newAction = LinkAction(self.link, self.duration, self.bandwidth)
        newAction.setID()
        return newAction

    def __str__(self):
        return "LINK_" + str(self.link)

class Request():
    def __init__(self, actions, deadline):
        self.actions = actions
        self.deadline = deadline

    def instantiate(self, startTime):
        newActions = []
        for a in self.actions:
            newActions.append(a.instantiate())
        return Schedule(newActions, startTime, self.deadline)

    def __str__(self):
        ret = str(self.actions[0])
        for a in self.actions[1:]:
            ret += "->" + str(a)
        return ret

class Schedule():
    def __init__(self, actions, startTime, deadline):
        self.actions = actions
        self.startTime = startTime
        self.deadline = deadline

    def linkActions(self):
        return list(filter(lambda x : isinstance(x, LinkAction), self.actions))

    def hostActions(self):
        return list(filter(lambda x : isinstance(x, HostAction), self.actions))

    def __str__(self):
        ret = str(self.actions[0])
        for a in self.actions[1:]:
            ret += "->" + str(a)
        return ret


##
## END OF CLASS DECLARATIONS
##

def requests(sysdict, mappings, routings):

    # Convert each slice to a sequence of hosts/link actions
    sliceRequests = []
    hostActions = []
    linkActions = []
    for (s, m, r) in zip(sysdict['Slices'], mappings, routings):
        actions = []
        for (vnf, route) in zip(m.mapping, r.routingtable + [Route(-1)]):
            hAction = HostAction(sysdict['Allocation'].host(vnf), vnf.BCET, vnf.WCET)
            hostActions.append(hAction)
            actions.append(hAction)
            for l in route.route:
                lAction = LinkAction(l, l.delay, s.bw)
                actions.append(lAction)
                linkActions.append(lAction)
        sliceRequests.append(Request(actions, s.lat))

    return sliceRequests

def schedules(sysdict, sliceMap):
    userEquipment = sysdict['UserEquipments']
    scheds = []
    for ue in userEquipment:
        actTime = int(ue.actTime)
        for i in range(int(ue.maxInst)):
            scheds.append(sliceMap[int(ue.subscribedSlice)].instantiate(actTime*(i+1)))
    return scheds

###
### SMT
###

def SMTVariables(actions):
    declarations = []
    for a in actions:
        declarations.extend(a.declarations())

    return declarations

def SMTSoundHostActions(actions):
    constraints = []
    for a in actions:
        c1 = "(<= 0 " + str(a.zero()) + ")"
        c2 = "(<= " + str(a.zero()) + " " + str(a.begin()) + ")"
        c3 = "(<= " + str(a.begin()) + " " + str(a.end()) + ")"
        dur = "(- " + str(a.end()) + " " + str(a.begin()) + ")"
        c4 = "(>= " + dur + " " + str(a.BCET) + ")"
        c5 = "(<= " + dur + " " + str(a.WCET) + ")"

        constraints.append("(and " + c1 + " " + c2 + " " + c3 + " " + c4 + " " + c5 + ")")

    return constraints

def SMTSoundLinkActions(actions):
    constraints = []
    for a in actions:
        c1 = "(<= 0 " + str(a.zero()) + ")"
        c2 = "(<= " + str(a.zero()) + " " + str(a.begin()) + ")"
        c3 = "(<= " + str(a.begin()) + " " + str(a.end()) + ")"
        dur = "(- " + str(a.end()) + " " + str(a.begin()) + ")"
        c4 = "(= " + dur + " " + str(a.duration) + ")"

        constraints.append("(and " + c1 + " " + c2 + " " + c3 + " " + c4 + ")")

    return constraints

def SMTSoundSchedules(schedules):
    constraints = []
    for s in schedules:
        start = "(= " + s.actions[0].zero() + " "  + str(s.startTime) + ")"
        constraints.append(start)
        for i in range(len(s.actions)-1):
            c1 = "(= " + str(s.actions[i].end()) + " " + str(s.actions[i+1].zero()) + ")"
            constraints.append(c1)

    return constraints

def SMTDeadlineViolated(schedules):
    constraint = "(or"
    for s in schedules:
        dur = "(- " + s.actions[-1].end() + " " + str(s.startTime) + ")"
        deadline = "(> " + dur + " "  + str(s.deadline) + ")"
        constraint += " " + deadline

    return [constraint + ")"]

def SMTNoHostOverlap(hostActionMap):
    constraints = []
    for host in hostActionMap:
        for (a1, a2) in itertools.combinations(hostActionMap[host], r=2):
            c1 = "(<= " + str(a1.end()) + " " + str(a2.begin()) + ")"
            c2 = "(<= " + str(a2.end()) + " " + str(a1.begin()) + ")"
            constraints.append("(or " + c1 + " " + c2 + ")")
    return constraints

def between(t, l, u):
    c1 = "(>= " + t + " " + l + ")"
    c2 = "(< " + t + " " + u + ")"
    return "(and " + c1 + " " + c2 + ")"

def inside(t, a):
    c1 = "(>= " + t + " " + a.begin() + ")"
    c2 = "(< " + t + " " + a.end() + ")"
    return "(and " + c1 + " " + c2 + ")"

def usedBW(linkAction, t):
    cond = inside(t, linkAction)
    exp = "(ite " + cond + " " + str(linkAction.bandwidth) + " 0)"
    return exp

def SMTNoLinkOverutilization(linkActionMap, bandwidthMap):
    constraints = []
    for l in linkActionMap:
        actions = linkActionMap[l]
        # bandwidth = bandwidthMap[l]
        bandwidth = l.bw

        # Compute linkstarts
        linkStarts = []
        for a in actions:
            linkStarts.append(a.begin())

        for ls in linkStarts:
            used = "(+"
            for a in actions:
                used += " " + usedBW(a, ls)
            total = used + ")"
            constraint = "(<= " + total + " " + bandwidth + ")"
            constraints.append(constraint)

    return constraints


def sumofBW(linkActions, t):
    if not linkActions:
        return "0"
    else:
        total = "(+"
        for l in linkActions:
            total += " " + usedBW(l, t)
        final = total + ")"
        return final

def linkCongested(linkActions, t, bandwidth):
    constraint = "(> " + sumofBW(linkActions, t) + " " + str(bandwidth) + ")"
    return constraint



def SMTLinkUrgency(linkActionMap, bandwidthMap):
    constraints = []
    for l in linkActionMap:
        # bandwidth = bandwidthMap[l]
        bandwidth = l.bw
        actions = linkActionMap[l]
        linkEnds = []

        for a in actions:
            linkEnds.append(a.end())

        for a in actions:

            relevantTimes = ([a.zero()] + linkEnds)
            relevantTimes.remove(a.end())

            otherActions = actions.copy()
            otherActions.remove(a)

            ## The link must be congested at all relevant times
            ## I.e., all link ends t, if t is within the interval, it must be congested
            for t in relevantTimes:
                cond = between(t, a.zero(), a.begin())
                c = linkCongested(otherActions, t, (int(bandwidth)-int(a.bandwidth)))
                const = "(=> " + cond + " " + c + ")"
                constraints.append(const)

    return constraints


def existsHostAction(hostActions, t, priority):
    if not hostActions:
        return "false"

    options = "(or"
    for a in hostActions:
        # This action must be ongoing
        cond1 = inside(t, a)
        # This action must have higher (or equal) priority
        cond2 = "(<= " + str(a.zero()) + " " + str(priority) + ")"
        options += " (and " + cond1 + " " + cond2 + ")"

    return options + ")"

# Make sure that each host-action is first come first serve and no idling
def SMTScheduling(hostActionMap):
    constraints = []
    for h in hostActionMap:
        actions = hostActionMap[h]
        hostEnds = []
        for a in actions:
            hostEnds.append(a.end())

        for a in actions:
            ## Lets create a list of relevant times for this action.
            ## This is all the points where an action ends.
            otherActions = actions.copy()
            otherActions.remove(a)
            relevantTimes = ([a.zero()] + hostEnds)
            relevantTimes.remove(a.end())
            for t in relevantTimes:
                and1 = "(<= " + a.zero() + " " + t + ")"
                and2 = "(< " + t + " " + a.begin() + ")"
                condition = "(and " + and1 + " " + and2 + ")"
                exists = existsHostAction(otherActions, t, a.zero())
                c = "(=> " + condition + " " + exists + ")"
                constraints.append(c)

    return constraints


###
### SMT END
###

def verify_smt(sysdict, mappings, routing, z3Location):

    # Create all requests
    reqs = requests(sysdict, mappings, routing)

    # Create all schedules
    scheds = schedules(sysdict, reqs)

    # Extract all actions
    linkActions = []
    hostActions = []

    for s in scheds:
        linkActions.extend(s.linkActions())
        hostActions.extend(s.hostActions())

    # Sort actions according to host/link-id
    hostActionMap = {}
    linkActionMap = {}

    for ha in hostActions:
        if not ha.host in hostActionMap:
            hostActionMap[ha.host] = []
        hostActionMap[ha.host].append(ha)

    for la in linkActions:
        if not la.link in linkActionMap:
            linkActionMap[la.link] = []
        linkActionMap[la.link].append(la)


    # We need map from links to bandwidth
    bandwidthMap = {}
    # for l in sysdict['Links']:
    #     bandwidthMap[l] = bw


    # SMT Variables
    varDecl = SMTVariables(linkActions + hostActions)

    # SMT Constraints
    soundHostActions = SMTSoundHostActions(hostActions)
    soundLinkActions = SMTSoundLinkActions(linkActions)
    soundSchedules = SMTSoundSchedules(scheds)
    noHostOverlap = SMTNoHostOverlap(hostActionMap)
    noLinkOverutilization = SMTNoLinkOverutilization(linkActionMap, bandwidthMap)
    hostScheduling = SMTScheduling(hostActionMap)
    linkUrgency = SMTLinkUrgency(linkActionMap, bandwidthMap)
    deadlineViolated = SMTDeadlineViolated(scheds)

    ## Helper functions to print formula to file 
    def pw(string, f):
        f.write(string + "\n")

    def pc(desc, constraints, f):
        pw(";; " + desc, f)
        for c in constraints:
            pw("(assert " + c + ")", f)
        pw("\n", f)

    # Print to file
    f = open("tmp/verify.smt2", "w")

    # Variable declarations
    for d in varDecl:
        pw(d, f)
    pw("\n\n", f)

    # Each group of constraints
    pc("Sound Host", soundHostActions, f)
    pc("Sound Link", soundLinkActions, f)
    pc("Sound Schedules", soundSchedules, f)
    pc("Host Scheduling", hostScheduling, f)
    pc("No Link Overutilization", noLinkOverutilization, f)
    pc("No Host Overlap", noHostOverlap, f)
    pc("Link Urgency", linkUrgency, f)
    pc("Deadline Violated", deadlineViolated, f)

    pw("(check-sat)", f)
    f.close()


    # Also print out the schedules such that we can parse the output
    f = open("tmp/verify.schedules", "w")

    for s in scheds:
        for a in s.actions:
            f.write(a.name() + " ")
        f.write("\n")
    f.close()

    filename = "tmp/verify.smt2"
    ret = subprocess.run(["z3", filename], stdout=subprocess.PIPE)
    answer = ret.stdout.decode('utf-8')

    # We invert since SMT model is backwards, i.e., a solution shows the existence of a broken trace.
    result = answer.strip()
    if result == "unsat":
        return True

    if result == "sat":
        return False

    raise Exception("Unknown result: " + str(result))
