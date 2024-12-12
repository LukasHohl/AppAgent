import argparse # argumente
import ast # abstract syntax tree
import json #Datenformat
import os #Betriebssystem
import re # regular expression
import sys #System
import time

import prompts
from config import load_config
from model import OpenAIModel, QwenModel
from utils import print_with_color

# some command line arguments
arg_desc = "AppAgent - Human Demonstration"
parser = argparse.ArgumentParser(formatter_class=argparse.RawDescriptionHelpFormatter, description=arg_desc)
parser.add_argument("--app", required=True)
parser.add_argument("--demo", required=True) # the name of the new file?
parser.add_argument("--root_dir", default="./")
args = vars(parser.parse_args())

configs = load_config() # so this is some kind of dictionary with some values

#I think the following code can be moved into a function, maybe load_config itself
# a model is created given some config data
if configs["MODEL"] == "OpenAI": # for some reason the os.environ are also here, but these are nevery used, maybe they are used elsewhere?
    mllm = OpenAIModel(base_url=configs["OPENAI_API_BASE"],
                       api_key=configs["OPENAI_API_KEY"],
                       model=configs["OPENAI_API_MODEL"],
                       temperature=configs["TEMPERATURE"],
                       max_tokens=configs["MAX_TOKENS"])
elif configs["MODEL"] == "Qwen":
    mllm = QwenModel(api_key=configs["DASHSCOPE_API_KEY"],
                     model=configs["QWEN_MODEL"])
else:
    print_with_color(f"ERROR: Unsupported model type {configs['MODEL']}!", "red")
    sys.exit()
#probably just use chatgpt

#directory for the stuff on the pc
root_dir = args["root_dir"]
work_dir = os.path.join(root_dir, "apps")
if not os.path.exists(work_dir):
    os.mkdir(work_dir)
app = args["app"]
work_dir = os.path.join(work_dir, app) #this just creates a folder in the folder?
demo_dir = os.path.join(work_dir, "demos")
demo_name = args["demo"]
task_dir = os.path.join(demo_dir, demo_name)
xml_dir = os.path.join(task_dir, "xml") #TODO why does not this exist? I see no mkdir?
labeled_ss_dir = os.path.join(task_dir, "labeled_screenshots")
record_path = os.path.join(task_dir, "record.txt")
task_desc_path = os.path.join(task_dir, "task_desc.txt")
if not os.path.exists(task_dir) or not os.path.exists(xml_dir) or not os.path.exists(labeled_ss_dir) \
        or not os.path.exists(record_path) or not os.path.exists(task_desc_path):
    print("Error! Some folders do not exist!") #they are probably created in step_recorder
    #so why are these 2 scripts even separate?
    sys.exit() # TODO this should exit here if I am not totally wrong?
log_path = os.path.join(task_dir, f"log_{app}_{demo_name}.txt")

docs_dir = os.path.join(work_dir, "demo_docs")
if not os.path.exists(docs_dir):
    os.mkdir(docs_dir)

print_with_color(f"Starting to generate documentations for the app {app} based on the demo {demo_name}", "yellow")
doc_count = 0
with open(record_path, "r") as infile:
    step = len(infile.readlines()) - 1 # we go through the lines?
    infile.seek(0) # go to the start of the file
    for i in range(1, step + 1):
        #we open the images
        img_before = os.path.join(labeled_ss_dir, f"{demo_name}_{i}.png")
        img_after = os.path.join(labeled_ss_dir, f"{demo_name}_{i + 1}.png")
        rec = infile.readline().strip() # read the line without space stuff
        action, resource_id = rec.split(":::") # read action and resource_id
        action_type = action.split("(")[0] # get the action
        action_param = re.findall(r"\((.*?)\)", action)[0] #? is for as few as possible
        #this just includes the number of the text in a string
        #this could be written a lot shorter, not really, a little bit
        if action_type == "tap":
            prompt_template = prompts.tap_doc_template
            prompt = re.sub(r"<ui_element>", action_param, prompt_template)
        elif action_type == "text":
            input_area, input_text = action_param.split(":sep:")
            prompt_template = prompts.text_doc_template
            prompt = re.sub(r"<ui_element>", input_area, prompt_template)
        elif action_type == "long_press":
            prompt_template = prompts.long_press_doc_template
            prompt = re.sub(r"<ui_element>", action_param, prompt_template)
        elif action_type == "swipe":
            swipe_area, swipe_dir = action_param.split(":sep:")
            if swipe_dir == "up" or swipe_dir == "down":
                action_type = "v_swipe"
            elif swipe_dir == "left" or swipe_dir == "right":
                action_type = "h_swipe"
            prompt_template = prompts.swipe_doc_template
            prompt = re.sub(r"<swipe_dir>", swipe_dir, prompt_template)
            prompt = re.sub(r"<ui_element>", swipe_area, prompt)
        else:
            break
        task_desc = open(task_desc_path, "r").read()
        prompt = re.sub(r"<task_desc>", task_desc, prompt)
        # so far we wrote down the number of the ui element and some extra info for the task the human let the PC do

        #i guess now we create some new file or something
        doc_name = resource_id + ".txt"
        doc_path = os.path.join(docs_dir, doc_name)

        if os.path.exists(doc_path):
            doc_content = ast.literal_eval(open(doc_path).read()) # safely evaluates this a python literal
            if doc_content[action_type]:
                if configs["DOC_REFINE"]:
                    suffix = re.sub(r"<old_doc>", doc_content[action_type], prompts.refine_doc_suffix)
                    prompt += suffix
                    print_with_color(f"Documentation for the element {resource_id} already exists. The doc will be "
                                     f"refined based on the latest demo.", "yellow")
                else:
                    print_with_color(f"Documentation for the element {resource_id} already exists. Turn on DOC_REFINE "
                                     f"in the config file if needed.", "yellow")
                    continue
        else:
            doc_content = {
                "tap": "",
                "text": "",
                "v_swipe": "",
                "h_swipe": "",
                "long_press": ""
            }
        #so we basically write down what using an action on a specific UI element does 
        #I like this idea, but we will have a problem if the ID changes

        #so we give the old documentation of the action, the new action that was taken and the before and after images
        #to the LLM to give us a documentation. It was asked to use 2-3 short sentences and avoid the element index (0,1,2,...)
        print_with_color(f"Waiting for GPT-4V to generate documentation for the element {resource_id}", "yellow")
        status, rsp = mllm.get_model_response(prompt, [img_before, img_after])
        if status:
            doc_content[action_type] = rsp
            with open(log_path, "a") as logfile:
                log_item = {"step": i, "prompt": prompt, "image_before": f"{demo_name}_{i}.png",
                            "image_after": f"{demo_name}_{i + 1}.png", "response": rsp}
                logfile.write(json.dumps(log_item) + "\n")
            with open(doc_path, "w") as outfile:
                outfile.write(str(doc_content))
            doc_count += 1
            print_with_color(f"Documentation generated and saved to {doc_path}", "yellow")
        else:
            print_with_color(rsp, "red")
        time.sleep(configs["REQUEST_INTERVAL"])

print_with_color(f"Documentation generation phase completed. {doc_count} docs generated.", "yellow")
#so they even use LLM to generate documentation. BUT There seem some cost problems here.
