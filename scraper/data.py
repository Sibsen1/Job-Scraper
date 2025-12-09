import json
import re
from typing import List
from utils.logger import *
from dataclasses import Field, asdict, dataclass, field, fields

from utils.misc import parseRelDatetime


def dataField(key: str, t: type) -> Field:
    typeMap = {
        list: lambda: field(metadata={'key': key},
                            init=True,
                            compare=False,
                            default_factory=list),
        str:  lambda: field(metadata={'key': key},
                            init=True,
                            compare=False,
                            default=""),
        bool: lambda: field(metadata={'key': key},
                            init=True,
                            compare=False,
                            default=False),
    }
    return typeMap[t]()

@dataclass
class SiteParams:
    urls: List[str]

    dataSelectors: dict  # Each key corresponds to a field in jobData; value is selector 
    jobSelector: str
    loadMoreSelector: str
    scroll: bool
    login: bool
    useHeadless: bool

    # Selectors are in the form of normal css selectors.
    # If a selector ends with "::<attributename>", it collects that attribute, otherwise innerText.


@dataclass
class JobData:
    id: str                 = field(metadata={'key': 'id'}),
    url: str                = dataField("url", str)
    name: str               = dataField("name", str)
    description: str        = dataField("description", str)
    date: str               = dataField("date", str)
    rating: str             = dataField("rating", str)
    location: str           = dataField("location", str)
    isPaymentVerified: bool = dataField("isPaymentVerified", bool)
    totalSpent: str         = dataField("totalSpent", str)
    jobType: str            = dataField("jobType", str)
    experienceLevel: str    = dataField("experienceLevel", str)
    duration: str           = dataField("duration", str)
    tags: List[str]         = dataField("tags", list)
    proposals: str          = dataField("proposals", str)

    def to_json(self) -> str:
        return json.dumps(asdict(self))

    @classmethod
    def from_json(cls, s: str):
        return cls(**json.loads(s))

def getSelector(job: JobData, fieldName: str, target: SiteParams):
    key = job.__dataclass_fields__[fieldName].metadata["key"]
    return target.selectors[key]

def isJob(data : dict) -> bool:
    if not data or not isinstance(data, dict):
        logDebug("isJob: Not job -  None or not dict:", data)
        return False

    JDFields = {f.name for f in fields(JobData)}
    sameFields = JDFields == set(data.keys())

    if not sameFields:
        logDebug("isJob: Not job - data keys not equal to JobData keys: ", set(data.keys()))

    return sameFields

def makeJob(raw: dict) -> JobData:
    if not isJob(raw):
        return None

    logDebug("Making job from", raw)

    def getStr(key):
        v = raw.get(key, "")
        if isinstance(v, list):
            return "".join([str(item) for item in v])
        return str(v).strip()

    def getList(key):
        val = raw.get(key, [])
        if not isinstance(val, list):
            return []

        return [item.strip() for v in val for item in v.split("\n") if item.strip()]

    id = getStr("id")
    url = getStr("url")
    name = getStr("name")
    description = getStr("description")

    date = parseRelDatetime(getStr("date"))
    rating = getList("rating")[-1] if getList("rating") else ""
    
    location = getStr("location")
    location = re.sub(r"\bLocation:?\b", "", location, flags=re.IGNORECASE).strip()

    verified = getStr("isPaymentVerified").lower()
    verified = ("verified" in verified and not "unverified" in verified)

    totalSpent = getStr("totalSpent")
    totalSpent = re.sub(r"\bspent\b", "", totalSpent, flags=re.IGNORECASE).strip()

    jobType=getStr("jobType")
    experienceLevel=getStr("experienceLevel")
    duration=getStr("duration")
    tags=getList("tags")
    proposals=getStr("proposals")

    return JobData(
        id=id,
        url=url,
        name=name,
        description=description,
        date=date,
        rating=rating,
        location=location,
        isPaymentVerified=verified,
        totalSpent=totalSpent,
        jobType=jobType,
        experienceLevel=experienceLevel,
        duration=duration,
        tags=tags,
        proposals=proposals,
    )