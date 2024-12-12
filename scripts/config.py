import os
import yaml


def load_config(config_path="./config.yaml"):
    configs = dict(os.environ)
    with open(config_path, "r") as file: # with closes file even if exception occurs
        yaml_data = yaml.safe_load(file)
    configs.update(yaml_data) # all keys in configs that are in yaml_data will be overwritten
    return configs
