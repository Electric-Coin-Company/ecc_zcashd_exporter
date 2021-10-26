#!/usr/bin/env python3

import json
import time
import subprocess
import os
import sys
import pycurl
import geocoder
import pygeohash as pgh
from prometheus_client import start_http_server, Summary, Gauge, Enum, Info
from shutil import which
from dotenv import load_dotenv
from slickrpc import Proxy
from slickrpc.exc import RpcException
from slickrpc.exc import RpcInWarmUp

# Create Prometheus metrics to track zcashd stats.
ZCASH_BUILD_INFO = Info('zcashd_build_info', 'Zcash build description information')
#ZCASH_LATITUDE = Info('zcash_node_lat_location', 'Zcashd node latitude point')
#ZCASH_LONGITUDE = Info('zcash_node_long_location', 'Zcashd node longitude point')
ZCASH_GEOHASH = Info('zcash_node_geohash_location', 'Zcashd node geohash')
ZCASH_NETWORK_TYPE = Enum('zcash_network_type', 'Zcash network type',
                           states=['mainnet', 'testnet', 'regtest'])
ZCASH_SYNCED = Enum('zcash_synced', 'Zcashd has completed initial block download',
                     states=['not_synced', 'synced'])                          
ZCASH_BLOCKS = Gauge('zcash_blocks', 'Block height')


def get_zcash_cli_path():
    return which('zcash-cli')

def get_zcashd_path():
    return which('zcashd')

def run_zcash_cli(cmd):
    zcash = subprocess.Popen([ZCASH_CLI_PATH, cmd], stdout=subprocess.PIPE, stdin=subprocess.PIPE, stderr=subprocess.PIPE)
    output = zcash.communicate()[0]
    return json.loads(output.decode('utf-8'))

def run_zcashd(cmd):
    zcash = subprocess.Popen([ZCASH_CLI_PATH, cmd], stdout=subprocess.PIPE, stdin=subprocess.PIPE, stderr=subprocess.PIPE)
    output = zcash.communicate()[0]
    return json.loads(output.decode('utf-8'))

ZCASH_CLI_PATH = str(get_zcash_cli_path())
ZCASHD_PATH = str(get_zcashd_path())

if __name__ == '__main__':
    #Get configuration from .env
    load_dotenv()
    RPC_USER = os.getenv("ZCASHD_RPCUSER")
    RPC_PASSWORD = os.getenv("ZCASHD_RPCPASSWORD")
    RPC_PORT = os.getenv("ZCASHD_RPCPORT")

    #Get geo hash for grafana geomap panel
    g = geocoder.ip('me')
    lat_p = g.latlng[0]
    long_p =  g.latlng[1]
    geohash = pgh.encode(lat_p, long_p)

    #Start prom client
    #@TODO make port configurable 
    start_http_server(9100)
    ZCASH_GEOHASH.info({'geohash': str(geohash)})

    #Get connection to zcashd
    #@TODO case mode for zcash_cli or http curl (container vs local deploy details)
    api = Proxy(f"http://{RPC_USER}:{RPC_PASSWORD}@127.0.0.1:{RPC_PORT}")
    
    #Get startup state of zcashd node
    #zcash_info = run_zcash_cli('getinfo')
    while True:
        try:
            zcash_info = api.getinfo()
        except pycurl.error:
            print("Zcashd has not been started yet. Retrying...")
            time.sleep(5)
        except RpcInWarmUp:
            print("Zcashd is in start up state. Retrying...")
            time.sleep(2)
        else:
            break

    ZCASH_BUILD_INFO.info({'version': zcash_info['version']})
    
    if(zcash_info['testnet'] == 'false'):
        ZCASH_NETWORK_TYPE.state('mainnet')
    else:
        ZCASH_NETWORK_TYPE.state('testnet')
    
    #Need to debug dict parse fail from localhost
    #ZCASH_BUILD_VERSION.info(zcash_info)
    
    print("VERSION:", zcash_info['version'])

    while True:
        #zcash_info = run_zcashd('getinfo')
        zcash_info = api.getinfo()
        ZCASH_BLOCKS.set(zcash_info['blocks'])
        time.sleep(2)