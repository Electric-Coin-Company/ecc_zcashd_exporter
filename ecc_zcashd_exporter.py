#!/usr/bin/env python3

# /************************************************************************
#  File: ecc_zcashd_exporter.py
#  Author: mdr0id
#  Date: 6/1/2022
#  Description:  exporter for zcashd
#  Docs: RPC docs - https://zcash.github.io/rpc
#
#  Usage: 
#
#  Known Bugs:
#
# ************************************************************************/

from cmath import log
import json
import logging
import time
import subprocess
import os
import sys
import pycurl
import geocoder
import pygeohash as pgh
from prometheus_client import start_http_server, Summary, Gauge, Enum, Info, Counter
from shutil import which
from dotenv import load_dotenv
from slickrpc import Proxy
from slickrpc.exc import RpcException
from slickrpc.exc import RpcInWarmUp

class ZcashExporter:

    def __init__(self, app_port=9200, polling_interval_seconds=5, polling_interval_startup_seconds=5,
                 rpc_user="user", rpc_password="passw", rpc_host="127.0.0.1", rpc_port=8232, rpc_network="mainnet"
                ):
        self.app_port = app_port
        self.polling_interval_startup_seconds = polling_interval_startup_seconds
        self.polling_interval_seconds = polling_interval_seconds
        self.rpc_user = rpc_user
        self.rpc_password = rpc_password
        self.rpc_host = rpc_host
        self.rpc_port = rpc_port
        self.rpc_network = rpc_network

        self.node_network= None #used to sanity check cacheing state issues across env

        """
         RPC Blockchain
        """
        # getblockchaininfo
        self.ZCASH_CHAIN = Info('zcash_chain', 'current network name as defined in BIP70 (main, test, regtest)')
        self.ZCASH_BLOCKS = Gauge('zcash_blocks', 'the current number of blocks processed in the server')
        self.ZCASH_IBD = Gauge('zcash_initial_block_download_complete', 'true if the initial download of the blockchain is complete')
        self.ZCASH_HEADERS = Gauge('zcash_headers', 'Zcashd current number of headers validated')
        self.ZCASH_BEST_BLOCK_HASH = Info('zcash_bestblockhash','the hash of the currently best block') #might need to change type
        self.ZCASH_DIFFICULTY= Gauge('zcash_difficulty', 'the current difficulty')
        self.ZCASH_VERIFICATION_PROG = Gauge('zcash_verification_progress', 'Zcashd estimate of chain verification progress' )
        self.ZCASH_ESTIMATED_HEIGHT = Gauge('zcash_estimated_height', 'Zcashd if syncing, the estimated height of the chain, else the current best height4 ')
        self.ZCASH_CHAINWORK = Gauge('zcash_chainwork', 'total amount of work in active chain, in hexadecimal')
        self.ZCASH_CHAIN_DISK_SIZE = Gauge('zcash_chain_size_on_disk', 'the estimated size of the block and undo files on disk')
        self.ZCASH_COMMITMENTS = Gauge('zcash_commitments', 'the current number of note commitments in the commitment tree')
        
        # getmempoolinfo
        self.ZCASH_MEMPOOL_SIZE = Gauge('zcash_mempool_size', 'Zcash current mempool tx count')
        self.ZCASH_MEMPOOL_BYTES = Gauge('zcash_mempool_bytes', 'Zcash sum of tx sizes')
        self.ZCASH_MEMPOOL_USAGE = Gauge('zcash_mempool_usage', 'Zcash total memory usage for the mempool') 

        """
         RPC Control
        """ 
        # getinfo
        self.ZCASH_VERSION = Info('zcashd_server_version', 'Zcash server version')
        self.ZCASH_BUILD = Info('zcashd_build_version', 'Zcash build number')
        self.ZCASH_SUBVERSION = Info('zcashd_subversion', 'Zcash server sub-version')
        self.ZCASH_PROTOCOL_VERSION = Info('zcashd_protocol_version', 'Zcash protocol version')
        self.ZCASH_WALLET_VERSION = Info('zcashd_wallet_version', 'Zcash wallet version')

        # getmemoryinfo
        self.ZCASH_MEM_USED = Gauge("zcash_mem_used", 'Number of bytes used')
        self.ZCASH_MEM_FREE = Gauge("zcash_mem_free", 'Number of bytes available in current arenas')
        self.ZCASH_MEM_TOTAL = Gauge("zcash_mem_total", 'Total number of bytes managed')
        self.ZCASH_MEM_LOCKED = Gauge("zcash_mem_locked", 'Amount of bytes that succeeded locking. If this number is smaller than total, locking pages failed at some point and key data could be swapped to disk.')
        self.ZCASH_MEM_CHUNKS_USED = Gauge("zcash_mem_chunks_used", 'Number allocated chunks')
        self.ZCASH_MEM_CHUNKS_FREE = Gauge("zcash_mem_chunks_free", 'Number unused chunks')

        """
         RPC Network
        """
        # getdeprecationinfo
        self.ZCASH_DEPRECATION_HEIGHT= Gauge('zcash_deprecation', 'Zcash mainnet block height at which this version will deprecate and shut down')

        # getnettotals
        self.ZCASH_TOTAL_BYTES_RECV = Gauge("zcash_total_bytes_recv", "Total bytes received")
        self.ZCASH_TOTAL_BYTES_SENT = Gauge("zcash_total_bytes_sent", "Total bytes sent")

    def run_startup_loop(self):
        """startup polling loop to ensure valid zcashd state before fetching metrics"""
        logging.info("Startup loop")
        api = Proxy(f"http://{self.rpc_user}:{self.rpc_password}@{self.rpc_host}:{self.rpc_port}")
        
        #Get startup state of zcashd node
        logging.info("Checking if zcashd is in valid state...")
        zcash_info = None
        while True:
            try:
                zcash_info = api.getblockchaininfo()
            except pycurl.error:
                logging.info("Zcashd has not been started yet. Retrying...")
                time.sleep(self.polling_interval_startup_seconds)
            except RpcInWarmUp:
                logging.info("Zcashd is in RpcInWarmUp state. Retrying...")
                time.sleep(self.polling_interval_startup_seconds)
            except ValueError:
                logging.info("Value error likely indicating bad env load")
                time.sleep(self.polling_interval_startup_seconds)
            else:
                break
        
        if(zcash_info['chain'] == 'main'):
            logging.info("Zcashd node is on mainnet")
            self.ZCASH_CHAIN.info({'zcash_chain': "mainnet"})
            self.node_network = "mainnet"
        elif(zcash_info['chain'] == 'test'):
            logging.info("Zcashd node is on testnet")
            self.ZCASH_CHAIN.info({'zcash_chain': "testnet"})
            self.node_network = "testnet"
        elif(zcash_info['chain'] == 'regtest'):
            logging.info("Zcashd node is on regtest")
            self.ZCASH_CHAIN.info({'zcash_chain': "regtest"})
            self.node_network = "regtest"
        else:
            logging.warning("Zcashd node is not mainnet, testnet, or regtest")
            self.ZCASH_CHAIN.info({'zcash_chain': "other"})
            self.node_network = "other"

    def run_loop(self):
        while True:
            self.fetch()
            time.sleep(self.polling_interval_startup_seconds)

    def fetch(self):
        """
        Get metrics from zcashd and refresh Prometheus metrics with new data.
        @TODO Change this to be a command set relative to env loaded 
              (e.g. don't call miner RPCs for none miner configs;
              regression testing for RPCs; combos/perm of RPCS on none wallet configs)
        """
        api = Proxy(f"http://{self.rpc_user}:{self.rpc_password}@{self.rpc_host}:{self.rpc_port}")
        logging.info("calling zcash RPC endpoint")
        try:
            zcash_info = api.getinfo()
            self.ZCASH_VERSION.info({'serverversion': str(zcash_info['version'])})
            self.ZCASH_PROTOCOL_VERSION.info({'protocolversion': str(zcash_info['protocolversion'])})
            self.ZCASH_WALLET_VERSION.info({'walletversion': str(zcash_info['walletversion'])})
        except Exception as e:
            logging.info("missed zcash RPC endpoint call")
       


        #self.ZCASH_NETWORK_TYPE.state(str(self.node_network))
        
def main():
    logging.basicConfig(format='%(asctime)s - %(message)s', level=logging.INFO)
    #Get configuration from .env
    logging.info("Loading .env file.")
    if(load_dotenv() == True):
        logging.info(".env loaded successfully")
    else:
        logging.error(".env did not load correctly.")
        return 1

    zcash_exporter = ZcashExporter(
        app_port=int(os.getenv("ZEXPORTER_PORT")),
        polling_interval_startup_seconds=int(os.getenv("ZEXPORTER_POLLING_INTERVAL_STARTUP")),
        polling_interval_seconds=int(os.getenv("ZEXPORTER_POLLING_INTERVAL")),
        rpc_user=os.getenv("ZCASHD_RPCUSER"),
        rpc_password=os.getenv("ZCASHD_RPCPASSWORD"),
        rpc_host=os.getenv("ZCASHD_RPCHOST"),
        rpc_port=int(os.getenv("ZCASHD_RPCPORT")),
        rpc_network=os.getenv("ZCASHD_NETWORK")
    )

    start_http_server(int(os.getenv("ZEXPORTER_PORT")))
    zcash_exporter.run_startup_loop()
    zcash_exporter.run_loop()

if __name__ == "__main__":
    main()