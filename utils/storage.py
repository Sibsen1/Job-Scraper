from dataclasses import asdict, is_dataclass
import json
from datetime import datetime
from scraper.data import SiteParams
from utils.logger import *


def saveDataToFile(data: list, target: SiteParams):
    if not all(is_dataclass(obj) for obj in data):
        raise TypeError("Expected a list of dataclass instances")
    
    dateTag = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
    export = {
        "urls": target.urls, 
        "fetchedAt": dateTag, 
        "data" : [asdict(d) for d in data] 
        }
    filename = f"Scraped Data/Scraped-Data-{dateTag}.json"

    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(export, f, indent=2, ensure_ascii=False)  

    logInfo("\nSaved data as", filename)
    return filename