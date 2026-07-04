import httpx
import asyncio
import json
import os
import platform
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
        f.close()
        print("Done")

async def DownloadAssets(assets,segments):
    urls=[]
    paths=[]
    hashes=[]
    for _,asset_value,in assets.items():
        hash_val=asset_value["hash"]
        asset_folder=hash_val[0]+hash_val[1]
        paths.append(f"minecraft/assets/objects/{asset_folder}")
        urls.append(f"{resource_url}/{asset_folder}/{hash_val}")
        hashes.append(hash_val)
    async with httpx.AsyncClient(timeout=5) as client:
        for i in range(0, len(urls), segments):
            await get_segments(client, urls[i:i+segments],paths[i:i+segments],hashes[i:i+segments])
def DownloadClient(v):
    client_url=v["client"]["url"]
    client_response=httpx.get(client_url)
    if client_response.status_code==200:
        if(not os.path.exists("test")):
            os.makedirs("test")
        with open("test/client.jar","wb") as f:
            f.write(client_response.content)
        f.close()
    
response=httpx.get("https://piston-meta.mojang.com/mc/game/version_manifest_v2.json")
resource_url="https://resources.download.minecraft.net/"
assets_url=""
assets_dict={}
client_dict={}
if response.status_code==200:
    print("Success")
    version_manifest=json.loads(response.content)
    latest_version=version_manifest["latest"]
    versions_list=version_manifest["versions"]
    for version in versions_list:
        if version["type"]=="release" and latest_version["release"]==version["id"]:
            latest_version_url=version["url"]
            version_res=httpx.get(latest_version_url)
            if(version_res.status_code==200):
                version_data=json.loads(version_res.content)
                for k,v in version_data.items():
                    if k=="downloads":
                        client_dict=v
                    elif k=="assetIndex":
                        assets_url=v["url"]
                        asset_response=httpx.get(assets_url)
                        if(asset_response.status_code==200):
                            assets=json.loads(asset_response.content)
                            assets_dict=assets["objects"]
                    
    asyncio.run(DownloadAssets(assets_dict,10))