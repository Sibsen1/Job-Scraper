import asyncio
import json
import zendriver as zd

from typing import List
from scraper import browser
from scraper.browser import solveCloudFlare
from utils.logger import *
from scraper.data import JobData, SiteParams, makeJob


        
async def parsePage(page: zd.Tab, target: SiteParams, timeout=20) -> List[JobData]:
    # Searches until last page reached or nothing is found in timeout seconds.

    logInfo("Parsing page at tab ", page.browser.tabs.index(page))

    loop = asyncio.get_running_loop()
    lastFoundTime = loop.time()

    allJobs = {}
    while loop.time() - lastFoundTime < timeout:

        body = await page.query_selector("body")

        if not body:
            logInfo(f"No body, waiting...")
            await page.sleep(1)
            continue;

        if await solveCloudFlare(page):
            continue

        foundData = await getData(body, target)

        newJobs = 0
        for d in foundData:
            foundJob = makeJob(d)

            if not foundJob:
                logDebug("Found data is not job:", d)
                continue
            if foundJob.id in allJobs:
                continue
            
            logInfo("Found new job:", foundJob.url)

            allJobs[foundJob.id] = foundJob
            newJobs += 1


        logInfo(f"Found {len(foundData)} jobs, of which ({newJobs} new jobs added).")

        if (newJobs):
            lastFoundTime = loop.time()

            currentPage, maxPage = await getPagination(page)

            if currentPage is not None and maxPage is not None:
                if currentPage >= maxPage:
                    logInfo(f"End of pages reached ({currentPage} / {maxPage}).")
                    break
                else:
                    logInfo(f"Current Page: {currentPage}")

    
            if target.loadMoreSelector:
                loadMore = await page.query_selector(target.loadMoreSelector)

                if loadMore:
                    logInfo("Clicking on loadMore")
                    await loadMore.click()
        
            if target.scroll:
                logInfo ("Scrolling")
                await page.scroll_down(amount=1000, speed=8000)

        await page.sleep(1)

    logInfo(f"\nScraped a total of {len(allJobs)} jobs.\n")
    return allJobs



async def getData(body : zd.Element, target: SiteParams) -> List[dict]:
    
    jsString = ("""
    body => {
        try {
            """
            +"\nlet jobSelector = %s;"           % repr(target.jobSelector)
            +"\nlet selectors = JSON.parse(%s);" % repr(json.dumps(target.dataSelectors))
            +"""
            results = [];
            
            //console.log("found jobs:", body.querySelectorAll(jobSelector).length);

            body.querySelectorAll(jobSelector).forEach(e => {
                let result = {}

                console.log("found element:", e);

                for (selKey in selectors) {
                    let [selector, attr] = selectors[selKey].split("::");

                    let foundData, extractor;
                    if (selector) foundData = [...e.querySelectorAll(selector)]
                    else          foundData = [e]

                    if (attr) extractor = x => x.getAttribute(attr) || ""
                    else      extractor = x => x.innerText

                    result[selKey] = foundData.map(extractor)
                    
                    console.log("  sel, attr:", selector, attr);
                    console.log("  found data:", result);
                }
                results.push(result)
            })

            return results

			} catch (err) {
            console.log("JS evaluate error:", JSON.stringify({
                name: err.name, message: err.message, stack: err.stack
            }, null, 2));
        }
    }
    """)

    data = await body.apply(jsString)
    if not isinstance(data, list):
        return []

    return data

async def getPagination(page : zd.Tab) -> List[int]: 
    # Returns list [currentPage, maxPages] if found, otherwise [None, None]
    try:
        pagination = await page.query_selector('[data-test="UpCPagination"]')
        curP = pagination.attrs['data-ev-current_page_index']
        maxP = pagination.attrs['data-ev-max_page_count']
        return [int(curP), int(maxP)]

    except TypeError:
        return [None, None]
    