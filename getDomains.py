# getList
# get your domains list
#
# Namecheap doc
# https://www.namecheap.com/support/api/methods/domains/get-list/
#

import xmltodict, json, os
import requests
# import math
from tabulate import tabulate
from requests.exceptions import HTTPError
import pathlib
import configparser

config_file = './.config.ini'       # Configuration file

def get_public_ip():
    try:
        response = requests.get('https://api.ipify.org')
        public_ip = response.text.strip()
        return public_ip
    except requests.RequestException as e:
        print(f"Error: {e}")
        return None

public_ip = get_public_ip()


app_config = {
    'App': {
        'debug': False,                         # Enable to display verbose printouts
        'useLocal': False,                      # For debugging if wanting to avoid many calls - add last call logic
        'localFile': 'getDomainsOutput.txt'     # getDomains call to output here
    },
    'Namecheap': {
        'username': 'NAMECHEAP_USERNAME',		# Namecheap username
        'apikey': 'NAMECHEAP_API_KEY'	        # Must be created (Namecheap => Profile => Tools => Business and app)
    },
    'Client': {
        'ipaddr': public_ip or 'YOUR_IP_ADDRESSHERE'    # Must be whitelisted (Namecheap => Profile => Tools => Business and app)
    },
    'getDomains': {
        'apidomain': 'api.namecheap.com',
        'page': 1,						        # default 1
        'pagesize': 100,					    # 0-100, default 20
        'sortby': 'EXPIREDATE',				    # default not set, maybe NAME : Possible values are NAME, NAME_DESC, EXPIREDATE, EXPIREDATE_DESC, CREATEDATE, CREATEDATE_DESC
        'colKeys': ['@Name','@Expires','@IsExpired','@AutoRenew','@WhoisGuard','@IsOurDNS']	# Columns to pull
    }
}
app_vals = {}

# Create config file if doesn't exist
if not os.path.isfile(config_file):
    path = pathlib.Path(config_file)
    path.touch(exist_ok=True)

# Load configuration file
if os.path.isfile(config_file):
    config = configparser.ConfigParser()
    config.read(config_file)

    for section in app_config.keys():
        sub_sections = app_config[section].keys()
        for sub_section in sub_sections:
            def_value = app_config[section][sub_section]
            if section not in app_vals: app_vals[section] = {}
            if section not in config.sections() or []: config.add_section(section)
            config_value = None
            if type(def_value) is bool:
                config_value = config.getboolean(section, sub_section, fallback=def_value)
                config.set(section, sub_section, str(config_value))
            elif type(def_value) is int:
                config_value = config.getint(section, sub_section, fallback=def_value)
                config.set(section, sub_section, str(config_value))
            elif type(def_value) is str:
                config_value = config.get(section, sub_section, fallback=def_value)
                config.set(section, sub_section, config_value)
            elif type(def_value) is list:
                config_value = json.loads(config.get(section, sub_section, fallback=json.dumps(def_value)))
                config.set(section, sub_section, json.dumps(config_value))
            app_vals[section][sub_section] = config_value
            

    # Write changes back to the file
    with open(config_file, 'w') as configfile:
        config.write(configfile)

# Gather variables
debug = app_vals['App']['debug']
useLocal = app_vals['App']['useLocal']
localFile = app_vals['App']['localFile']
username = app_vals['Namecheap']['username']
apikey = app_vals['Namecheap']['apikey']
ipaddr = app_vals['Client']['ipaddr']
apidomain = app_vals['getDomains']['apidomain']
page = app_vals['getDomains']['page']
pagesize = app_vals['getDomains']['pagesize']
sortby = app_vals['getDomains']['sortby']
colKeys = app_vals['getDomains']['colKeys']

prompted = False
if not username or username == app_config['Namecheap']['username']:
    prompted = True
    invalid = True
    while invalid:
        username = input('Please enter your namecheap username: ')
        if username: invalid = False

if not apikey or apikey == app_config['Namecheap']['apikey']:
    prompted = True
    invalid = True
    while invalid:
        apikey = input('Please enter your namecheap API key: ')
        if apikey: invalid = False

if prompted:
    if not ipaddr or ipaddr == app_config['Client']['ipaddr']:
        invalid = True
        while invalid:
            statement = 'enter' if not ipaddr or ipaddr == 'YOUR_IP_ADDRESSHERE' else 'confirm'
            in_ipaddr = input(f'Please {statement} your IP address ({ipaddr}): ')
            ipaddr = ipaddr if not in_ipaddr and ipaddr else in_ipaddr
            if ipaddr: invalid = False
    
    invalid = True
    while invalid:
        in_confirm = (input(f'\nYou have configured:\n------------------\nUsername: {username}\nAPI Key: {apikey}\nIP Address: {ipaddr}\n------------------\n\nSave and proceed (y/n)? ')).lower()
        if in_confirm == 'y':
            config.set('Namecheap', 'username', username)
            config.set('Namecheap', 'apikey', apikey)
            config.set('Client', 'ipaddr', ipaddr)
            # Write changes back to the file
            with open(config_file, 'w') as configfile:
                config.write(configfile)
            invalid = False
        elif in_confirm == 'n':
            print('Aborting...')
            quit()

def genApiUrl(
    _apicommand, 
    _apikey=apikey, 
    _ipaddr=ipaddr,
    _username=username, 
    _apidomain=apidomain,
    _pagesize=pagesize,
    _sortby=sortby
):
    outStr=''
    if (_apicommand and _apikey and _ipaddr and _username and _apidomain):
        urlArr = [
            "https://",
            _apidomain,
            "/xml.response?ApiUser=",
            _username,
            "&ApiKey=",
            _apikey,
            "&UserName=",
            _username,
            "&Command=",
            _apicommand,
            "&ClientIp=",
            _ipaddr,
            "&PageSize=",
            _pagesize,
            "&SortBy=",
            _sortby
        ]
        for x in urlArr:
            outStr=outStr+str(x)
    else:
        if (debug):
            errorPretxt='Problem with genApiUrl: '
            if (not _apicommand): print(errorPretxt+'Missing api command')
            if (not _apikey): print(errorPretxt+'Missing api key')
            if (not _ipaddr): print(errorPretxt+'Missing api client ip')
            if (not _username): print(errorPretxt+'Missing api username')
            if (not _apidomain): print(errorPretxt+'Missing api domain')
    return outStr


def getDomains(
    _print=False,
    _fromLocal=False,
    _colKeys=colKeys,
    _debug=debug
):
    apicommand='namecheap.domains.getList'

    def doPrint(_content, _shouldPrint=_print, _debug=_debug):
        if (_debug or (_content and type(_content)==str and _shouldPrint)):
            print(_content)
    def formatKeys(_arrIn=[]):
        output=['#']
        if (_arrIn and type(_arrIn) == list):
            for x in _arrIn:
                if (x and type(x) == str):
                    output.append(x[1:])
        return output
    
    
    jsonResponse = None
    if (not _fromLocal):
        url = genApiUrl(apicommand)
        doPrint(url, False)
        if (_debug):
            print(url)    
        if (not url):
            return -1      

        try:
            response = requests.get(url)
            response.raise_for_status()
        except HTTPError as http_err:
            print(f'HTTP error occurred: {http_err}')
            return -1
        except Exception as err:
            print(f'Other error occurred: {err}')
            return -1

        jsonResponse = json.dumps(xmltodict.parse(response.text))
    else:
        f=open('getDomainsOutput.txt','r')
        fileRead=f.read()
        jsonResponse = json.dumps(xmltodict.parse(fileRead))
    

    def keyExist(_dict,_key):
        if _key in _dict.keys():
            return True
        return False
    def checkKeysExist(_dict,_keyArr):
        check=0
        for x in _keyArr:
            if (not keyExist(_dict,x)): break
            check+=1
        if (check != len(_keyArr)):
            return False
        return True
    def cellFormat(_cell=None):
        if (_cell and type(_cell)==str):
            if (_cell=='true' or _cell=='ENABLED'): return 'x'
            if (_cell=='false' or _cell=='DISABLED'): return '-'
            return _cell
        else:
            doPrint('Issue with cell input')
        return ''

    if (jsonResponse):
        loadedJson = json.loads(jsonResponse)
        doPrint('loadedJson', False)
        doPrint(loadedJson, False)
        domainArr = loadedJson['ApiResponse']['CommandResponse']['DomainGetListResult']['Domain']

        numCount=1
        d=[]
        for x in domainArr:        
            if (checkKeysExist(x, _colKeys)):
                e=[numCount]
                for y in _colKeys:
                    e.append(cellFormat(x[y]))
                d.append(e)
                numCount+=1
            else:
                if (_debug):
                    print("Issue with "+str(x)+" - Missing a required property")
        
        print('')
        doPrint(tabulate(d, headers=formatKeys(_colKeys)))
        print('')
        return d
    doPrint('Error with json response\n')
    return -1



# getDomains(print?,local file?,debug?)
#
# add 'print' to print out tabulated domain list
# 2nd param passed in is a local file if you wish 
# to work with a local save instead of pulling from namecheap
if (useLocal):
    domainsArr=getDomains('print', localFile)  
else:
    domainsArr=getDomains('print')  


if (debug):
    print(domainsArr)
    print('')
