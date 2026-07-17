import httpx
import asyncio
import json
import os
import platform
import zipfile
import subprocess
import instancer
from logger import *
from mc_validator import *
launcher_name="Ray Launcher"
launcher_version="0.1.0"
player_bearer_token="eyJraWQiOiIwNDkxODEiLCJhbGciOiJSUzI1NiJ9.eyJ4dWlkIjoiMjUzNTQxNjYwNjcyMzkxNyIsImFnZyI6IkFkdWx0Iiwic3ViIjoiMzM2MjI5YzItZDZlMC01Yjg3LTgyNTQtNzE3MjMwZDZkZjZlIiwiYXV0aCI6IlhCT1giLCJucyI6ImRlZmF1bHQiLCJyb2xlcyI6W10sImlzcyI6ImF1dGhlbnRpY2F0aW9uIiwiZmxhZ3MiOlsibWluZWNyYWZ0X25ldCIsIm11bHRpcGxheWVyIl0sInByb2ZpbGVzIjp7Im1jIjoiN2MwMzZhNmMtY2Q1OS00Y2QwLTljMmMtOWYwYmRlMzQ3MGQ5In0sInBtaWQiOiI1MmU3ZDZkMy1hMzk3LTU0ZWYtYTUwYy1mZWFhYTZhZWU2NzYiLCJwbGF0Zm9ybSI6IldFQiIsInRpZCI6IkU5OUIwIiwicGZkIjpbeyJ0eXBlIjoibWMiLCJpZCI6IjdjMDM2YTZjLWNkNTktNGNkMC05YzJjLTlmMGJkZTM0NzBkOSIsIm5hbWUiOiJTY29ybmVfIn1dLCJ4aWQiOiIyNTM1NDE2NjA2NzIzOTE3IiwibmJmIjoxNzg0MjQ1NDE4LCJleHAiOjE3ODQzMzE4MTgsImlhdCI6MTc4NDI0NTQxOCwiYWlkIjoiN2Q1Yzg0M2ItZmUyNi00NWY3LTkwNzMtYjY4M2IyYWM3ZWMzIn0.ZtLg0Oo7-KQVHDljTkFmziAMeWbN3fzm2j1AQZG7hYnJz8J8k9zZ217aVvEHcuGg5IxXQYXQKUPpgxfzkbBcNb4mxt_bBSxNSVQ9Ye9u1D8wfSHLamCl-HacKNI9_t7-y90NiBaboINO7QkZd2XP4Sc_UzkziTrn8GIbgmANsS-V3nJtCq4LjmmBR_jyqtaufZnk_6RMmXzDqC_4ezhirc7GRwbvUgR5iCsSWw2KECykqU3aI2UoPgA50L_w2DnLPThrpuyPnEz59THBNmk8PsQUVyA5kQ9x17nEVAOMSLL3LyiFdAE6PkyTQ9ISnNmpGr4Dk_m11gAOuU8SAQpl8w"
player_name=get_name_from_token(player_bearer_token)
player_uuid=get_uuid_from_token(player_bearer_token)
client_id="00000000402b5328"
player_xuid=get_xuid_from_token(player_bearer_token)
download_timeout=60 #After 60 seconds if you aren't getting data stop downloading
dowload_segments=30 #Download 30 segments every time
resolution_width="1920"
resolution_height="1080"
quick_path="Test"
features={
    "is_demo_user":False,
    "has_custom_resolution":True,
    "has_quick_plays_support":True,
    "is_quick_play_singleplayer":False
}
def ParseArgs(jvm,placeholder_tags):
    #in both java and game args check if the tag exists in the argument
    for offset,argument in enumerate(jvm):
        for tag,value in placeholder_tags.items():
            #if it does exist replace it with the actual value
            if tag in argument:
                jvm[offset]=argument.replace(tag,value)
    return jvm
def IsApplicableFeature(argument,placeholder_tags):
    #in both java and game args check if the tag exists in the argument
    for tag,value in placeholder_tags.items():
        #if it does exist replace it with the actual value
        if tag in argument:
            return value
    return False
def is_allowed(rules, platform,machine):
    allowed = False
    for rule in rules:
        action = rule["action"] == "allow"
        if "os" not in rule:
            allowed = action
        elif rule["os"].get("name") == platform:
            allowed = action
        elif rule["os"].get("arch") == machine:
            allowed=action
    return allowed
def FeatureParse(argument,placeholder_tags):
    for rule in argument["rules"]:
        if "features" in rule:
            for feature in rule["features"]:
                accFeat=IsApplicableFeature(feature,placeholder_tags)
                return accFeat
async def get_segments(client, urls,paths,hashes,instance):
    tasks = [client.get(url) for url in urls]
    results = await asyncio.gather(*tasks)
    for offset, res in enumerate(results):
        res.raise_for_status()
        asset_folder=hashes[offset][0]+hashes[offset][1]
        if(not os.path.exists(f"instances/{instance}/minecraft/assets/objects/{asset_folder}")):
            os.makedirs(f"instances/{instance}/minecraft/assets/objects/{asset_folder}")
        with open(f"{paths[offset]}/{hashes[offset]}", "wb") as f:
            f.write(res.content)
async def get_libraries(client, urls,paths,instance,native_path):
    tasks = [client.get(url) for url in urls]
    results = await asyncio.gather(*tasks)
    if not os.path.exists(native_path):
        os.makedirs(native_path)
    for offset, res in enumerate(results):
        res.raise_for_status()
        if(not os.path.exists(f"instances/{instance}/minecraft/libraries/{os.path.dirname(next(iter(paths[offset].values())))}")):
            os.makedirs(f"instances/{instance}/minecraft/libraries/{os.path.dirname(next(iter(paths[offset].values())))}")
        with open(f"instances/{instance}/minecraft/libraries/{next(iter(paths[offset].values()))}", "wb") as f:
            f.write(res.content)
        if "natives-" in (next(iter(paths[offset].keys()))):
            with zipfile.ZipFile(f"instances/{instance}/minecraft/libraries/{next(iter(paths[offset].values()))}","r") as jar:
                jar.extractall(native_path)
async def DownloadAssets(assets,segments,instance):
    urls=[]
    paths=[]
    hashes=[]
    for _, asset_value in assets.items():
        hash_val=asset_value["hash"]
        asset_folder=hash_val[0]+hash_val[1]
        paths.append(f"instances/{instance}/minecraft/assets/objects/{asset_folder}")
        urls.append(f"{resource_url}/{asset_folder}/{hash_val}")
        hashes.append(hash_val)
    async with httpx.AsyncClient(timeout=download_timeout) as client:
        for i in range(0, len(urls), segments):
            await get_segments(client, urls[i:i+segments],paths[i:i+segments],hashes[i:i+segments],instance)

async def DownloadLibraries(library_dict,segments,native_path,instance):
    paths=[]
    urls=[]
    #separate Library files into paths and urls
    for lib_key,lib_val in library_dict.items():
        urls.append(lib_key)
        paths.append(lib_val)
    #then download the segments gotten
    async with httpx.AsyncClient(timeout=download_timeout) as client:
        for i in range(0, len(urls), segments):
            await get_libraries(client, urls[i:i+segments],paths[i:i+segments],instance,native_path)

def AddClientPaths(paths,instance,version_tag,classpath):
    # load all library files and append them to classpath
    for path in paths:
        classpath.append(f"instances/{instance}/minecraft/libraries/{path}")
    #theres no need to return .append is an inplace function
    classpath.append(f"instances/{instance}/minecraft/versions/{version_tag}/{version_tag}.jar")

def DownloadClient(v,instance,version_tag):
    #from the client dictionary get the url
    client_url=v["client"]["url"]
    client_response=httpx.get(client_url)
    #If it managed to make a connection write the contents of the client id to the file
    if client_response.status_code==200:
        if(not os.path.exists(f"instances/{instance}/minecraft/versions/{version_tag}")):
            os.makedirs(f"instances/{instance}/minecraft/versions/{version_tag}")
        with open(f"instances/{instance}/minecraft/versions/{version_tag}/{version_tag}.jar","wb") as f:
            f.write(client_response.content)  


resource_url="https://resources.download.minecraft.net"
current_platform=platform.system().lower()
current_machine=platform.machine().lower()

assets_index_id=0
DebugLog(LogLevel.LOG_INFO,f"Current Machine: {current_machine}")
if current_platform=="darwin":
    current_platform="osx"
DebugLog(LogLevel.LOG_INFO,f"Current Platform: {current_platform}")
def DownloadGame(instance,version_tag):
    jvm_args=[]
    game_paths=[]
    game_args=[]
    classpath=[]
    placeholder_tags=[]
    assets_url=""
    assets_dict={}
    client_dict={}
    lib_dict={}
    version_manifest_url="https://piston-meta.mojang.com/mc/game/version_manifest_v2.json"
    download_files=True
    if not os.path.exists(f"instances/{instance}"):
        download_files=True
    else:
        download_files=False
    response=httpx.get(version_manifest_url)
    if response.status_code==200:
        DebugLog(LogLevel.LOG_INFO,f"Successfully accessed Version Manifest at {version_manifest_url}")
        version_manifest=json.loads(response.content)
        versions_list=version_manifest["versions"]
        for version in versions_list:
            if version_tag==version["id"]:
                version_url=version["url"]
                version_res=httpx.get(version_url)
                if(version_res.status_code==200):
                    version_data=json.loads(version_res.content)
                    if(not os.path.exists(f"instances/{instance}/minecraft/versions/{version["id"]}")):
                        os.makedirs(f"instances/{instance}/minecraft/versions/{version["id"]}")
                    with open(f"instances/{instance}/minecraft/versions/{version["id"]}/{version["id"]}.json","w") as f:
                        json.dump(version_data,f,indent=2)
                    for k,v in version_data.items():
                        if k=="downloads":
                            #If the key is downloads save the client dictionary
                            client_dict=v
                        elif k=="assetIndex":
                            assets_url=v["url"]
                            asset_response=httpx.get(assets_url)
                            if(asset_response.status_code==200):
                                assets=json.loads(asset_response.content)
                                if(not os.path.exists(f"instances/{instance}/minecraft/assets/indexes")):
                                    os.makedirs(f"instances/{instance}/minecraft/assets/indexes")
                                with open(f"instances/{instance}/minecraft/assets/indexes/{v["id"]}.json","w") as f:
                                    json.dump(assets,f,indent=2)
                                assets_dict=assets["objects"]
                                assets_index_id=v["id"]
                        elif k == "libraries":
                                for library in v:
                                    lib_for_platform = True

                                    if "rules" in library:
                                        lib_for_platform = is_allowed(
                                            library["rules"],
                                            current_platform,
                                            current_machine
                                        )

                                    if not lib_for_platform:
                                        continue

                                    downloads = library.get("downloads", {})

                                    # Normal library jar
                                    if "artifact" in downloads:
                                        artifact = downloads["artifact"]
                                        lib_url = artifact["url"]
                                        lib_path = artifact["path"]

                                        lib_dict[lib_url] = {library["name"]: lib_path}
                                        game_paths.append(lib_path)

                                    # Old-style native jars inside classifiers
                                    if "natives" in library and "classifiers" in downloads:
                                        native_key = library["natives"].get(current_platform)

                                        if native_key:
                                            native = downloads["classifiers"].get(native_key)

                                            if native:
                                                native_url = native["url"]
                                                native_path = native["path"]

                                                lib_dict[native_url] = {f"{library['name']}:{native_key}": native_path}
                        elif k=="arguments":
                            for arg_keys,arg_vals in v.items():
                                if arg_keys=="jvm" or arg_keys=="game":
                                    for argument in arg_vals:
                                        if type(argument)==dict:
                                            if FeatureParse(argument,features):
                                                value=argument["value"]
                                                if isinstance(value, list):
                                                    if(arg_keys=="jvm"):
                                                        jvm_args.extend(value)
                                                    else:
                                                        game_args.extend(value)
                                                else:
                                                    if(arg_keys=="jvm"):
                                                        jvm_args.append(value)
                                                    else:
                                                        game_args.append(value)
                                        else:
                                            if(arg_keys=="jvm"):
                                                jvm_args.append(argument)
                                            else:
                                                game_args.append(argument)
        if download_files:
            DebugLog(LogLevel.LOG_INFO,f"No instance found with name:{instance}")
            DownloadClient(client_dict,instance,version_tag)
            DebugLog(LogLevel.LOG_INFO,"Successfully downloaded the client.jar")
            asyncio.run(DownloadLibraries(lib_dict,dowload_segments,f"instances/{instance}/minecraft/versions/{version_tag}/natives/",instance))
            DebugLog(LogLevel.LOG_INFO,"Downloaded the library files")
            asyncio.run(DownloadAssets(assets_dict,dowload_segments,instance))
            DebugLog(LogLevel.LOG_INFO,"Successfully downloaded the asset files")
        else:
            DebugLog(LogLevel.LOG_INFO,f"An instance with name \"{instance}\" has been found.Skipping Download ")
        AddClientPaths(game_paths,instance,version_tag,classpath)
        joiner=";"if current_platform=="windows" else ":"
        classpath=joiner.join(classpath)
        placeholder_tags = {
        "${auth_player_name}": player_name,
        "${version_name}": version_tag,
        "${game_directory}": f"instances/{instance}/minecraft",
        "${assets_root}": f"instances/{instance}/minecraft/assets",
        "${game_assets}": f"instances/{instance}/minecraft/assets",
        "${assets_index_name}": str(assets_index_id),
        "${auth_uuid}": player_uuid,
        "${auth_access_token}": player_bearer_token,
        "${auth_session}": player_bearer_token,
        "${clientid}": client_id,
        "${auth_xuid}": player_xuid,
        "${version_type}": "release",
        "${launcher_name}": launcher_name,
        "${launcher_version}": launcher_version,
        "${classpath}": classpath,
        "${natives_directory}": f"instances/{instance}/minecraft/versions/{version_tag}/natives/",
        "${resolution_width}":resolution_width,
        "${resolution_height}":resolution_height,
        "${quickPlaySingleplayer}":quick_path,
        "${user_type}": "msa",
        "${user_properties}": "{}"
        }
        jvm_args=ParseArgs(jvm_args,placeholder_tags)
        game_args=ParseArgs(game_args,placeholder_tags)
        command = [
        "java",
        *jvm_args,
        version_data["mainClass"],
        *game_args
        ]
        Save_data={}
        Save_data["Version"]=version_tag
        Save_data["Java Command"]=command
        instancer.WriteToInstance(instance,Save_data)
        DebugLog(LogLevel.LOG_INFO,f"Saved \"{instance}\" data to instances.json")
def LoadGame(instance):
    if(os.path.exists("instances.json")):
        with open("instances.json","r") as f:
            instances_data=json.load(f)
            if instance in instances_data["instances"]:
                command=instances_data["instances"][instance]
                return command["Java Command"]
            else:
                DebugLog(LogLevel.LOG_WARNING,f"The Provided Instance \"{instance}\" is not in instances.json")
                return ""
    else:
        DebugLog(LogLevel.LOG_WARNING,f"instances.json not found")
        return ""
def RunGame(instance):
    java_command=LoadGame(instance)
    print(java_command)
    if java_command!="":
        subprocess.run(java_command)
DownloadGame("New Days","1.21.11")
RunGame("New Days")