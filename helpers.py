import json, os, requests, pathlib, configparser, datetime

def get_public_ip():
    try:
        response = requests.get('https://api.ipify.org')
        public_ip = response.text.strip()
        return public_ip
    except requests.RequestException as e:
        print(f"Error: {e}")
        return None
    
def config_init(config_file, _defaults):
    if not _defaults: return [None, None]

    # Create config file if doesn't exist
    if not os.path.isfile(config_file):
        pathlib.Path(config_file).touch(exist_ok=True)

    # Load configuration file
    c = configparser.ConfigParser()
    if os.path.isfile(config_file):
        c.read(config_file)

    # Setup config elements
    a = {}
    for section in _defaults.keys():
        def_sect = _defaults.get(section, {})
        for s in def_sect.keys() or []:
            d = def_sect.get(s)
            if section not in a: a[section] = {}
            if section not in c.sections() or []: c.add_section(section)
            v = None
            if type(d) is bool:
                v = c.getboolean(section, s, fallback=d)
                c.set(section, s, str(v))
            elif type(d) is datetime.datetime:
                v = datetime.datetime.strptime(str(c.get(section, s, fallback=d)), a.get('App', {}).get('datetimeformat') or c.get('App', {}).get('datetimeformat'))
                c.set(section, s, str(v))
            elif type(d) is int:
                v = c.getint(section, s, fallback=d)
                c.set(section, s, str(v))
            elif type(d) is str:
                v = c.get(section, s, fallback=d)
                c.set(section, s, v.replace('%','%%'))
            elif type(d) is list:
                v = json.loads(c.get(section, s, fallback=json.dumps(d)))
                c.set(section, s, json.dumps(v))
            a[section][s] = v
            

    # Write changes back to the file
    with open(config_file, 'w') as configfile:
        c.write(configfile)

    return [c, a]