import argparse
import datetime

import cv2
import os
import shutil
import sys
import time

from and_controller import list_all_devices, AndroidController, traverse_tree
from config import load_config
from utils import print_with_color, draw_bbox_multi

#commandline argument stuff
arg_desc = "AppAgent - Human Demonstration"
parser = argparse.ArgumentParser(formatter_class=argparse.RawDescriptionHelpFormatter, description=arg_desc)
parser.add_argument("--app")
parser.add_argument("--demo")
parser.add_argument("--root_dir", default="./")
args = vars(parser.parse_args())

app = args["app"]
demo_name = args["demo"]
root_dir = args["root_dir"]

#config also does not use os.environ here
configs = load_config()

#we need an appname, probably for adb
if not app:
    print_with_color("What is the name of the app you are going to demo?", "blue")
    app = input()
    app = app.replace(" ", "")
# we need a name for the file that save all the stuff time is nice, as time does not tend to repeat itself as long as the system clock works
if not demo_name:
    demo_timestamp = int(time.time())
    demo_name = datetime.datetime.fromtimestamp(demo_timestamp).strftime(f"demo_{app}_%Y-%m-%d_%H-%M-%S")

#path to xml that represents the UI at a point in time and the before and after screenshots
work_dir = os.path.join(root_dir, "apps") #joins two paths probably uses / or something
#create directory if it does not already exist
if not os.path.exists(work_dir):
    os.mkdir(work_dir)
work_dir = os.path.join(work_dir, app)
if not os.path.exists(work_dir):
    os.mkdir(work_dir)
#here the files are saved?
demo_dir = os.path.join(work_dir, "demos")
if not os.path.exists(demo_dir):
    os.mkdir(demo_dir)
# so what does this do?
task_dir = os.path.join(demo_dir, demo_name)
if os.path.exists(task_dir):
    shutil.rmtree(task_dir) #if the directory exists it and all its contents are removed
os.mkdir(task_dir)
#Question: why the f does not any of these directories exist?
#Answere: This seems to be the script for manual demonstrations, I never used that so nothing
#exists here
raw_ss_dir = os.path.join(task_dir, "raw_screenshots")
os.mkdir(raw_ss_dir)
xml_dir = os.path.join(task_dir, "xml")
os.mkdir(xml_dir)
labeled_ss_dir = os.path.join(task_dir, "labeled_screenshots")
os.mkdir(labeled_ss_dir)
record_path = os.path.join(task_dir, "record.txt")
record_file = open(record_path, "w")
task_desc_path = os.path.join(task_dir, "task_desc.txt")

#bis hier wurden sehr viele directories erstellt und argumente geparst

#here we get a list of all devices, for some reason the official adb library is not used
device_list = list_all_devices()
if not device_list: # empty lists seem to be converted to false
    print_with_color("ERROR: No device found!", "red")
    sys.exit()
print_with_color("List of devices attached:\n" + str(device_list), "yellow")
if len(device_list) == 1:
    device = device_list[0]
    print_with_color(f"Device selected: {device}", "yellow")
else:
    print_with_color("Please choose the Android device to start demo by entering its ID:", "blue")
    device = input() #this can crash the program
controller = AndroidController(device)
width, height = controller.get_device_size()
if not width and not height: #should not this be an or?
    print_with_color("ERROR: Invalid device size!", "red")
    sys.exit()
print_with_color(f"Screen resolution of {device}: {width}x{height}", "yellow")

print_with_color("Please state the goal of your following demo actions clearly, e.g. send a message to John", "blue")
task_desc = input()
#writes down the task description
with open(task_desc_path, "w") as f:
    f.write(task_desc)
# also in einem Ordner wird die task description aufgeschrieben
#wait, when did this happen?
print_with_color("All interactive elements on the screen are labeled with red and blue numeric tags. Elements "
                 "labeled with red tags are clickable elements; elements labeled with blue tags are scrollable "
                 "elements.", "blue")
#maybe in the next loop it happens?

step = 0 # we save stuff for each step a screenshot and an xml?
while True: # there are break conditions what are they?
    step += 1
    #a screenshot is saved and captured
    screenshot_path = controller.get_screenshot(f"{demo_name}_{step}", raw_ss_dir)
    # xml is saved and captured
    xml_path = controller.get_xml(f"{demo_name}_{step}", xml_dir)
    if screenshot_path == "ERROR" or xml_path == "ERROR":
        break # if one of these files could not be obtained this ends
    #next the xml file is traversed to get all clickable or focusable items (What about scrollable?)
    clickable_list = []
    focusable_list = []
    traverse_tree(xml_path, clickable_list, "clickable", True)
    traverse_tree(xml_path, focusable_list, "focusable", True)
    elem_list = clickable_list.copy() # why are we copying the clickables?
    for elem in focusable_list:
        bbox = elem.bbox
        center = (bbox[0][0] + bbox[1][0]) // 2, (bbox[0][1] + bbox[1][1]) // 2 # we take all focusable centers
        # and compare the distance to the clickable centers
        close = False #what is this?
        for e in clickable_list:
            bbox = e.bbox
            center_ = (bbox[0][0] + bbox[1][0]) // 2, (bbox[0][1] + bbox[1][1]) // 2
            dist = (abs(center[0] - center_[0]) ** 2 + abs(center[1] - center_[1]) ** 2) ** 0.5
            if dist <= configs["MIN_DIST"]:
                close = True
                break
        if not close:
            elem_list.append(elem)
            #so if I understand this correctly we are append all focusable to the clickable list that are not too close to
            # a clickable
            #so here the labled image is created
    labeled_img = draw_bbox_multi(screenshot_path, os.path.join(labeled_ss_dir, f"{demo_name}_{step}.png"), elem_list,
                                  True)
    cv2.imshow("image", labeled_img) #here the image is showed
    print("Press any key while selecting the image to continue.")
    cv2.waitKey(0) # super nothing indicates this you should print something
    cv2.destroyAllWindows()
    #now get the input in text form from the user
    user_input = "xxx"
    print_with_color("Choose one of the following actions you want to perform on the current screen:\ntap, text, long "
                     "press, swipe, stop", "blue")
    #list der erlaubten aktionen, die könnte man doch in eine Liste schreiben, hier ist das so umständlich
    while user_input.lower() != "tap" and user_input.lower() != "text" and user_input.lower() != "long press" \
            and user_input.lower() != "swipe" and user_input.lower() != "stop":
        user_input = input()
    #hier wird für einen tap das Ziel ausgewählt
    if user_input.lower() == "tap":
        print_with_color(f"Which element do you want to tap? Choose a numeric tag from 1 to {len(elem_list)}:", "blue")
        user_input = "xxx"
        while not user_input.isnumeric() or int(user_input) > len(elem_list) or int(user_input) < 1:
            user_input = input()
        #definitely a case of code duplication
        tl, br = elem_list[int(user_input) - 1].bbox
        x, y = (tl[0] + br[0]) // 2, (tl[1] + br[1]) // 2
        ret = controller.tap(x, y)
        if ret == "ERROR":
            print_with_color("ERROR: tap execution failed", "red")
            break
        record_file.write(f"tap({int(user_input)}):::{elem_list[int(user_input) - 1].uid}\n")
        #where is this record file?
        #probably this has to be closed first before it is in the file
    elif user_input.lower() == "text":
        print_with_color(f"Which element do you want to input the text string? Choose a numeric tag from 1 to "
                         f"{len(elem_list)}:", "blue")
        input_area = "xxx"
        while not input_area.isnumeric() or int(input_area) > len(elem_list) or int(input_area) < 1:
            input_area = input()
        print_with_color("Enter your input text below:", "blue")
        user_input = ""
        while not user_input:
            user_input = input()
        controller.text(user_input)
        record_file.write(f"text({input_area}:sep:\"{user_input}\"):::{elem_list[int(input_area) - 1].uid}\n")
    elif user_input.lower() == "long press":
        print_with_color(f"Which element do you want to long press? Choose a numeric tag from 1 to {len(elem_list)}:",
                         "blue")
        user_input = "xxx"
        while not user_input.isnumeric() or int(user_input) > len(elem_list) or int(user_input) < 1:
            user_input = input()
        tl, br = elem_list[int(user_input) - 1].bbox
        x, y = (tl[0] + br[0]) // 2, (tl[1] + br[1]) // 2
        ret = controller.long_press(x, y)
        if ret == "ERROR":
            print_with_color("ERROR: long press execution failed", "red")
            break
        record_file.write(f"long_press({int(user_input)}):::{elem_list[int(user_input) - 1].uid}\n")
    elif user_input.lower() == "swipe":
        print_with_color(f"What is the direction of your swipe? Choose one from the following options:\nup, down, left,"
                         f" right", "blue")
        user_input = ""
        while user_input != "up" and user_input != "down" and user_input != "left" and user_input != "right":
            user_input = input()
        swipe_dir = user_input
        print_with_color(f"Which element do you want to swipe? Choose a numeric tag from 1 to {len(elem_list)}:")
        while not user_input.isnumeric() or int(user_input) > len(elem_list) or int(user_input) < 1:
            user_input = input()
        tl, br = elem_list[int(user_input) - 1].bbox
        x, y = (tl[0] + br[0]) // 2, (tl[1] + br[1]) // 2
        ret = controller.swipe(x, y, swipe_dir)
        if ret == "ERROR":
            print_with_color("ERROR: swipe execution failed", "red")
            break
        record_file.write(f"swipe({int(user_input)}:sep:{swipe_dir}):::{elem_list[int(user_input) - 1].uid}\n")
    elif user_input.lower() == "stop":
        record_file.write("stop\n")
        record_file.close()
        break
    else:
        break
    time.sleep(3)
    #input end and for some reason for 3 second this sleeps
    #next document geneartion is called, why not in 1 script? this is strange.

print_with_color(f"Demonstration phase completed. {step} steps were recorded.", "yellow")
