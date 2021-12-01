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

    try:
        # Save posts that are less than the duration(24h)
        for post in posts:
            if post.time_elapsed().total_seconds() < duration:
                if any(tag in post['tags'] for tag in club_tags):
                    if post['author'] in club_users:
                        continue
                    else:
                        tx = check_transfers(post['author'])
                        club_users.append({
                            'Username': post['author'],
                            'Reward': tx['reward_sp'],
                            'Power up': tx['power_up'],
                            'Transfer': tx['transfer'],
                            'Diff +,-': tx['power_up'] - tx['transfer'],
                        })
            else:
                break
    except (TypeError, AttributeError):
        club_users = []

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
def check_transfers(username='japansteemit', days=30):
    # Get total transfer and power up amount
    result = {
        'power_up': 0.0,
        'transfer': 0.0,
        'reward_sp': 0.0,
        'target_sp': 0.0,
        'delegations': [],
    }

    try:
        ACCOUNT = Account(username)
    except AccountDoesNotExistsException:
        return None

    reward_data = get_reward_data(username, days)

    # Get delegation list
    delegations = []
    for d in ACCOUNT.get_vesting_delegations():
        delegations.append(d['delegatee'])

    result['delegations'] = delegations

    # Get power up and transfer data
    start = date.today() - timedelta(days=days)
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
    result['target_sp'] = reward_data['target_sp']

    return result


@st.cache
def get_reward_data(username='japansteemit', days=30):
    reward_data = {
        'reward_sp': 0.0,
        'target_sp': 0.0,
    }

    start = date.today() - timedelta(days=days)
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

        if days == 30:
            reward_data['target_sp'] = reward_sp * 0.5
        elif days == 60:
            reward_data['target_sp'] = reward_sp * 0.75
        elif days == 90:
            reward_data['target_sp'] = reward_sp

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
        Check transactions for power ups and transfers (cash out)
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


def show_delegations(data):
    st.subheader('Outgoing Delegations')
    st.caption('Not eligible if delegate to investment services or bid-bots')
    st.write(data['delegations'])


def show_progress(data, club):
    if club == 50:
        st.subheader('#Club5050 (30 days)')
    elif club == 75:
        st.subheader('#Club75 (60 days)')
    elif club == 100:
        st.subheader('#Club100 (90 days)')

    # st.subheader('Power Up At Least 50% Of Earnings')
    st.text(f'Earned Reward:\n {data["reward_sp"]:.3f} STEEM')
    st.text(f'Power Up Target (est):\n {data["target_sp"]:.3f} STEEM')
    st.text(f'Powered Up Total:\n {data["power_up"]:.3f} STEEM')

    if data["power_up"] == 0:
        progress_value = 0
        st.error(f'Not eligible. Progress: {progress_value*100:.2f} %')
    elif data["power_up"] > data["target_sp"]:
        progress_value = 1.0
        st.success('Looking good 👍')
    else:
        progress_value = data["power_up"] / data["target_sp"]
        st.warning(f'Not eligible. Club progress: {progress_value*100:.2f} %')

    st.progress(progress_value)
    # st.caption(f'Progress: {progress_value*100:.2f} %')


def draw_pie_chart(data, club):
    if club == 50:
        st.subheader('Last 30 days')
    elif club == 75:
        st.subheader('Last 60 days')
    elif club == 100:
        st.subheader('Last 90 days')

    pie_total = sum([data['power_up'], data['transfer']])

    if pie_total:
        labels = 'Power Up', 'Transfer'
        power_up = data['power_up'] / pie_total * 100
        transfer = data['transfer'] / pie_total * 100
        st.text(
            f'Power Up:\n {power_up:.3f}%\n ({data["power_up"]:.3f} STEEM)')
        st.text(
            f'Transfer:\n {transfer:.3f}%\n ({data["transfer"]:.3f} STEEM)')

        sizes = [power_up, transfer]
        explode = (0, 0.1)  # only "explode" the 2nd slice

        figure, ax1 = plt.subplots()
        colors = ['#f9c74f', '#f94144']
        ax1.pie(
            sizes, explode=explode, labels=labels, autopct='%1.1f%%',
            shadow=None, startangle=90, colors=colors, radius=0.5)
        # Equal aspect ratio ensures that pie is drawn as a circle.
        ax1.axis('equal')

        if data['power_up'] == 0:
            st.error('No power up')
        elif data['power_up'] < data['transfer']:
            st.warning('Need more power up')
        elif data['power_up'] >= data['transfer']:
            st.success('Looking good 👍')

        st.pyplot(figure)

    else:
        labels = 'No Power Up', 'No Transfer'
        sizes = [100, 0]
        figure, ax1 = plt.subplots()
        colors = ['#d5dbdb', '#d5dbdb']  # Grey color
        ax1.pie(sizes, labels=labels, colors=colors)

        st.error('No power up')

        st.pyplot(figure)


def _set_block_container_width(
    max_width: int = 1200,
    max_width_100_percent: bool = False,
    padding_top: int = 5,
    padding_right: int = 1,
    padding_left: int = 1,
    padding_bottom: int = 10,
):
    if max_width_100_percent:
        max_width_str = f"max-width: 100%;"
    else:
        max_width_str = f"max-width: {max_width}px;"
    st.markdown(
        f"""
<style>
    .reportview-container .main .block-container{{
        {max_width_str}
        padding-top: {padding_top}rem;
        padding-right: {padding_right}rem;
        padding-left: {padding_left}rem;
        padding-bottom: {padding_bottom}rem;
    }}
</style>
""",
        unsafe_allow_html=True,
    )


def main():
    _set_block_container_width()

    with st.expander("What is Club5050?"):
        st.write(
            """
To take part in #club5050,
you must be powering up at least 50% of your earnings,
and over the previous 30 days,
any cash-outs or transfers must be matched by equal or greater power-ups.
\n
Use #club5050, #club100, #club75 tags on your post if you are eligible.\n
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
            transfer_data_30 = check_transfers(username, 30)

            if transfer_data_30:
                show_delegations(transfer_data_30)

                transfer_data_60 = check_transfers(username, 60)
                transfer_data_90 = check_transfers(username, 90)

                st.subheader(
                    '* Have you powered up at least 50% of your earnings?')
                st.caption('Power up your eanings for #club5050 tag')

                col1, col2, col3 = st.columns(3)
                with col1:
                    show_progress(transfer_data_30, 50)
                with col2:
                    show_progress(transfer_data_60, 75)
                with col3:
                    show_progress(transfer_data_90, 100)

                st.subheader('* Have you powered up more than you transfered?')
                st.caption('Any transfers must be matched by power-ups')

                col1, col2, col3 = st.columns(3)
                with col1:
                    draw_pie_chart(transfer_data_30, 50)
                with col2:
                    draw_pie_chart(transfer_data_60, 75)
                with col3:
                    draw_pie_chart(transfer_data_90, 100)
            else:
                st.error('Account Does Not Exist')
                st.stop()
        else:
            st.stop()


if __name__ == '__main__':
    main()
