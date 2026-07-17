import json
import os


def WriteToInstance(instance,data):
    if not os.path.exists("instances.json"):
        with open("instances.json","w") as f:
            instance_data={
                "current_instances":0
            }
            instance_data["instances"]={}
            instance_data["instances"][instance]=data
            instance_data["current_instances"]=1
            json.dump(instance_data,f,indent=4)
    else:
        try:
            with open("instances.json") as f:
                instance_data = json.load(f)
            instance_data["current_instances"]+=1
            instance_data["instances"][instance]=data
            with open("instances.json","w") as f:
                json.dump(instance_data,f,indent=4)
        except json.JSONDecodbeError:
            # Fallback if file contains invalid JSON
            instance_data = {}