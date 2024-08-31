# py-nc-getdomains
helpful utility to gather your domains with namecheap api

# bash
./domainlist.sh

# py
python3 getDomains.py

# What to expect
Running for the first time and/or without a .config.ini will simply prompt you to enter the needed information and then subsequently store within local .config.ini

# Output
Output in theory should be a nice tabulated overview

  #  Name                                  Expires     IsExpired    AutoRenew    WhoisGuard    IsOurDNS
---  ------------------------------------  ----------  -----------  -----------  ------------  ----------
  1  aaaaaaa.com                           10/01/2024  -            x            x             -
  2  bbbbbbbbbbb.org                       11/01/2024  -            -            x             -
  3  ccccccccc.cc                          12/01/2024  -            x            x             -
