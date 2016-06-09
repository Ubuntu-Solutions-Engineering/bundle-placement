#!/usr/bin/python3

from bundleplacer.charmstore_api import CharmStoreID

ids = ['mysql',
       'mysql-9',
       'nova-compute',
       'nova-cloud-controller',
       'cs:~adam-stokes/trusty/ghost',
       'cs:~openstack-charmers-next/xenial/lxd',
       'cs:~openstack-charmers-next/xenial/nova-compute-12',
       'cs:~openstack-charmers-next/xenial/nova-compute',
       'cs:bundle/openstack-base-40']

for i in ids:
    print(80*'-')
    print(i)
    csid = CharmStoreID(i)
    print(repr(csid))
    print(csid.as_str_without_rev())
    print(csid.as_str())
