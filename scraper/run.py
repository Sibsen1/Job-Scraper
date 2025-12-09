from ast import Dict
import asyncio
from dataclasses import asdict

import zendriver.core.cloudflare as zcf
from utils.logger import *
from typing import List

from zendriver import Tab

from scraper import config
from scraper.data import JobData
from .browser import getBrowser, login, newPage, endSession
from .parser import SiteParams, parsePage
from pprint import pformat


requestSemaphore = asyncio.Semaphore(config.concurrentRequests)

async def scrapeTarget(target : SiteParams) -> Dict:
    # Returns dict with job id as key
    
    logInfo("Scraping target:")
    logInfo(pformat(target))

    if (target.login):
        await login(target)

    parseTasks = []
    for url in target.urls:
        parseTask = asyncio.create_task(scrapeUrl(url, target))
        parseTasks.append(parseTask)

    results = await asyncio.gather(*parseTasks)
    results = {a:b for l in results for (a,b) in l.items()}
    
    #await endSession()
    return results


async def scrapeUrl(url: str, target : SiteParams) -> List[JobData]:

    results = []
    async with requestSemaphore:

        page = await newPage(url, target)
        results = await parsePage(page, target)
        await asyncio.sleep(1 / config.requestsPerSeconds)

    return results