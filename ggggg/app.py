# Main file for GGGGG program
# Manages the GUI as well as running the back-end, etc.

import PySimpleGUI as sg
import os
import random
import string

from ggggg.uml_to_uppaal import LoadSystem, ToUPPAAL
from ggggg.run_uppaal import runUPPAAL
from ggggg.generate_routings import AllRoutings

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
deffolder = os.getcwd() + '/instances/'

#
#  BINARY LOCATIONS
#

uppaalLocation = ''
verifytaLocation = ''

def loadConfig():
    global uppaalLocation
    global verifytaLocation
    f = open("config.txt", "r")
    uppaalLocation = f.readline().strip()
    verifytaLocation = f.readline().strip()
    f.close()

loadConfig()

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
    return "A[] not UE0.NoFreeExecutor"

def QUERYNoFreeMonitor(sysdict):
    return "A[] not UE0.NoFreeMonitor"

def QUERYNeedRerouting(sysdict):
    return "A[] not E0.NeedRerouting"

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
    ("Queues not full", "Queues", QUERYQueueFull),
    ("No deadlock", "Deadlock", QUERYDeadlock),
    ("No free executor", "Executor", QUERYNoFreeExecutor),
    ("No free monitor", "Monitor", QUERYNoFreeMonitor),
    ("Need Rerouting", "Rerouting", QUERYNeedRerouting),
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

main_layout = [
    ## GENERATE MODEL ##
    [sg.Text('Generate UPPAAL model', key="labelGenerate", text_color='gray', font=header_font)],
    [sg.Button('Create UPPAAL model', key='generateUPPAAL', disabled=True)],

    [sep(100)],

    ## VERIFY MODEL ##
    [sg.Text('Verify UPPAAL model', key='labelVerify', text_color='gray', font=header_font)],
    [sg.Button('Preview', disabled=True, font=font)],
    [sg.Input('', key='txtUPPAALFile', font=font, disabled=True)],
    [sg.Button('Check Deadlines Met', key='btnDeadlines', disabled=True),
     sg.Text("Not checked", key='labelDeadlines', text_color='gray', font=font),
     sg.Input('hmm', key="txtDeadlinesQuery", visible=False)],

    [sg.Button('Check Message Queues Not Full', key='btnQueues', disabled=True),
     sg.Text("Not checked", key='labelQueues', text_color='gray', font=font),
     sg.Input('hmm', key="txtQueuesQuery", visible=False)],

    [sg.Button('Check No Deadlock', key='btnDeadlock', disabled=True),
     sg.Text("Not checked", key='labelDeadlock', text_color='gray', font=font),
     sg.Input('hmm', key="txtDeadlockQuery", visible=False)],

    [sg.Button('Check No Free Executor', key='btnExecutor', disabled=True),
     sg.Text("Not checked", key='labelExecutor', text_color='gray', font=font),
     sg.Input('hmm', key="txtExecutorQuery", visible=False)],

    [sg.Button('Check No Free Monitor', key='btnMonitor', disabled=True),
     sg.Text("Not checked", key='labelMonitor', text_color='gray', font=font),
     sg.Input('hmm', key="txtMonitorQuery", visible=False)],

    [sg.Button('Check No Need Rerouting', key='btnRerouting', disabled=True),
     sg.Text("Not checked", key='labelRerouting', text_color='gray', font=font),
     sg.Input('hmm', key="txtReroutingQuery", visible=False)]

]

settings_layout = [
    [sg.Text("Settings", font=header_font)],
    [sg.Text("UPPAAL Location", font=font)],
     [sg.Input(uppaalLocation, key='uppaalLocation', font=font, enable_events=True),
     sg.FileBrowse(button_text="Browse", font=font, target='uppaalLocation', initial_folder=uppaalLocation)],
    [sg.Text("verifyta Location", font=font)],
     [sg.Input(verifytaLocation, key='verifytaLocation', font=font, enable_events=True),
     sg.FileBrowse(button_text="Browse", font=font, target='verifytaLocation', initial_folder=verifytaLocation)]
]

routings_layout = [
    [sg.Text("Generate routings", font=header_font)],
    [sg.Button('Generate all routings', key='btnGenerateRoutings', disabled=True)]
]

layout = [
    [sg.Column([[sg.Image("ggggg/resources/logo.png")]], justification='center')],
    ## LOAD INSTANCE ##
    [sg.Text('Load Instance', font=header_font)],
    [sg.Input('', key='InstanceFile', enable_events=True, visible=False, font=font),
     sg.FileBrowse(button_text="Load Instance", font=font, initial_folder=deffolder, target='InstanceFile'),
     sg.Text('Instance name:', font=font), sg.Text('n/a', key='labelInstanceName', size=(30,1), font=font)],

    [sep(100)],

    ## INSTANCE DETAILS ##
    [sg.Text('Instance details:', key="labelInstance", text_color='gray', font=header_font)],
    [sg.Text("Hosts:",  text_color='gray', key="labelHosts", font=font), sg.Text('--', key="txtHosts", text_color='gray',font=font),
     sg.Text("VNFs:",  text_color='gray', key="labelVNFs", font=font), sg.Text('--', key="txtVNFs", text_color='gray', font=font),
     sg.Text("Slices:",  text_color='gray', key="labelSlices", font=font), sg.Text('--', key="txtSlices", text_color='gray', font=font),
     sg.Text("User Equipment:",  text_color='gray', key="labelUEs", font=font), sg.Text('--', key="txtUEs", text_color='gray', font=font),
     sg.Text("Links:",  text_color='gray', key="labelLinks", font=font), sg.Text('--', key="txtLinks", text_color='gray', font=font)],

    [sep(100)],

[sg.Text("Executors/Monitors: ", key="labelExecutorMonitor", text_color='gray', font=font),
     sg.Input('2', key='txtExecutors', font=font, size=(4,1), disabled=True),
     sg.Text("Message Queue Length: ", key="labelQueue", text_color='gray', font=font),
     sg.Input('3', key='txtQueue', disabled=True, font=font, size=(4,1))],
    [sg.TabGroup([[sg.Tab('Verification', main_layout),
                   sg.Tab('Routings', routings_layout),
                   sg.Tab('Settings', settings_layout)]],
                       tab_background_color='white',
                       background_color='white',
                       selected_background_color='blue')]]

window = sg.Window('GGGGG', layout)

## Enables widgets and changes text color depending on what stage in the process the user is infd
def set_stage(stage):
    if stage == 1:
        window['labelInstance'].update(text_color=textColor)
        window['labelGenerate'].update(text_color=textColor)

        window['labelHosts'].update(text_color=textColor)
        window['labelVNFs'].update(text_color=textColor)
        window['labelSlices'].update(text_color=textColor)
        window['labelUEs'].update(text_color=textColor)
        window['labelLinks'].update(text_color=textColor)

        window['txtHosts'].update(text_color=textColor)
        window['txtVNFs'].update(text_color=textColor)
        window['txtSlices'].update(text_color=textColor)
        window['txtUEs'].update(text_color=textColor)
        window['txtLinks'].update(text_color=textColor)

        window['labelExecutorMonitor'].update(text_color=textColor)
        window['labelQueue'].update(text_color=textColor)

        window['txtExecutors'].update(disabled=False)
        window['txtQueue'].update(disabled=False)
        window['generateUPPAAL'].update(disabled=False)

        window['btnGenerateRoutings'].update(disabled=False)


        ## Disable stage 2 (in case previously enabled)
        window['Preview'].update(disabled=True)
        window['labelVerify'].update(text_color='gray')
        window['labelDeadlines'].update(text_color='gray')
        window['labelDeadlock'].update(text_color='gray')
        window['labelExecutor'].update(text_color='gray')
        window['labelMonitor'].update(text_color='gray')
        window['labelRerouting'].update(text_color='gray')
 
        window['labelQueues'].update(text_color='gray')
        window['btnDeadlines'].update(disabled=True)
        window['btnDeadlock'].update(disabled=True)
        window['btnExecutor'].update(disabled=True)
        window['btnMonitor'].update(disabled=True)
        window['btnRerouting'].update(disabled=True)
        window['btnQueues'].update(disabled=True)




    if stage == 2:
        window['Preview'].update(disabled=False)
        window['labelVerify'].update(text_color=textColor)
        window['labelDeadlines'].update(text_color=textColor, value="Not Checked")
        window['labelQueues'].update(text_color=textColor, value="Not Checked")
        window['labelDeadlock'].update(text_color=textColor, value="Not Checked")
        window['labelExecutor'].update(text_color=textColor, value="Not Checked")
        window['labelMonitor'].update(text_color=textColor, value="Not Checked")
        window['labelRerouting'].update(text_color=textColor, value = "Not Checked")
        window['btnDeadlines'].update(disabled=False)
        window['btnDeadlock'].update(disabled=False)
        window['btnQueues'].update(disabled=False)
        window['btnExecutor'].update(disabled=False)
        window['btnMonitor'].update(disabled=False)
        window['btnRerouting'].update(disabled=False)



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

def generate_uppaal(infile, executors, queueLength):
    modelName = os.path.splitext(os.path.basename(infile))[0]
    uppaalFile = os.getcwd() + '/models/' + modelName + '.xml'
    sysdict = LoadSystem(infile)
    ToUPPAAL(sysdict, uppaalFile, executors, queueLength)
    queryFileNames = genQueries(sysdict, modelName)
    window['txtDeadlinesQuery'].update(value=queryFileNames[0])
    window['txtQueuesQuery'].update(value=queryFileNames[1])
    window['txtDeadlockQuery'].update(value=queryFileNames[2])
    window['txtExecutorQuery'].update(value=queryFileNames[3])
    window['txtMonitorQuery'].update(value=queryFileNames[4])
    window['txtReroutingQuery'].update(value=queryFileNames[5])
    window['txtUPPAALFile'].update(value=uppaalFile)
    set_stage(2)

def preview(uppaalfile, modelFile):
    currentDir = os.getcwd()
    uppaalDir = os.path.dirname(uppaalfile)
    os.chdir(uppaalDir)
    uppaalCmd = "./uppaal"
    cmd = uppaalCmd + " \"" + modelFile + "\""
    # cmd = "\"" + uppaalCmd + "\"" # \"" //+ str(infile) + "\" \"" + queryfile + "\" > " + "\"" + outputfile + "\""
    os.system(cmd)
    os.chdir(currentDir)


def verify(uppaalfile, query, queryfile):
    outputfile = os.getcwd() + '/tmp/' + 'tmp'
    answers = runUPPAAL(values['verifytaLocation'], uppaalfile, queryfile, outputfile)
    window['label' + query].update(answers[0][1])
    window['btn' + query].update(disabled=True)



while True:
    event, values = window.read()

    ### QUIT ###
    if event == sg.WINDOW_CLOSED or event == 'Quit':
        break

    ### LOAD INSTANCE ###
    elif event == 'InstanceFile':
        load_instance(values['InstanceFile'])

    ### GENERATE MODEL ###
    elif event == 'generateUPPAAL':
        generate_uppaal(values['InstanceFile'], int(values['txtExecutors']), int(values['txtQueue']))

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

    ### VERIFY MONITOR ###
    elif event == 'btnMonitor':
        uppaalfile = values['txtUPPAALFile']
        queryfile = values['txtMonitorQuery']
        verify(uppaalfile, "Monitor", queryfile)

    ### VERIFY REROUTING ###
    elif event == 'btnRerouting':
        uppaalfile = values['txtUPPAALFile']
        queryfile = values['txtReroutingQuery']
        verify(uppaalfile, "Rerouting", queryfile)



    ### GENERATE ROUTINGS ###
    elif event == 'btnGenerateRoutings':
        print("GEN ROUTINGS")

        sysdict = LoadSystem(values['InstanceFile'])
        systems = AllRoutings(sysdict, int(values['txtExecutors']), int(values['txtQueue']))
        print("FOUND ", len(systems), " SYSTEMS")
        modelName = os.path.splitext(os.path.basename(values['InstanceFile']))[0]
        if not os.path.exists('models/' + modelName):
            os.makedirs('models/' + modelName)

        prefix = "models/" + modelName + "/" + modelName
        i = 0
        for s in systems:
            filename = prefix + "_" + str(i) + ".xml"
            f = open(filename, "w")
            f.write(s)
            print("\tWrote file: ", filename)
            i = i + 1


    ### CHANGE UPPAALLOCATION
    elif event == 'uppaalLocation':
        if (values['uppaalLocation'] != ''):
            uppaalLocation = values['uppaalLocation']
            saveConfig()

    ### CHANGE VERIFYTALOCATION
    elif event == 'verifytaLocation':
        if (values['verifytaLocation'] != ''):
            verifytaLocation = values['verifytaLocation']
            saveConfig()

    ### UNRECOGNIZED EVENT ###
    else:
        print("Unrecognized event:", event)

window.close()
