import httpx
import asyncio
import json
import os
import platform
import zipfile
launcher_name="Tedd Launcher"
launcher_version="0.1.0"
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
async def get_segments(client, urls,paths,hashes):
    tasks = [client.get(url) for url in urls]
    results = await asyncio.gather(*tasks)
    for offset, res in enumerate(results):
        res.raise_for_status()
        asset_folder=hashes[offset][0]+hashes[offset][1]
        if(not os.path.exists(f"minecraft/assets/objects/{asset_folder}")):
            os.makedirs(f"minecraft/assets/objects/{asset_folder}")
        if(not os.path.exists(f"{paths[offset]}/{hashes[offset]}")):
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
        if(not os.path.exists(f"minecraft/libraries/{next(iter(paths[offset].values()))}")):
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
    async with httpx.AsyncClient(timeout=5) as client:
        for i in range(0, len(urls), segments):
            await get_segments(client, urls[i:i+segments],paths[i:i+segments],hashes[i:i+segments])

async def DownloadLibraries(library_dict,segments,native_path,os_platform,classpath):
    paths=[]
    urls=[]
    for lib_key,lib_val in library_dict.items():
        urls.append(lib_key)
        paths.append(lib_val)
    for path in paths:
        vals = next(iter(path.values()))
        classpath.append(f"minecraft/libraries/{vals}")
    async with httpx.AsyncClient(timeout=5) as client:
        for i in range(0, len(urls), segments):
            await get_libraries(client, urls[i:i+segments],paths[i:i+segments],native_path)
    return classpath
def DownloadClient(v,version_id,classpath):
    client_url=v["client"]["url"]
    client_response=httpx.get(client_url)
    if client_response.status_code==200:
        if(not os.path.exists(f"minecraft/versions/{version_id}")):
            os.makedirs(f"minecraft/versions/{version_id}")
        if(not os.path.exists(f"minecraft/versions/{version_id}/{version_id}.jar")):
            with open(f"minecraft/versions/{version_id}/{version_id}.jar","wb") as f:
                f.write(client_response.content)
    classpath.append(f"minecraft/versions/{version_id}/{version_id}.jar")
def ParseJVMargs(jvm,launcher_name,launcher_version,native_path,class_path):
    replacements = {
    "${natives_directory}":native_path,
    "${classpath}": class_path,
    "${launcher_name}": launcher_name,
    "${launcher_version}":launcher_version
    }
    for offset,argument in enumerate(jvm):
        for placeholder,value in replacements.items():
            if placeholder in argument:
                jvm[offset]=argument.replace(placeholder,value)
    return jvm
response=httpx.get("https://piston-meta.mojang.com/mc/game/version_manifest_v2.json")
resource_url="https://resources.download.minecraft.net"
assets_url=""
assets_dict={}
client_dict={}
lib_dict={}
version_id=""
current_platform=platform.system().lower()
current_machine=platform.machine().lower()
jvm_args=[]
classpath=[]
print(current_machine)
if current_platform=="darwin":
    current_platform="osx"
print(current_platform)
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
                    elif k=="libraries":
                        for library in v:
                            lib_url=library["downloads"]["artifact"]["url"]
                            lib_path=library["downloads"]["artifact"]["path"]
                            lib_for_platform=True
                            for lib_key,lib_val in library.items():
                                if lib_key=="rules":
                                    if not is_allowed(lib_val,current_platform,current_machine):
                                        lib_for_platform=False
                            if(lib_for_platform):
                                lib_dict[lib_url]={library["name"]:lib_path}
                    elif k=="arguments":
                        for arg_keys,arg_vals in v.items():
                            if arg_keys=="jvm":
                                for argument in arg_vals:
                                    if type(argument)==dict:
                                        if is_allowed(argument["rules"],current_platform,current_machine):
                                            jvm_args.append(argument["value"])
                                    else:
                                        jvm_args.append(argument)
    DownloadClient(client_dict,version_id,classpath)
    #print("Downloaded Client")
    #asyncio.run(DownloadLibraries(lib_dict,10,f"minecraft/versions/{version_id}/natives/",current_platform,classpath))
    #print("Downloaded libs")
    #asyncio.run(DownloadAssets(assets_dict,10))
    #print("Downloaded Assets")
    joiner=";"if current_platform=="windows" else ":"
    classpath=joiner.join(classpath)
    jvm_args=ParseJVMargs(jvm_args,launcher_name,launcher_version,f"minecraft/versions/{version_id}/natives/",classpath)
    for argument in jvm_args:
       print(argument)