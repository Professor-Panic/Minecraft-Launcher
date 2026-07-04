import json
import os
x=input("Enter Instance Name")
current_instance_id=0
instance_data={
    "current_instances":0
}
if not os.path.exists("instances.json"):
    with open("instances.json","w") as f:
        instance_data["instances"]={}
        instance_data["instances"][x]={}
        instance_data["current_instances"]=1
        json.dump(instance_data,f,indent=4)
else:
    try:
        with open("instances.json") as f:
            instance_data = json.load(f)
        instance_data["current_instances"]+=1
        instance_data["instances"][x]={}
        with open("instances.json","w") as f:
            json.dump(instance_data,f,indent=4)
    except json.JSONDecodbeError:
        # Fallback if file contains invalid JSON
        instance_data = {}