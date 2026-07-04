import httpx
import asyncio
import json
import os
import platform
import zipfile
import subprocess
launcher_name="Ray Launcher"
launcher_version="0.1.0"
player_name="Scorne_"
player_access_token="eyJraWQiOiIwNDkxODEiLCJhbGciOiJSUzI1NiJ9.eyJ4dWlkIjoiMjUzNTQxNjYwNjcyMzkxNyIsImFnZyI6IkFkdWx0Iiwic3ViIjoiMzM2MjI5YzItZDZlMC01Yjg3LTgyNTQtNzE3MjMwZDZkZjZlIiwiYXV0aCI6IlhCT1giLCJucyI6ImRlZmF1bHQiLCJyb2xlcyI6W10sImlzcyI6ImF1dGhlbnRpY2F0aW9uIiwiZmxhZ3MiOlsibXVsdGlwbGF5ZXIiLCJtaW5lY3JhZnRfbmV0Il0sInByb2ZpbGVzIjp7Im1jIjoiN2MwMzZhNmMtY2Q1OS00Y2QwLTljMmMtOWYwYmRlMzQ3MGQ5In0sInBtaWQiOiJmMDlhNDhlYi0wODhhLTUyZTEtYjZkNS00NTIxMzJmMDEwNzMiLCJwbGF0Zm9ybSI6IldFQiIsInRpZCI6IkU5OUIwIiwicGZkIjpbeyJ0eXBlIjoibWMiLCJpZCI6IjdjMDM2YTZjLWNkNTktNGNkMC05YzJjLTlmMGJkZTM0NzBkOSIsIm5hbWUiOiJQcm9mZXNzb3JfX1BhbmljIn1dLCJ4aWQiOiIyNTM1NDE2NjA2NzIzOTE3IiwibmJmIjoxNzgzMTQ4NTQ3LCJleHAiOjE3ODMyMzQ5NDcsImlhdCI6MTc4MzE0ODU0NywiYWlkIjoiN2Q1Yzg0M2ItZmUyNi00NWY3LTkwNzMtYjY4M2IyYWM3ZWMzIn0.Q16rLyiziJ2oiistov8vNeQA828K8oUXIC_iFGMbmjEgz_sJxq-52WYZMFXXhyQ4xD3edcxD4VWNdTn3MJb1LIjKWMuD3bhcgEtDygoTM7H1grugykln3W60ljQz1mOfDYrM-cZFQMWH1x0i8pwKEhvvg_3wMtX-dl03M2VxrKz9TYFAlDANR-PKKeGy7hp1oZE2WFhv4gjgr0AksQzRdM-m9D-hO_6RcZYbRVDI4gcWTJA0L8x_U76eKI0sUEKYVhMV1uZ1WYcDnoWXTSFUuKaZBsA1F9zACPj2wAdDtqKQVSpQ5Yl4RVsP9naCrHRJrfjuwPeT7V-9UsUbR19vrw}"
player_uuid="7c036a6ccd594cd09c2c9f0bde3470d9"
client_id=""
player_xuid=""
download_timeout=60 #After 60 seconds if you aren't getting data stop downloading
dowload_segments=30 #Download 30 segments every time
resolution_width="1920"
resolution_height="1080"
quick_path="Test"
features={
    "is_demo_user":False,
    "has_custom_resolution":True,
    "has_quick_plays_support":True,
    "is_quick_play_singleplayer":True
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
            print("Found Tag")
            return value
    return False
def is_allowed(rules, platform,machine):
    allowed = False
    for rule in rules:
        action = rule["action"] == "allow"
        if "os" not in rule:
            allowed = action
        if "features" in rule:
            return False
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
async def get_segments(client, urls,paths,hashes):
    tasks = [client.get(url) for url in urls]
    results = await asyncio.gather(*tasks)
    for offset, res in enumerate(results):
        res.raise_for_status()
        asset_folder=hashes[offset][0]+hashes[offset][1]
        if(not os.path.exists(f"minecraft/assets/objects/{asset_folder}")):
            os.makedirs(f"minecraft/assets/objects/{asset_folder}")
        with open(f"{paths[offset]}/{hashes[offset]}", "wb") as f:
            f.write(res.content)
async def get_libraries(client, urls,paths,native_path):
    tasks = [client.get(url) for url in urls]
    results = await asyncio.gather(*tasks)
    if not os.path.exists(native_path):
        os.makedirs(native_path)
    for offset, res in enumerate(results):
        res.raise_for_status()
        if(not os.path.exists(f"minecraft/libraries/{os.path.dirname(next(iter(paths[offset].values())))}")):
            os.makedirs(f"minecraft/libraries/{os.path.dirname(next(iter(paths[offset].values())))}")
        with open(f"minecraft/libraries/{next(iter(paths[offset].values()))}", "wb") as f:
            f.write(res.content)
        if "natives-" in (next(iter(paths[offset].keys()))):
            with zipfile.ZipFile(f"minecraft/libraries/{next(iter(paths[offset].values()))}","r") as jar:
                jar.extractall(native_path)
async def DownloadAssets(assets,segments):
    urls=[]
    paths=[]
    hashes=[]
    for _, asset_value in assets.items():
        hash_val=asset_value["hash"]
        asset_folder=hash_val[0]+hash_val[1]
        paths.append(f"minecraft/assets/objects/{asset_folder}")
        urls.append(f"{resource_url}/{asset_folder}/{hash_val}")
        hashes.append(hash_val)
    async with httpx.AsyncClient(timeout=download_timeout) as client:
        for i in range(0, len(urls), segments):
            await get_segments(client, urls[i:i+segments],paths[i:i+segments],hashes[i:i+segments])

async def DownloadLibraries(library_dict,segments,native_path,os_platform,classpath):
    paths=[]
    urls=[]
    #separate Library files into paths and urls
    for lib_key,lib_val in library_dict.items():
        urls.append(lib_key)
        paths.append(lib_val)
    #then download the segments gotten
    async with httpx.AsyncClient(timeout=download_timeout) as client:
        for i in range(0, len(urls), segments):
            await get_libraries(client, urls[i:i+segments],paths[i:i+segments],native_path)

def AddClientPaths(paths,version_id):
    # load all library files and append them to classpath
    for path in paths:
        classpath.append(f"minecraft/libraries/{path}")
    #theres no need to return .append is an inplace function
    classpath.append(f"minecraft/versions/{version_id}/{version_id}.jar")

def DownloadClient(v,version_id):
    #from the client dictionary get the url
    client_url=v["client"]["url"]
    client_response=httpx.get(client_url)
    #If it managed to make a connection write the contents of the client id to the file
    if client_response.status_code==200:
        if(not os.path.exists(f"minecraft/versions/{version_id}")):
            os.makedirs(f"minecraft/versions/{version_id}")
        with open(f"minecraft/versions/{version_id}/{version_id}.jar","wb") as f:
            f.write(client_response.content)  


resource_url="https://resources.download.minecraft.net"
assets_url=""
assets_dict={}
client_dict={}
lib_dict={}
version_id=""
current_platform=platform.system().lower()
current_machine=platform.machine().lower()
jvm_args=[]
game_paths=[]
game_args=[]
classpath=[]
placeholder_tags=[]
assets_index_id=0
print(current_machine)
if current_platform=="darwin":
    current_platform="osx"
print(current_platform)
def RunGame():
    response=httpx.get("https://piston-meta.mojang.com/mc/game/version_manifest_v2.json")
    if response.status_code==200:
        print("Success")
        version_manifest=json.loads(response.content)
        latest_version=version_manifest["latest"]
        versions_list=version_manifest["versions"]
        for version in versions_list:
            if version["type"]=="release" and latest_version["release"]==version["id"]:
                latest_version_url=version["url"]
                version_id=version["id"]
                version_res=httpx.get(latest_version_url)
                if(version_res.status_code==200):
                    version_data=json.loads(version_res.content)
                    if(not os.path.exists(f"minecraft/versions/{version["id"]}")):
                        os.makedirs(f"minecraft/versions/{version["id"]}")
                    with open(f"minecraft/versions/{version["id"]}/{version["id"]}.json","w") as f:
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
                                if(not os.path.exists("minecraft/assets/indexes")):
                                    os.makedirs("minecraft/assets/indexes")
                                with open(f"minecraft/assets/indexes/{v["id"]}.json","w") as f:
                                    json.dump(assets,f,indent=2)
                                assets_dict=assets["objects"]
                                assets_index_id=v["id"]
                        elif k=="libraries":
                            for library in v:
                                #for each library get its url and path
                                lib_url=library["downloads"]["artifact"]["url"]
                                lib_path=library["downloads"]["artifact"]["path"]
                                #first assume that I'm supposed to download this library
                                lib_for_platform=True
                                for lib_key,lib_val in library.items():
                                    #check if a rules dict exists
                                    if lib_key=="rules":
                                        #if it does exist check if the machine is allowed to download that library
                                        if not is_allowed(lib_val,current_platform,current_machine):
                                            #if not set this to false
                                            lib_for_platform=False
                                if(lib_for_platform):
                                    lib_dict[lib_url]={library["name"]:lib_path}
                                    game_paths.append(lib_path)
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
        #DownloadClient(client_dict,version_id,classpath)
        print("Downloaded Client")
        #asyncio.run(DownloadLibraries(lib_dict,50,f"minecraft/versions/{version_id}/natives/",current_platform,classpath))
        print("Downloaded libs")
        #asyncio.run(DownloadAssets(assets_dict,50))
        print("Downloaded Assets")
        AddClientPaths(game_paths,version_id)
        joiner=";"if current_platform=="windows" else ":"
        classpath=joiner.join(classpath)
        placeholder_tags = {
        "${auth_player_name}": player_name,
        "${version_name}": version_id,
        "${game_directory}": "minecraft",
        "${assets_root}": "minecraft/assets",
        "${assets_index_name}": str(assets_index_id),
        "${auth_uuid}": player_uuid,
        "${auth_access_token}": player_access_token,
        "${clientid}": client_id,
        "${auth_xuid}": player_xuid,
        "${version_type}": "release",
        "${launcher_name}": launcher_name,
        "${launcher_version}": launcher_version,
        "${classpath}": classpath,
        "${natives_directory}": f"minecraft/versions/{version_id}/natives/",
        "${resolution_width}":resolution_width,
        "${resolution_height}":resolution_height,
        "${quickPlaySingleplayer}":quick_path
        }
        jvm_args=ParseArgs(jvm_args,placeholder_tags)
        game_args=ParseArgs(game_args,placeholder_tags)
        for argument in game_args:
            print(argument)
        command = [
        "java",
        *jvm_args,
        version_data["mainClass"],
        *game_args
        ]
        return command
subprocess.run(RunGame())