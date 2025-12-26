import asyncio
import re
from typing import List
from dotenv import load_dotenv

from utils.logger import *
from scraper.data import JobData, SiteParams
from scraper.run import scrapeTarget
from utils.s3 import uploadFile
from utils.storage import saveDataToFile


jobGroupCodes = {
     "531770282584862721": "Accounting & Consulting",
     "531770282580668416": "Admin Support",
     "531770282580668417": "Customer Service",
     "531770282580668420": "Data Science & Analytics",
     "531770282580668421": "Design & Creative",
     "531770282584862722": "Engineering & Architecture",
     "531770282580668419": "IT & Networking",
     "531770282584862723": "Legal",
     "531770282580668422": "Sales & Marketing",
     "531770282584862720": "Translation",
     "531770282580668418": "Web, Mobile & Software Dev",
     "531770282580668423": "Writing",
}

#targetJobGroups = jobGroupCodes.keys()
targetJobGroups = ["531770282580668419", "531770282580668418"]

targets = [
    SiteParams( # All job groups:
        ["https://www.upwork.com/nx/search/jobs/?category2_uid=%s&per_page=50&sort=recency" % ",".join(targetJobGroups)],
        {
            "id":                '::data-ev-job-uid',
            "title":             '[data-test="UpCLineClamp"]',
            "url":               '[data-test="job-tile-title-link UpLink"]::href',
            "description":       '[data-test="UpCLineClamp JobDescription"]',
            "date":              '[data-test="job-pubilshed-date"]>*:last-child',
            "rating":            '[data-test="total-feedback"]>*>*>*>*:last-child',
            "location":          '[data-test="location"]',
            "isPaymentVerified": '[data-test="payment-verified"]',
            "totalSpent":        '[data-test="total-spent"]',
            "jobType":           '[data-test="job-type-label"]',
            "experienceLevel":   '[data-test="experience-level"]',
            "duration":          '[data-test="duration-label"]',
            "tags":              '[data-test="TokenClamp JobAttrs"]',
            "proposals":         '[data-test="proposals-tier"]>*:last-child',
        },
        jobSelector="article",
        loadMoreSelector='[data-ev-label="pagination_next_page"]',

        maxPages=10,
        scroll=False,
        login=True, # More data is visible for each job after login
        useHeadless=False # Cloudflare locks us out on headless
    )
]



async def main():
    setupLogger()

    target = targets[0]

    result = await scrapeTarget(target)
    jobs : List[JobData] = list(result.values())

    wordBlacklist = ["app dev", "wordpress", "firmware", r"\bai\b", r"\bnft\b", "pplication dev", "app design", "graphic design"]
    tagBlacklist = ["web de", "graphic design"]
    
    wordBlacklistP = [re.compile(p, re.IGNORECASE) for p in wordBlacklist]
    tagBlacklistP = [re.compile(p, re.IGNORECASE) for p in tagBlacklist]

    jobsF = []
    for j in jobs:
        if any(re.search(patt, tag) for patt in tagBlacklistP for tag in j.tags):
            continue
        
        fullText = (j.title+"\n"+j.description)
        if any(re.search(patt, fullText) for patt in wordBlacklistP):
            continue

        jobsF.append(j)
    logging.info(f"Filtered out {len(jobs)-len(jobsF)} jobs. Remaining jobs: {len(jobsF)}")

    if jobsF:
        filename = saveDataToFile(jobsF, target)

       # uploadFile(filename, f"scrapes/Upwork/{filename}")
        #logInfo(f"Uploaded {len(jobs)} jobs to S3 Bucket.")
    
        #jobsJsonBytes = json.dumps([asdict(j) for j in jobs], indent=2).encode("utf-8")
        #uploadBytes(jobsJsonBytes, f"scrapes/Upwork/data.json", content_type="application/json")



if __name__ == "__main__":
    load_dotenv()
    asyncio.run(main())
