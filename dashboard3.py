import streamlit as st
import requests
import pandas as pd

# Enable wide mode
st.set_page_config(layout="wide")

# Inputs for the user
owner_id = st.text_input("Enter your owner_id", "578826638104498176")
week = st.number_input("Select the week", min_value=1, max_value=18, value=1)

# Function to get league_ids dynamically based on the owner_id (user_id)
def get_league_ids(owner_id):
    url = f"https://api.sleeper.app/v1/user/{owner_id}/leagues/nfl/2024"
    response = requests.get(url)
    if response.status_code == 200:
        leagues = response.json()
        # Extract all league_ids from the response
        league_ids = [league['league_id'] for league in leagues]
        return league_ids
    else:
        st.write(f"Failed to retrieve leagues: {response.status_code}")
        return []

# Retrieve league_ids for the user
league_ids = get_league_ids(owner_id)

# Function to get roster_id based on owner_id
def get_roster_id(league_id, owner_id):
    url = f"https://api.sleeper.app/v1/league/{league_id}/rosters"
    response = requests.get(url)
    rosters = response.json()
    for roster in rosters:
        if roster['owner_id'] == owner_id:
            return roster['roster_id']
    return None

# Function to get matchups for the given week and retrieve starters and points
def get_matchup_data(league_id, roster_id, week):
    url = f"https://api.sleeper.app/v1/league/{league_id}/matchups/{week}"
    response = requests.get(url)
    matchups = response.json()

    # Find your matchup and your opponent's data
    for matchup in matchups:
        if matchup['roster_id'] == roster_id:
            my_starters = matchup.get('starters', [])
            my_starters_points = matchup.get('starters_points', [])
            my_matchup_id = matchup['matchup_id']

            # Find opponent matchup based on matchup_id
            for opponent in matchups:
                if opponent['matchup_id'] == my_matchup_id and opponent['roster_id'] != roster_id:
                    opponent_starters = opponent.get('starters', [])
                    opponent_starters_points = opponent.get('starters_points', [])
                    return my_starters, my_starters_points, opponent_starters, opponent_starters_points
    return None, None, None, None

# Function to get player names from player_ids
def get_player_names(player_ids):
    url = "https://api.sleeper.app/v1/players/nfl"
    response = requests.get(url)
    players = response.json()

    player_names = []
    for player_id in player_ids:
        player_name = players.get(player_id, {}).get('full_name', 'Unknown Player')
        player_names.append(player_name)
    return player_names

# Create columns dynamically to display matchups
def create_columns(n, widths):
    return st.columns(widths)

# Loop through each league and get matchups
matchup_count = 0
columns = create_columns(3, [4, 4, 4])  # Wider columns (use larger values for column width)

for league_id in league_ids:
    roster_id = get_roster_id(league_id, owner_id)
    if roster_id:
        my_starters, my_starters_points, opponent_starters, opponent_starters_points = get_matchup_data(league_id, roster_id, week)

        if my_starters and my_starters_points and opponent_starters and opponent_starters_points:
            my_players = get_player_names(my_starters)
            opponent_players = get_player_names(opponent_starters)

            # Create a table with columns for each matchup
            with columns[matchup_count % 3]:  # Adjust % 3 to % 4 for 4 columns if needed
                st.write(f"Matchup for League {league_id}")
                
                # Create a table with the matchup details
                matchup_df = pd.DataFrame({
                    "My Starters": my_players,
                    "My Points": my_starters_points,
                    "Opponent Points": opponent_starters_points,
                    "Opponent Starters": opponent_players
                })

                st.table(matchup_df)

            matchup_count += 1

