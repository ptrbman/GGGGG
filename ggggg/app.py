# Main file for GGGGG program
# Manages the GUI as well as running the back-end, etc.

import PySimpleGUI as sg
import os
import string
import copy
from pathlib import Path

from ggggg.uml_to_uppaal import LoadSystem, ToUPPAAL
from ggggg.run_uppaal import runUPPAAL
from ggggg.solver import Verify
from ggggg.kfault import *

#
#  THEME
#

sg.theme('DefaultNoMoreNagging')

header_font = ("Arial", 20)
font = ("Arial", 12)
textColor = 'black'

#
#  GLOBAL VARIABLES
#

# This is here just so we can forward reference it
window = ""

# These are used as standard values upon startup.
deffolder = Path(os.getcwd() + '/instances/')

currentInfile = None
currentSystem = None
currentMapping = None
currentRouting = None

# Kfault
kfaultresults = []

#
#  BINARY LOCATIONS
#

uppaalLocation = ''
verifytaLocation = ''

# Load "config.txt" and grab binary locations
def loadConfig():
    global uppaalLocation
    global verifytaLocation
    f = open("config.txt", "r")
    uppaalLocation = f.readline().strip()
    verifytaLocation = f.readline().strip()
    f.close()

loadConfig()

# Save binary locations to config.txt
def saveConfig():
    f = open("config.txt", "w")
    f.write(uppaalLocation +"\n")
    f.write(verifytaLocation +"\n")
    f.close()

#
#  QUERY
#

# Functions for generating different queries (based on system)
def QUERYMissedDeadline(sysdict):
    return "A[] not M0.MissedDeadline"

def QUERYQueueFull(sysdict):
    return "A[] not E0.ErrorQueueFull"

def QUERYNoFreeExecutor(sysdict):
    conds = []
    i = 0
    for ue in sysdict['UserEquipments']:
        conds.append("not UE" + str(i) + ".NoFreeExecutor")
        i += 1
    return "A[] (" + "&&".join(conds) + ")"

def QUERYDeadlock(sysdict):
    conds = []
    i = 0
    for ue in sysdict['UserEquipments']:
        conds.append("UE" + str(i) + ".numberOfRequests == " + str(ue.maxInst))
        i += 1
    uestring = "&&".join(conds)
    fquery = "A[] not deadlock || (" + uestring + ")"
    return fquery

# List of all available queries
QUERIES = [
    ("Deadlines met", "Deadlines", QUERYMissedDeadline),
    ("Sufficient queue length", "Queues", QUERYQueueFull),
    ("No deadlock", "Deadlock", QUERYDeadlock),
    ("Sufficient executors", "Executor", QUERYNoFreeExecutor),
]

# Generates and saves a query to correct file
def saveQuery(sysdict, queryName, queryString, modelName):
    q = queryString(sysdict)
    queryFile = os.getcwd() + '/queries/' + modelName + "_" + queryName + ".q"
    f = open(queryFile, "w")
    f.write(q.strip())
    f.close()
    return queryFile

# Generate all queries for system
def genQueries(sysdict, modelName):
    fileNames = []
    for (fullName, shortName, queryString) in QUERIES:
        fileNames.append(saveQuery(sysdict, shortName, queryString, modelName))
    return fileNames

#
#   MAIN LAYOUT
#

# A separator of width w
def sep(w):
    return sg.Text("_"*w, font=("Arial", 8))

verification_layout = [
    ## GENERATE MODEL ##
    [sg.Text('Verification', key="labelGenerate",  font=header_font)],
    [sg.Button('Create UPPAAL model', key='generateUPPAAL', disabled=True), sg.Button('Preview', disabled=True, font=font)],
    [sg.Input('', key='txtUPPAALFile', font=font, disabled=True)],

    ## VERIFY MODEL ##
    [sep(100)],
    [sg.Button(QUERIES[0][0], key='btnDeadlines', size=(30,1), disabled=True),
     sg.Text("Not checked", key='labelDeadlines',  size=(30,1), justification='right', font=font),
     sg.Input('hmm', key="txtDeadlinesQuery", visible=False)],

    [sg.Button(QUERIES[1][0], key='btnQueues', size=(30,1), disabled=True),
     sg.Text("Not checked", key='labelQueues',  size=(30,1), justification='right', font=font),
     sg.Input('hmm', key="txtQueuesQuery", visible=False)],

    [sg.Button(QUERIES[2][0], key='btnDeadlock', size=(30,1), disabled=True),
     sg.Text("Not checked", key='labelDeadlock',  size=(30,1), justification='right', font=font),
     sg.Input('hmm', key="txtDeadlockQuery", visible=False)],

    [sg.Button(QUERIES[3][0], key='btnExecutor', size=(30,1), disabled=True),
     sg.Text("Not checked", key='labelExecutor',  size=(30,1), justification='right', font=font),
     sg.Input('hmm', key="txtExecutorQuery", visible=False)]
    ]

data = [["-", "-"]]

kfault_layout = [
    [sg.Text('K-Fault Tolerance', font=header_font)],
    [sg.Text("Number of hosts to bring down: ", font=font), sg.Text('1', key="txtK", font=font),
     sg.Button('Check', key='btnKFault', size=(25,1), disabled=True)],
    [sg.Table(values=data,
              headings=["Removed Host(s)", "Satisfiable"],
              max_col_width=25,
              justification='right',
              alternating_row_color='lightblue',
              num_rows=20,
              enable_events=True,
              key="kfaulttable"),
    sg.Text("", key='txtKFault', font=font, size=(35,15))],
    [sg.Button('Study', key='btnKFaultStudy', size=(70,3), disabled=True)]
]

settings_layout = [
    [sg.Text("Settings", font=header_font)],
    [sg.Text("UPPAAL Location", font=font)],
    [sg.Input(uppaalLocation, key='uppaalLocation', font=font, enable_events=True),
     sg.FileBrowse(button_text="Browse", font=font, target='uppaalLocation', initial_folder=uppaalLocation)],
    [sg.Text("verifyta Location", font=font)],
     [sg.Input(verifytaLocation, key='verifytaLocation', font=font, enable_events=True),
      sg.FileBrowse(button_text="Browse", font=font, target='verifytaLocation', initial_folder=verifytaLocation)],
    [sg.Text("Executors/Monitors: ", key="labelExecutorMonitor", font=font),
     sg.Input('2', key='txtExecutors', font=font, size=(4,1)),
     sg.Text("Message Queue Length: ", key="labelQueue", font=font),
     sg.Input('3', key='txtQueue', font=font, size=(4,1))]
]

details_layout = [
    [sg.Text('Instance details:', key="labelInstance", font=header_font)],
    [sg.Text("Hosts:",   key="labelHosts", font=font), sg.Text('--', key="txtHosts", font=font),
     sg.Text("VNFs:",   key="labelVNFs", font=font), sg.Text('--', key="txtVNFs",  font=font),
     sg.Text("Slices:",   key="labelSlices", font=font), sg.Text('--', key="txtSlices",  font=font),
     sg.Text("User Equipment:",   key="labelUEs", font=font), sg.Text('--', key="txtUEs",  font=font),
     sg.Text("Links:",   key="labelLinks", font=font), sg.Text('--', key="txtLinks",  font=font)],
    [sg.Text("Mapping", font=header_font)],
    [sg.Text("No mapping", key='txtFindMapping', font=font, size=(50,15))],
    [sg.Button('Find mapping', key='btnFindMapping', size=(70,3), disabled=True)]
]

layout = [
    [sg.Column([[sg.Image("ggggg/resources/logo.png")]], justification='center')],

    ## LOAD INSTANCE ##
    [sg.Input('', key='InstanceFile', enable_events=True, visible=False, font=font),
     sg.FileBrowse(button_text="Load Instance", font=font, initial_folder=str(deffolder.absolute()), target='InstanceFile'),
     sg.Text('Instance name:', font=font), sg.Text('n/a', key='labelInstanceName', size=(30,1), font=font)],

    [sep(100)],

    [sg.TabGroup([[sg.Tab('Details', details_layout),
                   sg.Tab('Verification', verification_layout),
                   sg.Tab('K-Fault', kfault_layout),
                   sg.Tab('Settings', settings_layout)
                   ]],
                 tab_background_color='white',
                 background_color='white',
                 selected_background_color='blue')]]

window = sg.Window('GGGGG', layout)

## Enables widgets and changes text color depending on what stage in the process the user is
def set_stage(stage):
    if stage == 1:
        window['txtExecutors'].update(disabled=False)
        window['txtQueue'].update(disabled=False)
        window['generateUPPAAL'].update(disabled=False)
        window['btnFindMapping'].update(disabled=False)
        window['btnKFault'].update(disabled=False)

        ## Disable stage 2 (in case previously enabled)
        window['Preview'].update(disabled=True)
        window['btnDeadlines'].update(disabled=True)
        window['btnDeadlock'].update(disabled=True)
        window['btnExecutor'].update(disabled=True)
        window['btnQueues'].update(disabled=True)

    if stage == 2:
        window['Preview'].update(disabled=False)
        window['labelDeadlines'].update(value="Not Checked")
        window['labelQueues'].update(value="Not Checked")
        window['labelDeadlock'].update(value="Not Checked")
        window['labelExecutor'].update(value="Not Checked")
        window['btnDeadlines'].update(disabled=False)
        window['btnDeadlock'].update(disabled=False)
        window['btnQueues'].update(disabled=False)
        window['btnExecutor'].update(disabled=False)

# Loads instance infile and updates info accordingly
def load_instance(infile):
    instanceName = os.path.splitext(os.path.basename(infile))[0]
    window['labelInstanceName'].update(instanceName)
    sysdict = LoadSystem(infile)
    window['txtHosts'].update(str(len(sysdict['Hosts'])))
    window['txtVNFs'].update(str(len(sysdict['VNFs'])))
    window['txtSlices'].update(str(len(sysdict['Slices'])))
    window['txtUEs'].update(str(len(sysdict['UserEquipments'])))
    window['txtLinks'].update(str(len(sysdict['Links'])))
    set_stage(1)
    return sysdict

# Generate a UPPAAL model from instance in infile with executors and queueLength
def generate_uppaal(infile, sysdict, executors, queueLength):
    if not currentMapping:
        sg.Popup("Cannot create UPPAAL model until mapping has been found.")
    else:
        modelName = os.path.splitext(os.path.basename(infile))[0]
        uppaalFile = os.getcwd() + '/models/' + modelName + '.xml'
        sysdict['Mappings'] = currentMapping
        sysdict['Routing'] = currentRouting
        ToUPPAAL(sysdict, uppaalFile, executors, queueLength)

        queryFileNames = genQueries(sysdict, modelName)
        window['txtDeadlinesQuery'].update(value=queryFileNames[0])
        window['txtQueuesQuery'].update(value=queryFileNames[1])
        window['txtDeadlockQuery'].update(value=queryFileNames[2])
        window['txtExecutorQuery'].update(value=queryFileNames[3])
        window['txtUPPAALFile'].update(value=uppaalFile)
        set_stage(2)

# Opens UPPAAL to study file modelFile
def preview(uppaalfile, modelFile):
    currentDir = str(Path(os.getcwd()).absolute())
    uppaalDir = Path(os.path.dirname(uppaalfile))
    modelPath = str(Path(modelFile).absolute())
    os.chdir(str(uppaalDir.absolute()))
    #uppaalCmd = "./uppaal"
    uppaalCmd = str(Path(uppaalfile).absolute())
    cmd = uppaalCmd + " " + modelPath 
    print("\n\t", cmd)
    # cmd = "\"" + uppaalCmd + "\"" # \"" //+ str(infile) + "\" \"" + queryfile + "\" > " + "\"" + outputfile + "\""
    os.system(cmd)
    os.chdir(currentDir)

# Run UPPAAL using query
def verify(uppaalfile, query, queryfile):
    outputfile = os.getcwd() + '/tmp/' + 'tmp'
    answers = runUPPAAL(values['verifytaLocation'], uppaalfile, queryfile, outputfile)
    window['label' + query].update(answers[0][1])
    window['btn' + query].update(disabled=True)

def find_mapping(sysdict, executors, queue):
    sysdict['Executors'] = executors
    sysdict['QueueLength'] = queue

    # TODO: What if nothing found?
    (mappings, r) = Verify(sysdict, verifytaLocation)
    msg = ""
    for (s, mm) in zip(sysdict['Slices'], mappings):
        msg += s.name + ": " + "->".join(list(map(lambda v : v.name, mm.mapping))) + "\n"

    window['txtFindMapping'].update(msg)
    return (mappings, r)

def kfault(sysdict, executors, queue):
    global kfaultresults
    sysdict['Executors'] = executors
    sysdict['QueueLength'] = queue
    kfaultresults = kfaulthosts(1, sysdict, verifytaLocation)
    tableData = []
    for (h, r, s) in kfaultresults:
        if r:
            tableData.append([h.name, "SAT"])
        else:
            tableData.append([h.name, "UNSAT"])
    window['kfaulttable'].update(tableData)
    window['btnKFaultStudy'].update(disabled=True)

while True:
    event, values = window.read()

    ### QUIT ###
    if event == sg.WINDOW_CLOSED or event == 'Quit':
        break

    ### LOAD INSTANCE ###
    elif event == 'InstanceFile':
        currentInfile = values['InstanceFile']
        currentSystem = load_instance(currentInfile)
        (a, r) = (currentSystem['Allocation'], currentSystem['Routing'])
        # if a and r:
            # currentMapping = a
            # currentRouting = rr
            # window['txtFindMapping'].update(currentMapping)

    ### GENERATE MODEL ###
    elif event == 'generateUPPAAL':
        generate_uppaal(currentInfile, currentSystem, int(values['txtExecutors']), int(values['txtQueue']))

    ### PREVIEW ###
    elif event == 'Preview':
        preview(values['uppaalLocation'], values['txtUPPAALFile'])

    ### VERIFY DEADLINES ###
    elif event == 'btnDeadlines':
        uppaalfile = values['txtUPPAALFile']
        queryfile = values['txtDeadlinesQuery']
        verify(uppaalfile, "Deadlines", queryfile)

    ### VERIFY QUEUES ###
    elif event == 'btnQueues':
        uppaalfile = values['txtUPPAALFile']
        queryfile = values['txtQueuesQuery']
        verify(uppaalfile, "Queues", queryfile)

    ### VERIFY DEADLOCK ###
    elif event == 'btnDeadlock':
        uppaalfile = values['txtUPPAALFile']
        queryfile = values['txtDeadlockQuery']
        verify(uppaalfile, "Deadlock", queryfile)

    ### VERIFY EXECUTOR ###
    elif event == 'btnExecutor':
        uppaalfile = values['txtUPPAALFile']
        queryfile = values['txtExecutorQuery']
        verify(uppaalfile, "Executor", queryfile)

    ### FIND MAPPINGS ###
    elif event == 'btnFindMapping':
        (a, r) = find_mapping(currentSystem, int(values['txtExecutors']), int(values['txtQueue']))
        currentMapping = a
        currentRouting = r

    ### KFAULT ###
    elif event == 'btnKFault':
        kfault(currentSystem, int(values['txtExecutors']), int(values['txtQueue']))
        window['btnKFault'].update(disabled=True)

    elif event == 'kfaulttable':
        if kfaultresults:
        ## If multiple are selected, pick first one
            selected = values['kfaulttable'][0]
            (h, r, s) = kfaultresults[selected]
            if r:
                (mappings, r) = r
                msg = ""
                sysdict = currentSystem
                for (s, mm) in zip(sysdict['Slices'], mappings):
                    msg += s.name + ": " + "->".join(list(map(lambda v : v.name, mm.mapping))) + "\n"
                window['txtKFault'].update(msg)
            else:
                window['txtKFault'].update("No mapping found")
            window['btnKFaultStudy'].update(disabled=False)

    elif event == 'btnKFaultStudy':
        selected = values['kfaulttable'][0]
        uppaalFile = os.getcwd() + '/tmp/kfaultstudy.xml'
        (h, res, s) = kfaultresults[selected]
        if res:
            (a, r) = res
            newDict = s
            newDict['Mapping'] = a
            newDict['Routing'] = r
            ToUPPAAL(newDict, uppaalFile, int(values['txtExecutors']), int(values['txtQueue']))
            preview(values['uppaalLocation'], uppaalFile)
        else:
            sg.Popup('Cannot study UNSAT cases.')

    ### CHANGE UPPAALLOCATION ###
    elif event == 'uppaalLocation':
        if (values['uppaalLocation'] != ''):
            uppaalLocation = values['uppaalLocation']
            saveConfig()

    ### CHANGE VERIFYTALOCATION ###
    elif event == 'verifytaLocation':
        if (values['verifytaLocation'] != ''):
            verifytaLocation = values['verifytaLocation']
            saveConfig()


    ### UNRECOGNIZED EVENT ###
    else:
        print("Unrecognized event:", event)

window.close()
