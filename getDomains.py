# getList
# get your domains list
#
# Namecheap doc
# https://www.namecheap.com/support/api/methods/domains/get-list/
#

import datetime, json, os, pathlib, requests, xmltodict
from tabulate import tabulate
from requests.exceptions import HTTPError
from helpers import config_init, get_public_ip

config_file = './.config.ini'       # Configuration file
public_ip = get_public_ip()         # Get public ip

app_defaults = {
    'App': {
        'debug': False,                         # Enable to display verbose printouts
        'uselocal': False,                      # For debugging if wanting to avoid many calls - add last call logic
        'datetimeformat': '%Y-%m-%d %H:%M:%S'.replace('%','%%')     # Needed for configparser interpolation
    },
    'Namecheap': {
        'username': 'NAMECHEAP_USERNAME',		# Namecheap username
        'apikey': 'NAMECHEAP_API_KEY'	        # Must be created (Namecheap => Profile => Tools => Business and app)
    },
    'Client': {
        'ipaddr': public_ip or 'YOUR_IP_ADDRESSHERE'    # Must be whitelisted (Namecheap => Profile => Tools => Business and app)
    },
    'getDomains': {
        'apidomain': 'api.namecheap.com',           # Api url
        'apicommand': 'namecheap.domains.getList',  # Api command for getDomains
        'cachefile': 'getDomainsOutput.json',   # getDomains call to output here
        'cachetime': 240,                       # Time between calls in seconds
        'lastperformed': datetime.datetime.fromtimestamp(0),                     # Time last performed
        'page': 1,						        # default 1
        'pagesize': 100,					    # 0-100, default 20
        'sortby': 'EXPIREDATE',				    # default not set, maybe NAME : Possible values are NAME, NAME_DESC, EXPIREDATE, EXPIREDATE_DESC, CREATEDATE, CREATEDATE_DESC
        'colKeys': ['@Name','@Expires','@IsExpired','@AutoRenew','IsOurDNS','@WhoisGuard']	# Columns to pull
    }
}
[config, app_config] = config_init(config_file, app_defaults)

# Setup cfg variables
cfg_app = app_config.get('App', {})
cfg_getDomains = app_config.get('getDomains', {})
cachefile = cfg_getDomains.get('cachefile') 
username = app_config.get('Namecheap', {}).get('username')
apikey = app_config.get('Namecheap', {}).get('apikey')
ipaddr = app_config.get('Client', {}).get('ipaddr')

def dprint(_content, _debug=cfg_app['debug']):
    if (_content and type(_content)==str and _debug):
        print(_content)

def prefill(str_in):
    return f' ({str_in})' if str_in and type(str_in) == str else ''

prompted = False
if not username or username == app_defaults['Namecheap']['username']:
    prompted = True
    invalid = True
    while invalid:
        user_name = input(f'Please enter your namecheap username{prefill(username)}: ')
        username = username if not user_name and username else user_name
        if username: invalid = False

if not apikey or apikey == app_defaults['Namecheap']['apikey']:
    prompted = True
    invalid = True
    while invalid:
        api_key = input(f'Please enter your namecheap API key{prefill(apikey)}: ')
        apikey = apikey if not api_key and apikey else api_key
        if apikey: invalid = False

if prompted:
    if not ipaddr or ipaddr == app_defaults['Client']['ipaddr'] or ipaddr != app_config['Client']['ipaddr']:
        invalid = True
        while invalid:
            prefilled=prefill(ipaddr)
            enter_confirm='confirm' if prefilled else 'enter'
            in_ipaddr = input(f'Please {enter_confirm} your IP address{prefilled}: ')
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


last_performed = app_config['getDomains']['lastperformed']
date_time_now = datetime.datetime.now()
difference_s = (date_time_now - last_performed).total_seconds()
usecachefile = cfg_app['uselocal'] or difference_s < cfg_getDomains['cachetime']
dprint(f'\nusecachefile: {usecachefile} ({difference_s}/{cfg_getDomains["cachetime"]})\n')

if not usecachefile:
    # Write changes back to the file
    config.set('getDomains', 'lastperformed', date_time_now.strftime(cfg_app.get('datetimeformat')))
    with open(config_file, 'w') as configfile:
        config.write(configfile)

def genApiUrl(
    _apicommand, 
    _apikey=apikey, 
    _ipaddr=ipaddr,
    _username=username, 
    _apidomain=cfg_getDomains['apidomain'],
    _page=cfg_getDomains['page'],
    _pagesize=cfg_getDomains['pagesize'],
    _sortby=cfg_getDomains['sortby']
):
    outStr=''
    if (_apicommand and _apikey and _ipaddr and _username and _apidomain):
        urlArr = [
            f'https://{_apidomain}/xml.response?',
            f'ApiUser={_username}',
            f'&ApiKey={_apikey}'
            f'&UserName={_username}',
            f'&Command={_apicommand}',
            f'&ClientIp={_ipaddr}',
            f'&Page={_page}',
            f'&PageSize={_pagesize}',
            f'&SortBy={_sortby}'
        ]
        for x in urlArr:
            outStr=f'{outStr}{str(x)}'
    else:
        pretxt='Problem with genApiUrl: '
        if (not _apicommand): print(f'{pretxt} Missing api command')
        if (not _apikey): print(f'{pretxt} Missing api key')
        if (not _ipaddr): print(f'{pretxt} Missing api client ip')
        if (not _username): print(f'{pretxt} Missing api username')
        if (not _apidomain): print(f'{pretxt} Missing api domain')
    return outStr if outStr else None

def getDomains(
    _fromLocal=cfg_app['uselocal'] or False,
    _colKeys=cfg_getDomains['colKeys'],
    _apicommand=cfg_getDomains['apicommand']
):
    jsonResponse = None
    if (not _fromLocal or not cachefile):
        dprint('Gathering from request')
        url = genApiUrl(_apicommand)
        dprint(url)    
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
        # Create file if doesn't exist
        if not os.path.isfile(cachefile):
            pathlib.Path(cachefile).touch(exist_ok=True)
        # Write response to cachefile
        with open(cachefile, 'w') as cf:
            json.dump(jsonResponse, cf)
    else:
        dprint('Gathering from local cachefile')
        with open(cachefile, "r") as f:
            jsonResponse = json.load(f)

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
        dprint('Issue with cell input')
        return ''

    if (jsonResponse):
        loadedJson = json.loads(jsonResponse)
        domainArr = None
        try:
            api_response = loadedJson['ApiResponse']
            status = api_response['@Status']
            if status == 'ERROR':
                print(f'\nResponse: {json.dumps(api_response)}\n')
                return -1
            else:
                domainArr = api_response['CommandResponse']['DomainGetListResult']['Domain']
        except:
            print('Error loading domain data')
            return -1

        numCount=1
        d=[]
        if type(domainArr) == list:
            for x in domainArr:        
                if (checkKeysExist(x, _colKeys)):
                    e=[numCount]
                    for y in _colKeys:
                        e.append(cellFormat(x[y]))
                    d.append(e)
                    numCount+=1
                else:
                    print(f'Issue with {str(x)} - Missing a required property')
        
        return d
    print('Error with json response\n')
    return -1

# Print out domains
domainsArr=getDomains(usecachefile)
if domainsArr == -1: quit()
if (type(domainsArr == list) and domainsArr):
    print('')

    dprint(f'{json.dumps(domainsArr)}\n')
    def formatKeys(_arrIn=[]):
        output=['#']
        if (_arrIn and type(_arrIn) == list):
            for x in _arrIn:
                if (x and type(x) == str):
                    output.append(x[1:])
        return output
    print(tabulate(domainsArr, headers=formatKeys(cfg_getDomains['colKeys'])))
    
    print('')
else:
    print('Nothing to print')
