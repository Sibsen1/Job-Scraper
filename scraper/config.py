from configparser import ConfigParser

parser = ConfigParser()
parser.read("config.ini")

logJSEvents = parser.getboolean("general", "logJSEvents")

saveToLocal = parser.getboolean("general", "saveToLocal")
uploadToS3 = parser.getboolean("general", "uploadToS3")

concurrentRequests = parser.getfloat("scraping", "concurrentRequests")
requestsPerSeconds = parser.getfloat("scraping", "requestsPerSeconds")