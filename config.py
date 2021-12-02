import streamlit as st
import random
from beem import Steem
from beem.nodelist import NodeList
from beem.instance import set_shared_blockchain_instance


# Streamlit app settings
def app_config():
    st.set_page_config(
        page_title='Steemit Club',
        page_icon="🐟",
        initial_sidebar_state="auto",
        layout="centered",
        menu_items={
            'Report a bug': "https://tinyurl.com/steemit-tomoyan",
            'About': 'Steemit club tag power up check by @tomoyan.'
        }
    )


# Set up steem node
def setup_steem():
    # Setup Steem nodes
    nodelist = NodeList()
    nodelist.update_nodes()
    # nodes = nodelist.get_steem_nodes()
    nodes = [
        'https://steemd.steemworld.org',
        'https://api.steemzzang.com',
        'https://api.justyy.com',
        'https://api.steemitdev.com',
        'https://steem.justyy.workers.dev',
        'https://api.steem.fans',
        'https://api.steemit.com',
        'https://api.steem.buzz',
        'https://steem.61bts.com',
        # 'https://cn.steems.top',
    ]

    random.shuffle(nodes)
    STEEM = Steem(node=nodes)
    set_shared_blockchain_instance(STEEM)

    return STEEM
