from ggggg.uml_to_uppaal import LoadSystem, ToUPPAAL
import ggggg.fiveg
from ggggg.kfault import *
from ggggg.solver import *
import copy
import sys
import time

## CONFIGURE THESE
vtaloc = "/Applications/uppaal64-4.1.24/bin-Darwin/verifyta"

(LB1, UB1) = (1, 1)
(LB2, UB2) = (1, 1)
(LB3, UB3) = (1, 1)
(LB4, UB4) = (1, 10)

executors = 4
queue_length = 4
instanceName = sys.argv[1]
print("Loading: " + instanceName)


def run(sysdict):
    start_time = time.time()
    answer = Verify(sysdict, vtaloc)
    end_time = time.time()
    total_time = end_time - start_time
    return (bound, answer, total_time)

#### 1] Increase activation count for each node ####
print("Running max instantiations from " + str(LB1) + " to " + str(UB1))

# (BOUND, ANSWER, TIME)
results1 = []

for bound in range(LB1, UB1+1):
    print("Max insantiations: " + str(bound))
    sysdict = LoadSystem(instanceName)
    UE = sysdict['UserEquipments']
    for ue in UE:
        ue.maxInst = bound

    sysdict['Executors'] = bound*len(UE)
    sysdict['QueueLength'] = bound*len(UE)

    results1.append(run(sysdict))

##### 2] Increase number of user equipment
results2 = []


for bound in range(LB2, UB2+1):
    print("Copies of UEs: " + str(bound))
    sysdict = LoadSystem(instanceName)
    UE = sysdict['UserEquipments']

    newUE = []
    for ue in UE:
        for _ in range(0, bound):
            newUE.append(UserEquipment(-1, int(ue.maxInst), int(ue.actTime), int(ue.subscribedSlice)))

    sysdict['UserEquipments'] = UE + newUE
    sysdict['Executors'] = bound*len(UE)
    sysdict['QueueLength'] = bound*len(UE)

    results2.append(run(sysdict))



### 3] Increase number of Executors
results3 = []

for bound in range(LB3, UB3+1):
    print("Executors: " + str(bound))
    sysdict = LoadSystem(instanceName)
    sysdict['Executors'] = bound
    sysdict['QueueLength'] = 4

    results3.append(run(sysdict))

for (b, a, t) in results3:
    if a:
        res = "SAT"
    else:
        res = "UNSAT"
    print(str(b) + "\t" + res + "\t" + str(t))

### 4] Increase queue length 
results4 = []

for bound in range(LB4, UB4+1):
    print("Queue Length: " + str(bound))
    sysdict = LoadSystem(instanceName)
    sysdict['Executors'] = executors
    sysdict['QueueLength'] = bound

    results4.append(run(sysdict))

for results in [results1, results2, results3, results4]:
    print("RESULTS")
    for (b, a, t) in results:
        if a:
            res = "SAT"
        else:
            res = "UNSAT"
        print(str(b) + "\t" + res + "\t" + str(t))

