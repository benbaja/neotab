import time
import re
import requests
import io
from os import path
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import NoSuchElementException

sigma_aliases = ["Sigma", "sigma", "Merck", "merck", "Sigma ", "sigma ", "sigma aldrich", "Sigma aldrich", "Sigma Aldrich", "sigma Aldrich", "sigma-aldrich", "Sigma-aldrich", "Sigma-Aldrich", "sigma-Aldrich", "Aldrich", "aldrich", "Supelco", "supelco", "gibco", "Gibco", "Fluka"]
euromedex_aliases = ["Euromedex", "euromedex", "Bio Basic", "Bio basic", "bio Basic", "Bio-Basic", "Bio-basic", "bio-Basic"]
thermo_aliases = ["Thermo Scientific", "Invitrogen", "invitrogen", "Thermoscientific", "Thermo", "Thermo Fisher", "ThermoScientific"]
fisher_aliases = ["Fisher", "Fishersci", "Fisher Bioreagents", "Fisher Bioreagent", "Fisher Scientific", "FIsher Scientific"]
duchefa_aliases = ["Duchefa", "duchefa"]

def get_driver():
    options = webdriver.ChromeOptions()
    options.add_argument('--ignore-ssl-errors=yes')
    options.add_argument('--ignore-certificate-errors')
    options.add_argument('-timeout=30')
    prefs = {"download.default_directory" : "/home/seluser/Downloads/", "download.prompt_for_download": False, "plugins.always_open_pdf_externally": True, "directory_upgrade": True}
    options.add_experimental_option("prefs",prefs)
    driver = webdriver.Remote(
        command_executor='http://10.10.0.55:4444/wd/hub',
        options=options)
    driver.maximize_window()
    time.sleep(10)

    return driver

def duchefa(ref) :
    driver = get_driver()
    ref_url = "https://www.duchefa-biochemie.com/product/details/number/" + str(ref)
    driver.get(ref_url)
    time.sleep(3)
    driver.find_element(By.XPATH, "//a[contains(.,\'MSDS\')]").click()
    driver.find_element(By.XPATH, "//td[contains(.,\'Français\')]").click()
    time.sleep(1)
    driver.find_element(By.XPATH, "//td[contains(.,\'English\')]").click()
    time.sleep(2)
    driver.close()
    driver.quit()

    # make sure to share volume with NAS on selenium docker
    msds_fr_path = "/home/" + ref + "_FR.pdf"
    msds_en_path = "/home/" + ref + "_GB.pdf"

    if Path(msds_fr_path).is_file():
        with open(msds_fr_path, "rb") as fh:
            msds_fr = io.BytesIO(fh.read())
    else :
        msds_fr = None

    if Path(msds_en_path).is_file():
        with open(msds_en_path, "rb") as fh:
            msds_en = io.BytesIO(fh.read())
    else :
        msds_en = None
    
    return msds_fr, msds_en

def euromedex(ref) :
    driver = get_driver()
    #file_path = "/Users/benjaminbuhot/Downloads/msds_docker/" + ref + "_FDS.pdf"
    url = "https://shopresearch.euromedex.com/btREC/control/product?productId=REC_" + ref
    driver.get(url)
    time.sleep(1)
    try :
        driver.find_element(By.XPATH, "//a[contains(text(),'Safety data sheet')]").click()
    except NoSuchElementException :
        driver.close()
        driver.quit()
        return None, None
    time.sleep(0.5)

    try :
        sds_url = driver.find_element(By.LINK_TEXT, "View link").get_attribute("href")
    except NoSuchElementException:
        sds_url = False

    headers = {'User-Agent': 'Mozilla/5.0'}

    if sds_url :
        r = requests.get(sds_url, headers=headers, stream=True)
    else :
        driver.close()
        driver.quit()
        return None, None
    
    if r.status_code == 200 and sds_url :
        msds_en = io.BytesIO(r.content)
    else :
        msds_en = None

    driver.close()
    driver.quit()
    return None, msds_en

def format_ref_sigma(str) :
    if "." in str :
        sep = "\."
        pos = -1
    elif "-" in str :
        sep = "-"
        pos = 0
    else :
        return str

    last_dot = [m.start() for m in re.finditer(sep, str)][pos]
    str_cut = str[:last_dot]
    return str_cut

def sigma(ref) :
    driver = get_driver()
    ref = format_ref_sigma(ref)

    driver.get("https://www.sigmaaldrich.com/FR/fr/documents-search?tab=sds")
    time.sleep(3)
    try :
        driver.find_element(By.XPATH, "//button[@id=\'onetrust-reject-all-handler\']").click()
    except :
        pass
    time.sleep(1)
    driver.find_element(By.XPATH, "//input[@id=\'sds-product-number-field\']").location_once_scrolled_into_view
    time.sleep(0.5)
    driver.find_element(By.XPATH, "//input[@id=\'sds-product-number-field\']").click()
    driver.find_element(By.ID, "sds-product-number-field").send_keys(ref)
    driver.find_element(By.ID, "sds-product-number-field").send_keys(Keys.ENTER)
    time.sleep(0.5)

    # check if modal is asking for a selection, if so click the first one
    try :
        driver.find_element(By.XPATH, "//div[@id='sds-modal']/div[3]/div[2]/form/div/label/span[2]").click()
    except NoSuchElementException:
        pass  

    # tries to extract download URL
    try :
        fr_sds_url = driver.find_element(By.XPATH, "//a[contains(text(),\'FR\')]").get_attribute("href")
    except NoSuchElementException:
        fr_sds_url = False

    try :
        en_sds_url = driver.find_element(By.XPATH, "//a[contains(text(),\'EN\')]").get_attribute("href")
    except NoSuchElementException:
        en_sds_url = False
    
    headers = {'User-Agent': 'Mozilla/5.0'}

    if fr_sds_url :
        r_fr = requests.get(fr_sds_url, headers=headers, stream=True)
        if r_fr.status_code == 200 and fr_sds_url:
            msds_fr = io.BytesIO(r_fr.content)
        else :
            msds_fr = None
    else :
        msds_fr = None

    if en_sds_url :
        r_en = requests.get(en_sds_url, headers=headers, stream=True)
        if r_en.status_code == 200 and en_sds_url :
            msds_en = io.BytesIO(r_en.content)
        else :
            msds_en = None
    else :
        msds_en = None

    driver.close()
    driver.quit()
    return msds_fr, msds_en

def fetch_MSDS(supplier, ref):

    if supplier in sigma_aliases :
        return sigma(ref)
    elif supplier in euromedex_aliases :
        return euromedex(ref)
    elif supplier in thermo_aliases :
        return None, None
    elif supplier in fisher_aliases :
        return None, None
    elif supplier in duchefa_aliases :
        return duchefa(ref)
    else :
        return None, None
