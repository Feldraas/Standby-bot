import requests

from domain import URL

mod_list = {}

for mod in requests.get(url=URL.WARFRAME_MODS).json():
    if "wikiaThumbnail" in mod:
        mod_list[mod["name"].lower()] = mod["wikiaThumbnail"]
