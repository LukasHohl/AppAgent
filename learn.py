import argparse
import datetime
import os
import time

from scripts.utils import print_with_color

#start explanation
#arg_desc is the help message (--help)
#argparse.ArgumentParser parses the commandline arguments/does the hard work
#formatter_class is just the formatting of the help message
#description the content of the help message
# add_argument obviously adds commandline arguments for the ArgumentParser
#parse_args() does the stuff, the datatype is Namespace so vars is needed to convert that to a dictionary
arg_desc = "AppAgent - exploration phase"
parser = argparse.ArgumentParser(formatter_class=argparse.RawDescriptionHelpFormatter, description=arg_desc)
parser.add_argument("--app")
parser.add_argument("--root_dir", default="./")
args = vars(parser.parse_args())

# save the commandline arguments in variables
app = args["app"]
root_dir = args["root_dir"]

# just some fancy printing with color, does not work with cmd
print_with_color("Welcome to the exploration phase of AppAgent!\nThe exploration phase aims at generating "
                 "documentations for UI elements through either autonomous exploration or human demonstration. "
                 "Both options are task-oriented, which means you need to give a task description. During "
                 "autonomous exploration, the agent will try to complete the task by interacting with possible "
                 "elements on the UI within limited rounds. Documentations will be generated during the process of "
                 "interacting with the correct elements to proceed with the task. Human demonstration relies on "
                 "the user to show the agent how to complete the given task, and the agent will generate "
                 "documentations for the elements interacted during the human demo. To start, please enter the "
                 "main interface of the app on your phone.", "yellow")
print_with_color("Choose from the following modes:\n1. autonomous exploration\n2. human demonstration\n"
                 "Type 1 or 2.", "blue")

#gets the user input until it is either "1" or "2"
user_input = ""
while user_input != "1" and user_input != "2":
    user_input = input()

#I do not know with required=True this should not be neccessary
#additionally what happens if the name of the app is wrong
#Todo
if not app:
    print_with_color("What is the name of the target app?", "blue")
    app = input()
    app = app.replace(" ", "")

#führt befehl aus und gibt Rückgabewert zurück, potenzielle Sicherheitslücke, wenn Program mehr rechte hat als nutzer
if user_input == "1":
    os.system(f"python scripts/self_explorer.py --app {app} --root_dir {root_dir}")
else:
#first get time in seconds since 1970, convert to int because we only care about whole seconds?
#then generate a datetime, get a string from that datetime
#this can lead to problems if I understand it correctly if the file already exists, because not enough time since last file was created
    demo_timestamp = int(time.time())
    demo_name = datetime.datetime.fromtimestamp(demo_timestamp).strftime(f"demo_{app}_%Y-%m-%d_%H-%M-%S")
    os.system(f"python scripts/step_recorder.py --app {app} --demo {demo_name} --root_dir {root_dir}")
    os.system(f"python scripts/document_generation.py --app {app} --demo {demo_name} --root_dir {root_dir}")
