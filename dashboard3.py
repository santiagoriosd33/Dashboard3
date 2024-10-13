import streamlit as st
import requests
import json
import os
import pandas as pd

# Enable wide mode
st.set_page_config(layout="wide")

# Sidebar navigation for switching between dashboards
dashboard = st.sidebar.radio(
    "Select Dashboard",
    ("Matchup Dashboard", "Opponent Player Analysis")
)

# Auto-refresh using JavaScript (every 100 seconds)
st.markdown(
    """
    <script>
    function refreshPage() {
        setTimeout(function() {
            window.location.reload();
        }, 100000);  // Refresh every 100 seconds
    }
    refreshPage();
    </script>
    """,
    unsafe_allow_html=True
)

# Inputs for the user
owner_id = st.text_input("Enter your owner_id", "578826638104498176")
week = st.number_input("Select the week", min_value=1, max_value=18, value=1)

# Cache player info with Streamlit caching mechanism
@st.cache_data
def download_player_info():
    url = "https://api.sleeper.app/v1/players/nfl"
    response = requests.get(url)
    players = response.json()

    # Save player data to a local JSON file for future use
    with open('players.json', 'w') as f:
        json.dump(players, f)
    
    return players

# Load player data from local storage or download if not present
def load_local_player_info():
    if os.path.exists('players.json'):
        with open('players.json', 'r') as f:
            players = json.load(f)
        return players
    else:
        return download_player_info()

# Load players (either from local or download)
players_info = load_local_player_info()

# Function to get league_ids and league names dynamically based on the owner_id (user_id)
def get_leagues(owner_id):
    url = f"https://api.sleeper.app/v1/user/{owner_id}/leagues/nfl/2024"
    response = requests.get(url)
    if response.status_code == 200:
        leagues = response.json()
        league_data = [{'league_id': league['league_id'], 'name': league['name']} for league in leagues]
        return league_data
    else:
        st.write(f"Failed to retrieve leagues: {response.status_code}")
        return []

# Retrieve league_ids and names for the user
leagues = get_leagues(owner_id)

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

# Use the cached player info in your functions
def get_player_names(player_ids):
    player_names = []
    for player_id in player_ids:
        player_name = players_info.get(player_id, {}).get('full_name', 'Unknown Player')
        player_names.append(player_name)
    return player_names

# Function to add a total row at the top of each matchup DataFrame
def add_total_row(df, my_starters_points, opponent_starters_points):
    total_my_points = sum(my_starters_points)
    total_opponent_points = sum(opponent_starters_points)
    
    total_row = pd.DataFrame({
        "My Starters": ["Total"],
        "My Points": [f"{total_my_points:.2f}"],
        "Opponent Points": [f"{total_opponent_points:.2f}"],
        "Opponent Starters": ["Total"]
    })
    
    # Concatenate the total row at the top of the DataFrame
    df = pd.concat([total_row, df]).reset_index(drop=True)
    return df

# Function to create opponent player analysis without summing the points
def create_opponent_player_analysis(leagues, owner_id, week):
    opponent_player_list = []

    # Loop through each league to get opponent players and points
    for league in leagues:
        roster_id = get_roster_id(league['league_id'], owner_id)
        if roster_id:
            _, _, opponent_starters, opponent_starters_points = get_matchup_data(league['league_id'], roster_id, week)

            if opponent_starters and opponent_starters_points:
                for i, player_id in enumerate(opponent_starters):
                    player_name = get_player_names([player_id])[0]
                    player_points = opponent_starters_points[i]

                    # Append each occurrence of the player with its points to the list
                    opponent_player_list.append({
                        'Player': player_name,
                        'Points Against': round(player_points, 2)  # Ensure points are rounded to 2 decimals
                    })

    # Convert to DataFrame for easy viewing
    player_analysis_df = pd.DataFrame(opponent_player_list)

    # Group by Player to count how many times you've played against them
    player_analysis_df['Times Played Against'] = player_analysis_df.groupby('Player')['Player'].transform('count')

    # Sort by Times Played Against or Points Against as desired
    player_analysis_df = player_analysis_df.sort_values(by=['Times Played Against', 'Points Against'], ascending=[False, False])

    # Drop duplicates for the count column to show distinct rows
    player_analysis_df = player_analysis_df.drop_duplicates()

    return player_analysis_df

# Logic for displaying Matchup Dashboard
if dashboard == "Matchup Dashboard":
    # Create columns dynamically to display matchups
    def create_columns(n, widths):
        return st.columns(widths)

    # Loop through each league and get matchups
    matchup_count = 0
    columns = create_columns(3, [4, 4, 4])  # Wider columns (use larger values for column width)

    for league in leagues:
        roster_id = get_roster_id(league['league_id'], owner_id)
        if roster_id:
            my_starters, my_starters_points, opponent_starters, opponent_starters_points = get_matchup_data(league['league_id'], roster_id, week)

            if my_starters and my_starters_points and opponent_starters and opponent_starters_points:
                my_players = get_player_names(my_starters)
                opponent_players = get_player_names(opponent_starters)

                # Create a table with columns for each matchup
                with columns[matchup_count % 3]:  # Adjust % 3 to % 4 for 4 columns if needed
                    st.write(f"Matchup for {league['name']}")  # Display league name
                    
                    # Create a table with the matchup details and round points
                    matchup_df = pd.DataFrame({
                        "My Starters": my_players,
                        "My Points": [f"{point:.2f}" for point in my_starters_points],  # Format to 2 decimals
                        "Opponent Points": [f"{point:.2f}" for point in opponent_starters_points],  # Format to 2 decimals
                        "Opponent Starters": opponent_players
                    })

                    # Add total row at the top of the table
                    matchup_df = add_total_row(matchup_df, my_starters_points, opponent_starters_points)

                    st.table(matchup_df)

                matchup_count += 1

# Logic for displaying Opponent Player Analysis
elif dashboard == "Opponent Player Analysis":
    st.write("Opponent Player Analysis")
    player_analysis_df = create_opponent_player_analysis(leagues, owner_id, week)

    # Display the analysis table sorted by "Times Played Against" and "Points Against"
    st.table(player_analysis_df)
