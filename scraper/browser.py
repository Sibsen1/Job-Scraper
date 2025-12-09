import asyncio
from botocore.tokens import datetime
import zendriver as zd
from zendriver.core.cloudflare import cf_find_interactive_challenge
from scraper import config

from os import getenv
from zendriver.cdp import runtime, debugger
from zendriver.core.tab import ProtocolException
from websockets.exceptions import ConnectionClosedError
from scraper.data import SiteParams
from utils.logger import *

userAgent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36"
loginURL = "https://www.upwork.com/ab/account-security/login"

browser: zd.Browser | None = None
printLock = asyncio.Lock()

async def getBrowser(target : SiteParams) -> zd.Browser:
    global browser

    if browser is not None: return browser

  #  browser = await zd.start(headless=target.useHeadless, user_agent=userAgent)
    browser = await zd.start(headless=target.useHeadless)
    
    return browser


async def newPage(url, target) -> zd.Tab:
    
    browser = await getBrowser(target)
    page: zd.Tab = None

    if browser.main_tab.url == "about:blank":
        await browser.main_tab.get(url)
        page = browser.main_tab
    else:
        page = await browser.get(url, True)

    if config.logJSEvents:
        await attachLogHandlers(page)
    return page


async def endSession():
    global browser

    if browser:
        await browser.stop()

    browser = None



async def login(target):

    logInfo("login()")
    username = getenv("UPWORK_USERNAME")
    password = getenv("UPWORK_PASSWORD")
    securityQuestion = getenv("UPWORK_SECURITY_QUESTION")

    if not username or not password:
        raise RuntimeError("'username' and/or 'password' not set in environment variables!")

    _page = await newPage(loginURL, target)
#    _page = await browser.get(loginURL)
    
    #await handleCloudflare(_page)

    userInp = await _page.select('#login_username:not(:disabled)')
    contButt = await _page.select('#login_password_continue')
    
    await userInp.send_keys(username)
    await asyncio.sleep(0.1)
    await contButt.click();
    
    passInp = await _page.select('#login_password:not(:disabled)')
    contButt = await _page.select('#login_control_continue')
    
    await asyncio.sleep(0.5)
    await passInp.send_keys(password)
    await asyncio.sleep(0.1)
    await contButt.click();

    async def waitLoginEnd():
        loop = asyncio.get_running_loop()
        loginTimeout = loop.time() + 30 # Wait for max 30 sec

        while "/login" in _page.url:
            await asyncio.sleep(0.1)

            if loop.time() >= loginTimeout:
                break

        else:
            return True
        return False

    if await waitLoginEnd():
        logInfo("Finished logging in.")
        return

    secInp = await _page.query_selector('input:not(:disabled)')
    contButt = await _page.query_selector('.air3-loader-container.auth-growable-flex button')

    if not secInp or not contButt:
        logError("Login timed out.")
        return
    
    logInfo("Answering security questions.")
    
    await asyncio.sleep(0.5)
    await secInp.send_keys(securityQuestion)
    await asyncio.sleep(0.1)
    await contButt.click();

    if await waitLoginEnd():
        logInfo("Finished logging in.")
        return
    
    logError("Login timed out.")
    


async def solveCloudFlare(page):
    try:
        (h, s, c) = await cf_find_interactive_challenge(page)
        if not c:
            return False
     
        await page.verify_cf(timeout=10)
        logInfo("Cloudflare challenge solved.")  
    
    except (TimeoutError, ProtocolException, asyncio.CancelledError, ConnectionClosedError):
        pass
    
    except Exception as e:
        logError("solveCloudFlare():", repr(e))
        
    return True



async def attachLogHandlers(page: zd.Tab):
    # Allows browser logs and exceptions to be logInfoed to console
    
    await page.send(runtime.enable()) # Required for cdp to send (console/error) events to python
    await page.send(debugger.enable()) # Used in logInfoing code for exception stack traces
      

    def formatNode(obj: runtime.RemoteObject) -> str:
        if not obj.preview:
            return "<node>"

        tag = obj.preview.description or obj.class_name or "node"

        attrs = {}
        for prop in obj.preview.properties:
            name = prop.name
            value = prop.value
            if value is None or value == "":
                continue  # skip empty attrs
            attrs[name] = value

        if attrs:
            attr_str = " ".join(f'{k}="{v}"' for k, v in attrs.items())
            return f"<{tag} {attr_str}>"
        else:
            return f"<{tag}>"


    def formatConsoleArg(arg : runtime.RemoteObject):
        if arg.value is not None:
            return repr(arg.value)

        if getattr(arg, "subtype", None) == "node":
            return formatNode(arg)

        if getattr(arg, "subtype", None) == "error":
            return "Error"

        if getattr(arg, "type_", None) == "function":
            return f"function {arg.description or '()'}"
        
        return f"[{getattr(arg, 'type_', '<no type>')}]"



    # Handler for console messages (including errors)
    async def consoleHandler(event: runtime.ConsoleAPICalled):

        argsJoin = " ".join(formatConsoleArg(a) for a in event.args)[:200]
        
        async with printLock:
            if event.type_ == "error":  ## Catches mostly console.error and some warnings
                logError(f"JS Error: {argsJoin}")
                await logStackTrace(event.stack_trace)

            else:
                logInfo(f"JS Console ({event.type_}): {argsJoin}")

    # Handler for uncaught exceptions  
    async def exceptionHandler(event: runtime.ExceptionThrown):  
        exception = event.exception_details  
        
        async with printLock:
            logError(f"\nJS Exception:\n ", exception.text, exception.exception.description if exception.exception else "")
        
            await logStackTrace(exception.stack_trace)

    async def logStackTrace(stackTrace):   
        # Looks up script sources, may be slow

        if not stackTrace:
            return

        message = ""
          
        for frame in stackTrace.call_frames:  
            message += f"  > at {frame.function_name or '<anonymous>'} ({frame.url}:{frame.line_number}:{frame.column_number})\n"
              
            # Fetch the script source (slow and requires debugger enabled:) 
            try:
                script_source, _ = await page.send(debugger.get_script_source(frame.script_id))  

                lines = script_source.split('\n')
                if 0 <= frame.line_number < len(lines):  
                    message += (f"     {lines[frame.line_number]}")   

            except zd.core.connection.ProtocolException as e:
                pass

        logError(message);



    page.add_handler(runtime.ConsoleAPICalled, consoleHandler)  
    page.add_handler(runtime.ExceptionThrown, exceptionHandler)  


async def screencapLoop(page : zd.Tab):
    # Saves a screenshot every 2 seconds for debugging

    try: 
        i = 1
        while page and not page.closed:
            await page.sleep(2)

            dateTag = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
            filename = f"Page {browser.tabs.index(page)} - {dateTag}.jpeg"

            logInfo("Taking screenshot ", repr(filename))
            await page.save_screenshot("/screenshots/" + filename)

            i+=1
        
    except asyncio.CancelledError:
        pass

    