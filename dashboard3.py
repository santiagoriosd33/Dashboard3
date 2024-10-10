import streamlit as st
import requests
import pandas as pd
import time

# Enable wide mode
st.set_page_config(layout="wide")

# Sidebar navigation for switching between dashboards
dashboard = st.sidebar.radio(
    "Select Dashboard",
    ("Matchup Dashboard", "Opponent Player Analysis")
)

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

# Function to create opponent player analysis without summing the points
def create_opponent_player_analysis(league_ids, owner_id, week):
    opponent_player_list = []

    # Loop through each league to get opponent players and points
    for league_id in league_ids:
        roster_id = get_roster_id(league_id, owner_id)
        if roster_id:
            _, _, opponent_starters, opponent_starters_points = get_matchup_data(league_id, roster_id, week)

            if opponent_starters and opponent_starters_points:
                for i, player_id in enumerate(opponent_starters):
                    player_name = get_player_names([player_id])[0]
                    player_points = opponent_starters_points[i]

                    # Append each occurrence of the player with its points to the list
                    opponent_player_list.append({
                        'Player': player_name,
                        'Points Against': player_points
                    })

    # Convert to DataFrame for easy viewing
    player_analysis_df = pd.DataFrame(opponent_player_list)

    # Group by Player to count how many times you've played against them
    player_analysis_df['Times Played Against'] = player_analysis_df.groupby('Player')['Player'].transform('count')

    # Sort by Times Played Against or Points Against as desired
    player_analysis_df = player_analysis_df.sort_values(by=['Times Played Against', 'Points Against'], ascending=[False, False])

    # Drop duplicates for the count column to show distinct rows
    player_analysis_df = player_analysis_df.drop_duplicates()

    # Round points to 2 decimal places
    player_analysis_df['Points Against'] = player_analysis_df['Points Against'].round(2)

    return player_analysis_df

# Logic for displaying Matchup Dashboard
if dashboard == "Matchup Dashboard":
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
                    
                    # Create a table with the matchup details and round points
                    matchup_df = pd.DataFrame({
                        "My Starters": my_players,
                        "My Points": pd.Series(my_starters_points).round(2),
                        "Opponent Points": pd.Series(opponent_starters_points).round(2),
                        "Opponent Starters": opponent_players
                    })

                    st.table(matchup_df)

                matchup_count += 1

# Logic for displaying Opponent Player Analysis
elif dashboard == "Opponent Player Analysis":
    st.write("Opponent Player Analysis")
    player_analysis_df = create_opponent_player_analysis(league_ids, owner_id, week)

    # Display the analysis table sorted by "Times Played Against" and "Points Against"
    st.table(player_analysis_df)

# Auto-refresh every 100 seconds
time.sleep(100)
st.experimental_rerun()
