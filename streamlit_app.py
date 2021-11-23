import streamlit as st
import pandas as pd
import numpy as np
# import random
from datetime import date, datetime, timedelta
import matplotlib.pyplot as plt
import requests
import json
from PIL import Image
import config as cfg

# from beem import Steem
from beem.account import Account
from beem.community import Communities
# from beem.nodelist import NodeList
# from beem.instance import set_shared_blockchain_instance
from beem.discussions import Query, Discussions
from beem.exceptions import AccountDoesNotExistsException


# Streamlit app settings
cfg.app_config()

# Set up steem
STEEM = cfg.setup_steem()


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
                        'Reward': result['reward_sp'],
                        'Power up': result['power_up'],
                        'Transfer': result['transfer'],
                        'Diff +,-': result['power_up'] - result['transfer'],
                    })
        else:
            break

    return club_users


@st.cache
def get_powerups(url):
    power_up = 0.0
    power_up_res = requests.get(url)
    power_up_json = power_up_res.json()

    for d in power_up_json['result']['rows']:
        if d[1] == d[2]:
            power_up += d[3]

    return power_up


@st.cache
def get_transfers(url):
    transfer = 0.0
    transfer_res = requests.get(url)
    transfer_json = transfer_res.json()

    for d in transfer_json['result']['rows']:
        transfer += d[3]

    return transfer


@st.cache
def check_transfers(username='japansteemit'):
    # Get total transfer and power up amount for the last 30 days
    result = {
        'power_up': 0.0,
        'transfer': 0.0,
        'reward_sp': 0.0,
        'club50_sp': 0.0,
        'club75_sp': 0.0,
        'club100_sp': 0.0,
        'delegations': [],
    }

    try:
        ACCOUNT = Account(username)
    except AccountDoesNotExistsException:
        return None

    reward_data = get_reward_data(username)

    # Get delegation list
    delegations = []
    for d in ACCOUNT.get_vesting_delegations():
        delegations.append(d['delegatee'])

    result['delegations'] = delegations

    # Get power up and transfer data for last 30 days
    start = date.today() - timedelta(days=30)
    stop = date.today()
    start_epoch = int(
        datetime(start.year, start.month,
                 start.day, 0, 0).timestamp())
    stop_epoch = int(
        datetime(stop.year, stop.month, stop.day, 0, 0).timestamp())

    # /transfers_api/getTransfers/{"type":"transfer","to":"steemchiller"}
    endpoint = 'https://sds.steemworld.org/transfers_api/getTransfers'
    # Check power ups
    power_up_query = {
        "type": "transfer_to_vesting",
        "from": username,
        "fromTime": start_epoch,
        "toTime": stop_epoch,
    }
    url = (
        f'{endpoint}'
        f'/{json.dumps(power_up_query)}')
    result['power_up'] = get_powerups(url)

    # Check transfers
    transfer_query = {
        "type": "transfer",
        "from": username,
        "fromTime": start_epoch,
        "toTime": stop_epoch,
    }
    url = (
        f'{endpoint}'
        f'/{json.dumps(transfer_query)}')
    result['transfer'] = get_transfers(url)

    result['reward_sp'] = reward_data['reward_sp']
    result['club50_sp'] = reward_data['club50_sp']
    result['club75_sp'] = reward_data['club75_sp']
    result['club100_sp'] = reward_data['club100_sp']

    return result


@st.cache
def get_reward_data(username='japansteemit'):
    reward_data = {
        'reward_sp': 0.0,
        'club50_sp': 0.0,
        'club75_sp': 0.0,
        'club100_sp': 0.0,
    }

    start = date.today() - timedelta(days=30)
    stop = date.today()

    start_epoch = int(
        datetime(start.year, start.month,
                 start.day, 0, 0).timestamp())
    stop_epoch = int(
        datetime(stop.year, stop.month, stop.day, 0, 0).timestamp())

    # Get reward data from API: sds.steemworld.org
    # rewards_api/getAllRewardsSums/tomoyan/1635750000-1638345599
    endpoint = 'https://sds.steemworld.org/rewards_api/getAllRewardsSums'
    url = (
        f'{endpoint}'
        f'/{username}'
        f'/{start_epoch}-{stop_epoch}')

    response = requests.get(url)
    if response:
        json_data = response.json()
        reward_vests = json_data['result']['author_reward']['vests']

        reward_sp = STEEM.vests_to_sp(reward_vests)
        reward_data['reward_sp'] = reward_sp
        reward_data['club50_sp'] = reward_sp * 0.5
        reward_data['club75_sp'] = reward_sp * 0.75
        reward_data['club100_sp'] = reward_sp

    return reward_data


def style_negative_number(value, props=''):
    # Change number to red if float value is less than 0.0
    if isinstance(value, float) and value < 0:
        props = 'background-color:red; color:white;'

    return props


def style_club_number(value, props='', powerup=0.0):
    # Change value to green if value is more than powerup
    if value <= powerup > 0:
        props = 'background-color:green; color:white;'
    else:
        props = 'background-color:red; color:white;'

    return props


@st.cache
def get_community_list():
    communities = Communities()
    community_list = ['']

    for c in communities:
        json_data = c.json()
        community_list.append(f"{json_data['name']} - {json_data['title']}")

    return community_list


def show_community_header():
    st.header("""
    [Check Club Tag Members](https://tinyurl.com/club-check/)
    """)

    st.text("""
        Power up check for active(24H) club tag community members
        Check last 30 day transactions for power ups and transfers (cash out)
    """)

    st.caption('#club5050 #club100 #club75')


def show_individual_header():
    st.header("""
    [Check Club Tag Eligibility](https://tinyurl.com/club-check/)
    """)

    st.text("""
        Check last 30 day transactions for power ups and transfers (cash out)
    """)

    username = st.text_input('Enter Username', placeholder='Username')

    return username.strip().lower()


def show_community_list(communities):
    option = st.selectbox(
        'Select A Community',
        communities,
        key='community_selectbox'
    )
    community_tag = option.split(' - ')[0]

    st.write('Selected community:', community_tag)
    return community_tag


def draw_pie_chart(data):
    pie_total = sum([data['power_up'], data['transfer']])

    st.subheader('Outgoing Delegations')
    st.caption('Not eligible if delegate to investment services or bid-bots')
    st.write(data['delegations'])

    st.subheader('Power Up At Least 50% Of Earnings')
    st.text(
        f'Earned Reward: {data["reward_sp"]:.3f} STEEM\
        Power Up Total: {data["power_up"]:.3f} STEEM')

    if data["power_up"] >= data["reward_sp"]:
        progress_value = 1.0
    else:
        progress_value = data["power_up"] / data["reward_sp"]

    st.caption(f'Club progress: {progress_value*100:.2f} %')
    st.progress(progress_value)

    data_array = np.array([
        [data["club50_sp"], data["club75_sp"], data["club100_sp"]]
    ])

    pd.set_option("display.precision", 3)
    df = pd.DataFrame(
        data_array,
        index=['Eligible Club (estimate)'],
        columns=['Club5050', 'Club75', 'Club100'])

    st.table(
        df.style.applymap(
            style_club_number, props='',
            powerup=data['power_up'])
    )

    st.subheader('Transaction Ratio (Power Up More Than Transfer)')
    if pie_total:
        labels = 'Power Up', 'Transfer'
        power_up = data['power_up'] / pie_total * 100
        transfer = data['transfer'] / pie_total * 100
        st.text(
            f'Power Up: {power_up:.3f} % ({data["power_up"]:.3f} STEEM)\
            Transfer: {transfer:.3f} % ({data["transfer"]:.3f} STEEM)')

        sizes = [power_up, transfer]
        explode = (0, 0.1)  # only "explode" the 2nd slice

        figure, ax1 = plt.subplots()
        colors = ['#f9c74f', '#f94144']
        ax1.pie(
            sizes, explode=explode, labels=labels, autopct='%1.1f%%',
            shadow=None, startangle=90, colors=colors)
        # Equal aspect ratio ensures that pie is drawn as a circle.
        ax1.axis('equal')

        st.pyplot(figure)

    else:
        labels = 'No Power Up', 'No Transfer'
        sizes = [100, 0]
        figure, ax1 = plt.subplots()
        colors = ['#d5dbdb', '#d5dbdb']  # Grey color
        ax1.pie(sizes, labels=labels, colors=colors)

        st.pyplot(figure)


def main():

    with st.expander("What is Club5050?"):
        st.write(
            """
To take part in Club5050,
power up more than 50% of the liquid rewards you earned.
Anytime you cash out or transfer away any STEEM or SBD,
you must power up an equal (or greater amount) at the same time.
\n
Use #club5050, #club100, #club75 tags on your post.
Read more: https://tinyurl.com/club5050v2

You are not eligible the club if...
* You have not made any recent power-ups.
* You are powering down, or have recently stopped powering down.
* You have bought votes from any vote buying or bid-bot services.
* You are delegating to any 'investment services' or bid-bots.
* You are not using your Steem Power to vote regularly.
            """)

    # Main Menu
    option = st.selectbox(
        'Select option ...',
        ('Home', 'Community Check', 'Individual Check'),
        key='main_option'
    )

    # Main page
    if option == 'Home':
        image = Image.open('images/main.png')
        st.image(image, caption='Powered by @tomoyan')

        st.stop()

    # Chcek club tags for community
    elif option == 'Community Check':
        show_community_header()

        communities = get_community_list()
        community_tag = show_community_list(communities)

        if community_tag:
            users = retrieve_club_members(86400, community_tag)
            pd.set_option("display.precision", 3)
            df = pd.DataFrame(users)

            # apply color to numbers and display dataframe
            st.dataframe(
                df.style.applymap(style_negative_number, props=''),
                height=2500)
        else:
            st.stop()
    # Chcek club tags for individual
    elif option == 'Individual Check':
        username = show_individual_header()

        if username:
            transfer_data = check_transfers(username)
            if transfer_data:
                draw_pie_chart(transfer_data)
            else:
                st.error('Account Does Not Exist')
                st.stop()
        else:
            st.stop()


if __name__ == '__main__':
    main()
