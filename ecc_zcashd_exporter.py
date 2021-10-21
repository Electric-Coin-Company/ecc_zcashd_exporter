#!/usr/bin/env python

import json
import time
import subprocess
import os
import sys
import pycurl
from prometheus_client import start_http_server, Summary, Gauge, Enum, Info
from shutil import which
from dotenv import load_dotenv
from slickrpc import Proxy
from slickrpc.exc import RpcException
from slickrpc.exc import RpcInWarmUp

# Create Prometheus metrics to track zcashd stats.
ZCASH_BUILD_VERSION = Info('zcash_build_version', 'Zcash build description information')
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

    #Start prom client
    start_http_server(9100)
    
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
            print("Zcashd not full started. Retrying...")
            time.sleep(2)
        else:
            break

    
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