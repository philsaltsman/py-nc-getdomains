# getDomains
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
        'datetimeformat': '%Y-%m-%d %H:%M:%S'   #.replace('%','%%')     # Needed for configparser interpolation
    },
    'Namecheap': {
        'username': 'NAMECHEAP_USERNAME',		# Namecheap username
        'apikey': 'NAMECHEAP_API_KEY'	        # Must be created (Namecheap => Profile => Tools => Business and app)
    },
    'Client': {
        'ipaddr': 'YOUR_IP_ADDRESSHERE'    # Must be whitelisted (Namecheap => Profile => Tools => Business and app)
    },
    'getDomains': {
        'apidomain': 'api.namecheap.com',           # Api url
        'apicommand': 'namecheap.domains.getList',  # Api command for getDomains
        'cachefile': './cache/getDomainsResponse.json',   # getDomains call to output here
        'cachetime': 240,                       # Time between calls in seconds
        'lastperformed': datetime.datetime.fromtimestamp(0),                     # Time last performed
        'page': 1,						        # default 1
        'pagesize': 100,					    # 0-100, default 20
        'sortby': 'EXPIREDATE',				    # default not set, maybe NAME : Possible values are NAME, NAME_DESC, EXPIREDATE, EXPIREDATE_DESC, CREATEDATE, CREATEDATE_DESC
        'colKeys': ['@Name','@Expires','@IsExpired','@AutoRenew','@IsOurDNS','@WhoisGuard']	# Columns to pull
    }
}
[config, app_config] = config_init(config_file, app_defaults)

# Setup cfg variables
cfg_app = app_config.get('App', {})
cfg_getDomains = app_config.get('getDomains', {})
cachefile = cfg_getDomains.get('cachefile') 
cachetime = cfg_getDomains.get('cachetime')
last_performed = cfg_getDomains.get('lastperformed')
username = app_config.get('Namecheap', {}).get('username')
apikey = app_config.get('Namecheap', {}).get('apikey')
ipaddr = public_ip or app_config.get('Client', {}).get('ipaddr')

# Defaults
default_username = app_defaults.get('Namecheap', {}).get('username')
default_key = app_defaults.get('Namecheap', {}).get('apikey')
default_ipaddr = app_defaults.get('Client', {}).get('ipaddr')

def dprint(_content, _debug=cfg_app.get('debug')):
    if (_content and type(_content)==str and _debug):
        print(_content)

def prefill(str_in, default=''):
    return f' ({str_in})' if str_in and type(str_in) == str and type(default) == str and str_in != default else ''

prompted = False
if not username or username == default_username:
    prompted = True
    invalid = True
    while invalid:
        user_name = input(f'Please enter your namecheap username{prefill(username, default_username)}: ')
        username = username if not user_name and username else user_name
        if username: invalid = False

if not apikey or apikey == default_key:
    prompted = True
    invalid = True
    while invalid:
        api_key = input(f'Please enter your namecheap API key{prefill(apikey, default_key)}: ')
        apikey = apikey if not api_key and apikey else api_key
        if apikey: invalid = False

if not ipaddr or ipaddr == default_ipaddr or ipaddr != app_config.get('Client', {}).get('ipaddr'):
    prompted = True
    invalid = True
    while invalid:
        in_ipaddr = input(f"Please {'confirm' if prefill(ipaddr) else 'enter'} your IP address{prefill(ipaddr, default_ipaddr)}: ")
        ipaddr = ipaddr if not in_ipaddr and ipaddr else in_ipaddr
        if ipaddr: invalid = False

if prompted:
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


date_time_now = datetime.datetime.now()
difference_s = (date_time_now - last_performed).total_seconds()
usecachefile = cfg_app.get('uselocal') or difference_s < cachetime    

if not usecachefile:
    print('\nGather from request')
    # Write changes back to the file
    config.set('getDomains', 'lastperformed', date_time_now.strftime(cfg_app.get('datetimeformat')))
    with open(config_file, 'w') as configfile:
        config.write(configfile)
else:
    print(f'\nGathering from local cache ({round(difference_s, 1)}s / {cachetime}s)')

def genApiUrl(
    _apicommand, 
    _apikey=apikey, 
    _ipaddr=ipaddr,
    _username=username, 
    _apidomain=cfg_getDomains.get('apidomain'),
    _page=cfg_getDomains.get('page'),
    _pagesize=cfg_getDomains.get('pagesize'),
    _sortby=cfg_getDomains.get('sortby')
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
    _fromLocal=cfg_app.get('uselocal', False),
    _colKeys=cfg_getDomains.get('colKeys', []),
    _apicommand=cfg_getDomains.get('apicommand', '')
):
    jsonResponse = None
    if (not _fromLocal or not cachefile):
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

        try:
            # Create file if doesn't exist
            if not os.path.isfile(cachefile):
                dir_path = os.path.dirname(cachefile)
                pathlib.Path(dir_path).mkdir(parents=True, exist_ok=True)
                pathlib.Path(cachefile).touch(exist_ok=True)
            # Write response to cachefile
            with open(cachefile, 'w') as cf:
                json.dump(jsonResponse, cf)
        except:
            print('Error creating cache path and/or file')
    else:
        with open(cachefile, "r") as f:
            jsonResponse = json.load(f)

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
            api_response = loadedJson.get('ApiResponse', {})
            status = api_response.get('@Status')
            if status == 'ERROR':
                print(f'\nResponse: {json.dumps(api_response)}\n')
                return -1
            else:
                domainArr = api_response.get('CommandResponse', {}).get('DomainGetListResult', {}).get('Domain')
        except:
            print('Error loading domain data')
            return -1

        numCount=1
        d=[]
        if type(domainArr) == list:
            for x in domainArr:        
                e=[numCount]
                for y in _colKeys:
                    e.append(cellFormat(x.get(y, '?missing?')))
                d.append(e)
                numCount+=1
        
        return d
    print('Error with json response\n')
    return -1

# Print report
print('')
domainsArr=getDomains(usecachefile)
if domainsArr == -1: quit()
if (type(domainsArr == list) and domainsArr):
    dprint(f'\n{json.dumps(domainsArr)}\n')
    def formatKeys(_arrIn=[]):
        output=['#']
        if (_arrIn and type(_arrIn) == list):
            for x in _arrIn:
                if (x and type(x) == str):
                    output.append(x.replace('@',''))
        return output
    print(tabulate(domainsArr, headers=formatKeys(cfg_getDomains.get('colKeys'))))
    print('')
else:
    print('Nothing to print\n')
