import streamlit as st
import pandas as pd
import random
from datetime import datetime, timedelta

from beem import Steem
from beem.account import Account
from beem.community import Communities
from beem.nodelist import NodeList
from beem.instance import set_shared_blockchain_instance
from beem.discussions import Query, Discussions

# Setup Steem nodes
nodelist = NodeList()
nodelist.update_nodes()
# nodes = nodelist.get_steem_nodes()
nodes = [
    'https://api.steemit.com',
    'https://cn.steems.top',
    'https://api.steem.buzz',
    'https://steem.61bts.com']
random.shuffle(nodes)
STEEM = Steem(node=nodes)
set_shared_blockchain_instance(STEEM)


@st.cache
def retrieve_club_members(duration=86400, community_tag='hive-161179'):
    # Get community posts for the last 24H
    club_tags = ['club5050', 'club100', 'club75']
    club_users = []

    # Get community posts
    query = Query(tag=community_tag)
    d = Discussions()
    posts = d.get_discussions('created', query, limit=10000)

    # Save posts that are less than the duration(24h)
    for post in posts:
        if post.time_elapsed().total_seconds() < duration:
            if any(tag in post['tags'] for tag in club_tags):
                if post['author'] in club_users:
                    continue
                else:
                    result = check_transfers(post['author'])
                    club_users.append({
                        'Username': post['author'],
                        'Power up': result['power_up'],
                        'Transfer': result['transfer'],
                        'Diff +,-': result['power_up'] - result['transfer'],
                    })
        else:
            break

    return club_users


@st.cache
def check_transfers(username='japansteemit'):
    # Get total transfer and power up amount for the last 30 days
    result = {
        'power_up': 0.0,
        'transfer': 0.0,
    }

    stop = datetime.utcnow() - timedelta(days=30)
    ACCOUNT = Account(username)
    account_data = ACCOUNT.history_reverse(
        stop=stop, only_ops=['transfer', 'transfer_to_vesting'])

    for d in account_data:
        if d['type'] == 'transfer' and d['to'] != username:
            result['transfer'] += float(d['amount']['amount'])
        elif d['type'] == 'transfer_to_vesting':
            if d['from'] == d['to']:
                result['power_up'] += float(d['amount']['amount'])
        else:
            continue

    result['power_up'] /= 1000
    result['transfer'] /= 1000

    return result


def style_negative_number(value, props=''):
    # Change number to red if float value is less than 0.0
    if isinstance(value, float) and value < 0:
        props = 'color:red;'

    return props


@st.cache
def get_community_list():
    communities = Communities()
    community_list = ['']

    for c in communities:
        json_data = c.json()
        community_list.append(f"{json_data['name']} - {json_data['title']}")

    return community_list


"""
# [Club Tag Members](/)
Check last 30 day transactions for active(24H) members who used club tags\n
#club5050 #club100 #club75
"""

communities = get_community_list()
option = st.selectbox(
    'Select A Community',
    communities,
    key='community_selectbox'
)
community_tag = option.split(' - ')[0]

st.write('Selected community:', community_tag)

# st.text_input(
#     "Enter Community Tag",
#     key="community_tag",
#     help='e.g. hive-161179',
#     placeholder='hive-161179')
# community_tag = st.session_state.community_tag


if community_tag:
    # data_load_state = st.text('Loading data...')
    users = retrieve_club_members(86400, community_tag)
    df = pd.DataFrame(users)

    # apply color to numbers and display dataframe
    st.dataframe(
        df.style.applymap(style_negative_number, props=''),
        height=2500)

    # data_load_state.text("Done! (using st.cache)")
else:
    st.stop()
