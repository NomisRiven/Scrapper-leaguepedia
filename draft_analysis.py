"""
Draft Analysis Module for League of Legends
============================================

This module provides functions to analyze draft data from Leaguepedia,
including pick order statistics, champion statistics by role, and draft visualizations.

Author: Nono
Date: January 2026
"""

import pandas as pd
import mwclient
from collections import defaultdict


# ============================================================================
# LEAGUEPEDIA CONNECTION & DATA RETRIEVAL
# ============================================================================

def connect_to_leaguepedia(username="Bagzzzzz@MrRobot", password="3l470f1jkabsq7tg3pl4vlgbph1jog5q"):
    """
    Connects to Leaguepedia API
    
    Args:
        username: Leaguepedia bot username
        password: Leaguepedia bot password
        
    Returns:
        site: mwclient Site object
    """
    site = mwclient.Site('lol.fandom.com', path='/')
    site.login(username, password)
    print("✅ Connexion établie avec Leaguepedia")
    return site


def cargo_query(site, tables, fields, where='', join_on='', group_by='', order_by='', limit=None):
    """
    Executes a Cargo query on Leaguepedia
    
    Args:
        site: mwclient Site object
        tables: Table name(s)
        fields: Fields to retrieve
        where: WHERE clause
        join_on: JOIN clause
        group_by: GROUP BY clause
        order_by: ORDER BY clause
        limit: Result limit
        
    Returns:
        list: Query results
    """
    cargo_params = {
        'action': 'cargoquery',
        'format': 'json',
        'tables': tables,
        'fields': fields,
    }
    
    if where:
        cargo_params['where'] = where
    if join_on:
        cargo_params['join_on'] = join_on
    if group_by:
        cargo_params['group_by'] = group_by
    if order_by:
        cargo_params['order_by'] = order_by
    if limit:
        cargo_params['limit'] = limit
    
    response = site.api(**cargo_params)
    
    if 'cargoquery' in response:
        results = []
        for item in response['cargoquery']:
            results.append(item['title'])
        return results
    return []


def scrape_draft_data(site, tournament_names, limit=None):
    """
    Retrieves complete draft data for multiple tournaments
    
    Args:
        site: mwclient Site object
        tournament_names: List of tournament names
        limit: Match limit per tournament (None = all)
    
    Returns:
        pandas.DataFrame: DataFrame with all draft info
    """
    
    all_games = []
    all_picksbans = []
    
    for tournament_name in tournament_names:
        print(f"\n{'='*60}")
        print(f"🔍 Traitement du tournoi: {tournament_name}")
        print(f"{'='*60}")
        
        print(f"\n🔍 Étape 1: Récupération des matchs...")
        
        games_response = cargo_query(
            site,
            tables='ScoreboardGames',
            fields='GameId, Team1, Team2, Winner, Patch, DateTime_UTC, MatchHistory',
            where=f"Tournament='{tournament_name}'",
            order_by='DateTime_UTC ASC',
            limit=limit
        )
        
        if not games_response:
            print(f"❌ Aucun match trouvé pour {tournament_name}.")
            continue
        
        print(f"✅ {len(games_response)} matchs trouvés")
        
        df_games = pd.DataFrame(games_response)
        game_ids = df_games['GameId'].tolist()
        
        print(f"\n🔍 Étape 2: Récupération des picks & bans...")
        
        batch_size = 200
        tournament_picksbans = []
        
        for i in range(0, len(game_ids), batch_size):
            batch_ids = game_ids[i:i+batch_size]
            game_ids_str = "','".join(batch_ids)
            
            print(f"   Requête {i//batch_size + 1}/{(len(game_ids)-1)//batch_size + 1}...", end=' ')
            
            picksbans_response = cargo_query(
                site,
                tables='PicksAndBansS7',
                fields=(
                    'GameId, Team1, Team2, Winner, '
                    'Team1Ban1, Team1Ban2, Team1Ban3, Team1Ban4, Team1Ban5, '
                    'Team1Pick1, Team1Pick2, Team1Pick3, Team1Pick4, Team1Pick5, '
                    'Team1Role1, Team1Role2, Team1Role3, Team1Role4, Team1Role5, '
                    'Team2Ban1, Team2Ban2, Team2Ban3, Team2Ban4, Team2Ban5, '
                    'Team2Pick1, Team2Pick2, Team2Pick3, Team2Pick4, Team2Pick5, '
                    'Team2Role1, Team2Role2, Team2Role3, Team2Role4, Team2Role5'
                ),
                where=f"GameId IN ('{game_ids_str}')",
                order_by='GameId',
                limit=5000
            )
            
            if picksbans_response:
                tournament_picksbans.extend(picksbans_response)
                print(f"✓ ({len(picksbans_response)} matchs)")
            else:
                print("✗")
        
        if tournament_picksbans:
            all_games.append(df_games)
            all_picksbans.extend(tournament_picksbans)
            print(f"✅ {tournament_name}: {len(tournament_picksbans)} matchs avec picks/bans")
        else:
            print(f"❌ Aucune donnée de picks/bans pour {tournament_name}.")
    
    if not all_games or not all_picksbans:
        print("\n❌ Aucune donnée récupérée pour aucun tournoi.")
        return None
    
    print(f"\n{'='*60}")
    print(f"🔍 Étape 3: Fusion des données de tous les tournois...")
    print(f"{'='*60}")
    
    df_games_combined = pd.concat(all_games, ignore_index=True)
    df_picksbans = pd.DataFrame(all_picksbans)
    
    df_final = pd.merge(
        df_games_combined[['GameId', 'Patch', 'MatchHistory']],
        df_picksbans,
        on='GameId',
        how='left'
    )
    
    column_order = [
        'GameId', 'Patch', 'Team1', 'Team2', 'Winner', 'MatchHistory',
        'Team1Ban1', 'Team1Ban2', 'Team1Ban3', 'Team1Ban4', 'Team1Ban5',
        'Team1Pick1', 'Team1Role1',
        'Team1Pick2', 'Team1Role2',
        'Team1Pick3', 'Team1Role3',
        'Team1Pick4', 'Team1Role4',
        'Team1Pick5', 'Team1Role5',
        'Team2Ban1', 'Team2Ban2', 'Team2Ban3', 'Team2Ban4', 'Team2Ban5',
        'Team2Pick1', 'Team2Role1',
        'Team2Pick2', 'Team2Role2',
        'Team2Pick3', 'Team2Role3',
        'Team2Pick4', 'Team2Role4',
        'Team2Pick5', 'Team2Role5'
    ]
    
    existing_cols = [col for col in column_order if col in df_final.columns]
    df_final = df_final[existing_cols]
    
    # Normalize patch format
    df_final['Patch'] = df_final['Patch'].apply(normalize_patch)
    
    print(f"\n✅ TOTAL: Données de draft assemblées pour {len(df_final)} matchs")
    
    return df_final


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def normalize_champion(champ_name):
    """Normalizes champion name for DDragon URL"""
    if pd.isna(champ_name) or champ_name == "":
        return ""
    
    special_cases = {
        "Wukong": "MonkeyKing",
        "Miss Fortune": "MissFortune",
        "Jarvan IV": "JarvanIV",
        "K'Sante": "KSante",
        "Nunu & Willump": "Nunu",
        "Tahm Kench": "TahmKench",
        "Twisted Fate": "TwistedFate",
        "Xin Zhao": "XinZhao",
        "Lee Sin": "LeeSin",
        "Master Yi": "MasterYi",
        "Dr. Mundo": "DrMundo",
        "Aurelion Sol": "AurelionSol",
        "Cho'Gath": "Chogath",
        "Kai'Sa": "Kaisa",
        "Kha'Zix": "Khazix",
        "Kog'Maw": "KogMaw",
        "LeBlanc": "Leblanc",
        "Rek'Sai": "RekSai",
        "Vel'Koz": "Velkoz",
        "Bel'Veth": "Belveth",
        "Renata Glasc": "Renata"
    }
    
    normalized = special_cases.get(champ_name, champ_name.replace(" ", "").replace("'", "").replace(".", ""))
    return f"https://ddragon.leagueoflegends.com/cdn/16.2.1/img/champion/{normalized}.png"


def normalize_patch(patch):
    """
    Normalizes patch format to handle variations like 26.2, 26.02, 16.2, 16.02
    Returns a comparable format: "26.2" (always without leading zero in minor version)
    
    Examples:
        "26.02" -> "26.2"
        "26.2" -> "26.2"
        "16.02" -> "16.2"
    """
    if pd.isna(patch) or patch == "":
        return ""
    
    patch_str = str(patch).strip()
    
    # Split by dot
    parts = patch_str.split('.')
    if len(parts) != 2:
        return patch_str  # Return as-is if format is unexpected
    
    major, minor = parts
    
    # Remove leading zeros from minor version
    minor_normalized = str(int(minor)) if minor.isdigit() else minor
    
    return f"{major}.{minor_normalized}"


def get_role_icon(role):
    """Returns URL for role icon"""
    if pd.isna(role) or role == "":
        return ""
    role_lower = role.lower()
    role_map = {
        'top': 'https://raw.communitydragon.org/latest/plugins/rcp-fe-lol-clash/global/default/assets/images/position-selector/positions/icon-position-top.png',
        'jungle': 'https://raw.communitydragon.org/latest/plugins/rcp-fe-lol-clash/global/default/assets/images/position-selector/positions/icon-position-jungle.png',
        'mid': 'https://raw.communitydragon.org/latest/plugins/rcp-fe-lol-clash/global/default/assets/images/position-selector/positions/icon-position-middle.png',
        'bot': 'https://raw.communitydragon.org/latest/plugins/rcp-fe-lol-clash/global/default/assets/images/position-selector/positions/icon-position-bottom.png',
        'support': 'https://raw.communitydragon.org/latest/plugins/rcp-fe-lol-clash/global/default/assets/images/position-selector/positions/icon-position-utility.png'
    }
    return role_map.get(role_lower, '')


def filter_dataframe(df, team_filter=None, patches=None, filter_champion=None, filter_champion_picks_only=False):
    """
    Filters DataFrame based on criteria
    
    Args:
        df: DataFrame to filter
        team_filter: Team name to filter by
        patches: List of patches to filter by
        filter_champion: Champion to filter by (only show drafts with this champion)
        filter_champion_picks_only: If True, only filter by picks (ignore bans)
        
    Returns:
        pandas.DataFrame: Filtered DataFrame
    """
    df_filtered = df.copy()
    
    # Filter by team
    if team_filter:
        df_filtered = df_filtered[
            (df_filtered['Team1'] == team_filter) | 
            (df_filtered['Team2'] == team_filter)
        ]
        print(f"📊 Filtré par équipe: {team_filter} ({len(df_filtered)} games)")
    
    # Filter by patches
    if patches:
        # Normalize both the filter patches and the dataframe patches
        normalized_filter_patches = [normalize_patch(p) for p in patches]
        df_filtered = df_filtered[df_filtered['Patch'].isin(normalized_filter_patches)]
        print(f"📊 Filtré par patches: {patches} -> normalisé: {normalized_filter_patches} ({len(df_filtered)} games)")
    
    # Filter by champion (picks or picks+bans)
    if filter_champion:
        def champion_in_draft(row):
            """Check if champion appears in picks (and optionally bans)"""
            champion_lower = filter_champion.lower()
            
            # Check all picks for both teams
            for i in range(1, 6):
                # Team1 picks
                if pd.notna(row.get(f'Team1Pick{i}', '')) and row.get(f'Team1Pick{i}', '').lower() == champion_lower:
                    return True
                # Team2 picks
                if pd.notna(row.get(f'Team2Pick{i}', '')) and row.get(f'Team2Pick{i}', '').lower() == champion_lower:
                    return True
            
            # If filter_champion_picks_only is False, also check bans
            if not filter_champion_picks_only:
                for i in range(1, 6):
                    # Team1 bans
                    if pd.notna(row.get(f'Team1Ban{i}', '')) and row.get(f'Team1Ban{i}', '').lower() == champion_lower:
                        return True
                    # Team2 bans
                    if pd.notna(row.get(f'Team2Ban{i}', '')) and row.get(f'Team2Ban{i}', '').lower() == champion_lower:
                        return True
            
            return False
        
        df_filtered = df_filtered[df_filtered.apply(champion_in_draft, axis=1)]
        if filter_champion_picks_only:
            print(f"📊 Filtré par champion (PICKS uniquement): {filter_champion} ({len(df_filtered)} games)")
        else:
            print(f"📊 Filtré par champion (picks + bans): {filter_champion} ({len(df_filtered)} games)")
    
    return df_filtered


# ============================================================================
# MAIN ANALYSIS FUNCTION 1: DRAFTS + PICK ORDER
# ============================================================================

def analyze_drafts_and_pickorder_OLD(
    site,
    tournaments,
    output_filename='drafts_analysis.html',
    team_filter=None,
    patches=None,
    filter_champion=None,
    filter_champion_picks_only=False,
    highlight_champion=None,
    limit=None
):
    """
    Analyzes drafts and pick order statistics
    
    Args:
        site: mwclient Site object
        tournaments: List of tournament names
        output_filename: Output HTML filename
        team_filter: Filter by specific team (optional)
        patches: Filter by specific patches (optional)
        filter_champion: Filter to show only drafts with this champion (optional)
        filter_champion_picks_only: If True, only filter by picks (ignore bans) (optional)
        highlight_champion: Highlight specific champion in yellow (optional)
        limit: Limit matches per tournament (optional)
        
    Returns:
        pandas.DataFrame: The analyzed data
    """
    # Scrape data
    df = scrape_draft_data(site, tournaments, limit=limit)
    
    if df is None or len(df) == 0:
        print("❌ Pas de données à analyser")
        return None
    
    # Apply filters
    df_filtered = filter_dataframe(
        df, 
        team_filter=team_filter, 
        patches=patches, 
        filter_champion=filter_champion,
        filter_champion_picks_only=filter_champion_picks_only
    )
    
    if len(df_filtered) == 0:
        print("❌ Aucune donnée après filtrage")
        return None
    
    # Generate HTML
    _create_drafts_and_pickorder_html(
        df_filtered,
        output_filename=output_filename,
        highlight_champion=highlight_champion,
        team_filter=team_filter
    )
    
    return df_filtered


def _create_drafts_and_pickorder_html(df, output_filename, highlight_champion=None, team_filter=None):
    """Internal function to create the HTML with drafts and pick order stats"""
    
    # Analyze pick order stats with winrates
    first_pick_stats, second_pick_stats = _analyze_pick_order_with_winrates(df, team_filter=team_filter)
    
    # Generate stats HTML
    stats_html = f"""
    <div class="stats-section">
        <h1>Draft Analysis{' - ' + team_filter if team_filter else ''} ({len(df)} Games)</h1>
        <div class="stats-container">
            <div class="stats-grid">
                <div>
                    {_generate_pickorder_table_html(first_pick_stats, 'First Pick (Team1)')}
                </div>
                <div>
                    {_generate_pickorder_table_html(second_pick_stats, 'Second Pick (Team2)')}
                </div>
            </div>
        </div>
    </div>
    """
    
    # Generate all draft cards
    all_drafts_html = ""
    for idx, row in df.iterrows():
        all_drafts_html += _generate_draft_card_html(row, highlight_champion)
    
    # Complete HTML
    full_html = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Draft Analysis - {len(df)} Games</title>
        {_get_css_styles()}
    </head>
    <body>
        {stats_html}
        
        <div class="drafts-section">
            <div class="draft-container">
                {all_drafts_html}
            </div>
        </div>
    </body>
    </html>
    """
    
    with open(output_filename, 'w', encoding='utf-8') as f:
        f.write(full_html)
    
    print(f"\n✅ Page web créée: {output_filename}")
    print(f"Total de drafts: {len(df)}")
    if highlight_champion:
        print(f"Champion surligné: {highlight_champion}")


def _analyze_pick_order_with_winrates(df, team_filter=None):
    """Analyzes pick order statistics with winrates"""
    
    first_pick_stats = {
        'Top': defaultdict(lambda: {'count': 0, 'wins': 0}),
        'Jungle': defaultdict(lambda: {'count': 0, 'wins': 0}),
        'Mid': defaultdict(lambda: {'count': 0, 'wins': 0}),
        'Adc': defaultdict(lambda: {'count': 0, 'wins': 0}),
        'Support': defaultdict(lambda: {'count': 0, 'wins': 0})
    }
    
    second_pick_stats = {
        'Top': defaultdict(lambda: {'count': 0, 'wins': 0}),
        'Jungle': defaultdict(lambda: {'count': 0, 'wins': 0}),
        'Mid': defaultdict(lambda: {'count': 0, 'wins': 0}),
        'Adc': defaultdict(lambda: {'count': 0, 'wins': 0}),
        'Support': defaultdict(lambda: {'count': 0, 'wins': 0})
    }
    
    role_mapping = {'Top': 'Top', 'Jungle': 'Jungle', 'Mid': 'Mid', 'Bot': 'Adc', 'Support': 'Support'}
    
    games_as_first = 0
    games_as_second = 0
    
    for _, row in df.iterrows():
        # If team_filter is specified, only count that team's stats
        if team_filter:
            is_team1 = (row.get('Team1') == team_filter)
            is_team2 = (row.get('Team2') == team_filter)
            
            if not (is_team1 or is_team2):
                continue
            
            if is_team1:
                # Team is Team1 (First Pick)
                games_as_first += 1
                team1_won = (str(row.get('Winner', '')) == '1')
                
                role1 = row.get('Team1Role1', '')
                if pd.notna(role1) and role1 != '':
                    mapped_role = role_mapping.get(role1, role1)
                    first_pick_stats[mapped_role]['P1']['count'] += 1
                    if team1_won:
                        first_pick_stats[mapped_role]['P1']['wins'] += 1
                
                for i in [2, 3]:
                    role = row.get(f'Team1Role{i}', '')
                    if pd.notna(role) and role != '':
                        mapped_role = role_mapping.get(role, role)
                        first_pick_stats[mapped_role]['P2/P3']['count'] += 1
                        if team1_won:
                            first_pick_stats[mapped_role]['P2/P3']['wins'] += 1
                
                for i in [4, 5]:
                    role = row.get(f'Team1Role{i}', '')
                    if pd.notna(role) and role != '':
                        mapped_role = role_mapping.get(role, role)
                        first_pick_stats[mapped_role]['P4/P5']['count'] += 1
                        if team1_won:
                            first_pick_stats[mapped_role]['P4/P5']['wins'] += 1
            
            else:  # is_team2
                # Team is Team2 (Second Pick)
                games_as_second += 1
                team2_won = (str(row.get('Winner', '')) == '2')
                
                for i in [1, 2]:
                    role = row.get(f'Team2Role{i}', '')
                    if pd.notna(role) and role != '':
                        mapped_role = role_mapping.get(role, role)
                        second_pick_stats[mapped_role]['P1/P2']['count'] += 1
                        if team2_won:
                            second_pick_stats[mapped_role]['P1/P2']['wins'] += 1
                
                role3 = row.get('Team2Role3', '')
                if pd.notna(role3) and role3 != '':
                    mapped_role = role_mapping.get(role3, role3)
                    second_pick_stats[mapped_role]['P3']['count'] += 1
                    if team2_won:
                        second_pick_stats[mapped_role]['P3']['wins'] += 1
                
                role4 = row.get('Team2Role4', '')
                if pd.notna(role4) and role4 != '':
                    mapped_role = role_mapping.get(role4, role4)
                    second_pick_stats[mapped_role]['P4']['count'] += 1
                    if team2_won:
                        second_pick_stats[mapped_role]['P4']['wins'] += 1
                
                role5 = row.get('Team2Role5', '')
                if pd.notna(role5) and role5 != '':
                    mapped_role = role_mapping.get(role5, role5)
                    second_pick_stats[mapped_role]['P5']['count'] += 1
                    if team2_won:
                        second_pick_stats[mapped_role]['P5']['wins'] += 1
        
        else:
            # No team filter: count all teams (original behavior)
            team1_won = (str(row.get('Winner', '')) == '1')
            team2_won = (str(row.get('Winner', '')) == '2')
            
            games_as_first += 1
            games_as_second += 1
            
            # Team1 (First Pick): P1, P2/P3, P4/P5
            role1 = row.get('Team1Role1', '')
            if pd.notna(role1) and role1 != '':
                mapped_role = role_mapping.get(role1, role1)
                first_pick_stats[mapped_role]['P1']['count'] += 1
                if team1_won:
                    first_pick_stats[mapped_role]['P1']['wins'] += 1
            
            for i in [2, 3]:
                role = row.get(f'Team1Role{i}', '')
                if pd.notna(role) and role != '':
                    mapped_role = role_mapping.get(role, role)
                    first_pick_stats[mapped_role]['P2/P3']['count'] += 1
                    if team1_won:
                        first_pick_stats[mapped_role]['P2/P3']['wins'] += 1
            
            for i in [4, 5]:
                role = row.get(f'Team1Role{i}', '')
                if pd.notna(role) and role != '':
                    mapped_role = role_mapping.get(role, role)
                    first_pick_stats[mapped_role]['P4/P5']['count'] += 1
                    if team1_won:
                        first_pick_stats[mapped_role]['P4/P5']['wins'] += 1
            
            # Team2 (Second Pick): P1/P2, P3, P4, P5
            for i in [1, 2]:
                role = row.get(f'Team2Role{i}', '')
                if pd.notna(role) and role != '':
                    mapped_role = role_mapping.get(role, role)
                    second_pick_stats[mapped_role]['P1/P2']['count'] += 1
                    if team2_won:
                        second_pick_stats[mapped_role]['P1/P2']['wins'] += 1
            
            role3 = row.get('Team2Role3', '')
            if pd.notna(role3) and role3 != '':
                mapped_role = role_mapping.get(role3, role3)
                second_pick_stats[mapped_role]['P3']['count'] += 1
                if team2_won:
                    second_pick_stats[mapped_role]['P3']['wins'] += 1
            
            role4 = row.get('Team2Role4', '')
            if pd.notna(role4) and role4 != '':
                mapped_role = role_mapping.get(role4, role4)
                second_pick_stats[mapped_role]['P4']['count'] += 1
                if team2_won:
                    second_pick_stats[mapped_role]['P4']['wins'] += 1
            
            role5 = row.get('Team2Role5', '')
            if pd.notna(role5) and role5 != '':
                mapped_role = role_mapping.get(role5, role5)
                second_pick_stats[mapped_role]['P5']['count'] += 1
                if team2_won:
                    second_pick_stats[mapped_role]['P5']['wins'] += 1
    
    # Determine total_games for percentage calculation
    total_games_first = games_as_first if team_filter else len(df)
    total_games_second = games_as_second if team_filter else len(df)
    
    # Create DataFrames
    first_pick_data = []
    for role in ['Top', 'Jungle', 'Mid', 'Adc', 'Support']:
        row_data = {'Role': role}
        for pick_pos in ['P1', 'P2/P3', 'P4/P5']:
            count = first_pick_stats[role][pick_pos]['count']
            wins = first_pick_stats[role][pick_pos]['wins']
            losses = count - wins
            percentage = (count / total_games_first) * 100 if total_games_first > 0 else 0
            winrate = (wins / count) * 100 if count > 0 else 0
            
            row_data[pick_pos] = {
                'percentage': percentage,
                'wins': wins,
                'losses': losses,
                'winrate': winrate,
                'count': count
            }
        first_pick_data.append(row_data)
    
    second_pick_data = []
    for role in ['Top', 'Jungle', 'Mid', 'Adc', 'Support']:
        row_data = {'Role': role}
        for pick_pos in ['P1/P2', 'P3', 'P4', 'P5']:
            count = second_pick_stats[role][pick_pos]['count']
            wins = second_pick_stats[role][pick_pos]['wins']
            losses = count - wins
            percentage = (count / total_games_second) * 100 if total_games_second > 0 else 0
            winrate = (wins / count) * 100 if count > 0 else 0
            
            row_data[pick_pos] = {
                'percentage': percentage,
                'wins': wins,
                'losses': losses,
                'winrate': winrate,
                'count': count
            }
        second_pick_data.append(row_data)
    
    return pd.DataFrame(first_pick_data), pd.DataFrame(second_pick_data)


def _generate_pickorder_table_html(stats_df, title):
    """Generates HTML for pick order table with winrates"""
    
    def get_winrate_color(winrate):
        if winrate >= 55:
            return 'rgba(76, 175, 80, 0.4)'
        elif winrate >= 50:
            return 'rgba(76, 175, 80, 0.25)'
        elif winrate >= 45:
            return 'rgba(76, 175, 80, 0.15)'
        else:
            return 'rgba(220, 38, 38, 0.2)'
    
    html = f'<h2>{title}</h2>\n<table class="stats-table">\n'
    
    # Header
    html += '<thead>\n<tr>\n<th>Role</th>\n'
    pick_columns = [col for col in stats_df.columns if col != 'Role']
    for col in pick_columns:
        html += f'<th>{col}</th>\n'
    html += '</tr>\n</thead>\n'
    
    # Body
    html += '<tbody>\n'
    for _, row in stats_df.iterrows():
        html += '<tr>\n'
        html += f'<td class="role-cell"><strong>{row["Role"]}</strong></td>\n'
        
        for col in pick_columns:
            data = row[col]
            percentage = data['percentage']
            wins = data['wins']
            losses = data['losses']
            winrate = data['winrate']
            count = data['count']
            
            bg_color = get_winrate_color(winrate) if count > 0 else 'rgba(20, 22, 28, 0.6)'
            
            html += f'<td class="pick-cell" style="background-color: {bg_color};">\n'
            html += f'<div class="pick-rate">{percentage:.2f}%</div>\n'
            if count > 0:
                html += f'<div class="win-loss">{wins}-{losses} ({winrate:.0f}%)</div>\n'
            else:
                html += f'<div class="win-loss">-</div>\n'
            html += '</td>\n'
        
        html += '</tr>\n'
    html += '</tbody>\n</table>\n'
    
    return html


def _generate_draft_card_html(row, highlight_champion=None):
    """Generates HTML for a single draft card"""
    
    def is_highlighted(champ_name):
        if not highlight_champion or pd.isna(champ_name) or champ_name == "":
            return False
        return champ_name.lower() == highlight_champion.lower()
    
    winner_value = int(row.get('Winner', 0)) if pd.notna(row.get('Winner')) else 0
    team1_won = (winner_value == 1)
    team2_won = (winner_value == 2)
    
    team1_class = 'winner' if team1_won else ''
    team2_class = 'winner' if team2_won else ''
    team1_score = 1 if team1_won else 0
    team2_score = 1 if team2_won else 0
    
    team1_bans_first = [row.get(f'Team1Ban{i}', '') for i in range(1, 4)]
    team2_bans_first = [row.get(f'Team2Ban{i}', '') for i in range(1, 4)]
    team1_bans_second = [row.get(f'Team1Ban{i}', '') for i in range(4, 6)]
    team2_bans_second = [row.get(f'Team2Ban{i}', '') for i in range(4, 6)]
    
    team1_picks_first = [(row.get(f'Team1Pick{i}', ''), row.get(f'Team1Role{i}', '')) for i in range(1, 4)]
    team2_picks_first = [(row.get(f'Team2Pick{i}', ''), row.get(f'Team2Role{i}', '')) for i in range(1, 4)]
    team1_picks_second = [(row.get(f'Team1Pick{i}', ''), row.get(f'Team1Role{i}', '')) for i in range(4, 6)]
    team2_picks_second = [(row.get(f'Team2Pick{i}', ''), row.get(f'Team2Role{i}', '')) for i in range(4, 6)]
    
    def generate_bans_html(bans):
        html = ""
        for ban in bans:
            if pd.notna(ban) and ban != "":
                highlight_class = ' highlighted' if is_highlighted(ban) else ''
                html += f"""
                <div class="draft-pick-row draft-ban-row{highlight_class}">
                    <img src="{normalize_champion(ban)}" alt="{ban}" class="draft-champ-icon-small" title="{ban}">
                    <span class="draft-champ-name">{ban}</span>
                </div>
                """
        return html
    
    def generate_picks_html(picks):
        html = ""
        for champ, role in picks:
            if pd.notna(champ) and champ != "":
                role_icon = get_role_icon(role)
                role_html = f'<img src="{role_icon}" alt="{role}" class="draft-role-icon" title="{role}">' if role_icon else ''
                highlight_class = ' highlighted' if is_highlighted(champ) else ''
                html += f"""
                <div class="draft-pick-row{highlight_class}">
                    {role_html}
                    <img src="{normalize_champion(champ)}" alt="{champ}" class="draft-champ-icon-small" title="{champ}">
                    <span class="draft-champ-name">{champ}</span>
                </div>
                """
        return html
    
    html_output = f"""
    <div class="draft-card">
        <div class="draft-header-main">
            <div class="draft-team-name-left {team1_class}">{row['Team1']}</div>
            <div class="draft-score-container">
                <span class="score {'winner-score' if team1_won else ''}">{team1_score}</span>
                <span class="score-separator">-</span>
                <span class="score {'winner-score' if team2_won else ''}">{team2_score}</span>
            </div>
            <div class="draft-team-name-right {team2_class}">{row['Team2']}</div>
        </div>
        
        <div class="draft-picks-section-new draft-bans-inline">
            <div class="draft-picks-team1-new">
                {generate_bans_html(team1_bans_first)}
            </div>
            <div class="draft-picks-team2-new">
                {generate_bans_html(team2_bans_first)}
            </div>
        </div>
        
        <div class="draft-picks-section-new">
            <div class="draft-picks-team1-new">
                {generate_picks_html(team1_picks_first)}
            </div>
            <div class="draft-picks-team2-new">
                {generate_picks_html(team2_picks_first)}
            </div>
        </div>
        
        <div class="draft-picks-section-new draft-bans-inline">
            <div class="draft-picks-team1-new">
                {generate_bans_html(team1_bans_second)}
            </div>
            <div class="draft-picks-team2-new">
                {generate_bans_html(team2_bans_second)}
            </div>
        </div>
        
        <div class="draft-picks-section-new">
            <div class="draft-picks-team1-new">
                {generate_picks_html(team1_picks_second)}
            </div>
            <div class="draft-picks-team2-new">
                {generate_picks_html(team2_picks_second)}
            </div>
        </div>
        
        <div class="draft-meta">
            {row.get('GameId', '')} - Patch {row.get('Patch', '')}
        </div>
    </div>
    """
    
    return html_output


# ============================================================================
# MAIN ANALYSIS FUNCTION 2: CHAMPIONS BY ROLE
# ============================================================================

def analyze_champions_by_role_OLD(
    site,
    tournaments,
    output_filename='champions_stats.html',
    title=None,
    team_filter=None,
    patches=None,
    limit=None
):
    """
    Analyzes champion statistics by role
    
    Args:
        site: mwclient Site object
        tournaments: List of tournament names
        output_filename: Output HTML filename
        title: Custom title (optional)
        team_filter: Filter by specific team (optional)
        patches: Filter by specific patches (optional)
        limit: Limit matches per tournament (optional)
        
    Returns:
        pandas.DataFrame: The analyzed data
    """
    # Scrape data
    df = scrape_draft_data(site, tournaments, limit=limit)
    
    if df is None or len(df) == 0:
        print("❌ Pas de données à analyser")
        return None
    
    # Apply filters
    df_filtered = filter_dataframe(df, team_filter=team_filter, patches=patches)
    
    if len(df_filtered) == 0:
        print("❌ Aucune donnée après filtrage")
        return None
    
    # Default title
    if title is None:
        title = f"Champions Stats by Role ({len(df_filtered)} Games)"
        if team_filter:
            title = f"Champions Stats - {team_filter} ({len(df_filtered)} Games)"
        if patches:
            patches_str = ", ".join(patches)
            title = f"Champions Stats - Patches {patches_str} ({len(df_filtered)} Games)"
    
    # Generate HTML
    _create_champions_by_role_html(df_filtered, output_filename, title, team_filter=team_filter)
    
    return df_filtered


def _create_champions_by_role_html(df, output_filename, title, team_filter=None):
    """Internal function to create the HTML with champion statistics"""
    
    # Prepare champion stats
    champions_stats = []

    for role in ['Top', 'Jungle', 'Mid', 'Bot', 'Support']:
        for idx, row in df.iterrows():
            # If team_filter is specified, only count that team's picks
            if team_filter:
                # Check if team is Team1 or Team2
                is_team1 = (row.get('Team1') == team_filter)
                is_team2 = (row.get('Team2') == team_filter)
                
                if is_team1:
                    # Only count Team1's picks
                    for i in range(1, 6):
                        if row.get(f'Team1Role{i}') == role:
                            champion = row.get(f'Team1Pick{i}')
                            if pd.notna(champion) and champion != '':
                                win = 1 if str(row.get('Winner', '')) == '1' else 0
                                champions_stats.append({
                                    'Champion': champion,
                                    'Role': role,
                                    'Win': win
                                })
                elif is_team2:
                    # Only count Team2's picks
                    for i in range(1, 6):
                        if row.get(f'Team2Role{i}') == role:
                            champion = row.get(f'Team2Pick{i}')
                            if pd.notna(champion) and champion != '':
                                win = 1 if str(row.get('Winner', '')) == '2' else 0
                                champions_stats.append({
                                    'Champion': champion,
                                    'Role': role,
                                    'Win': win
                                })
            else:
                # No team filter: count both teams (original behavior)
                # For Team1
                for i in range(1, 6):
                    if row.get(f'Team1Role{i}') == role:
                        champion = row.get(f'Team1Pick{i}')
                        if pd.notna(champion) and champion != '':
                            win = 1 if str(row.get('Winner', '')) == '1' else 0
                            champions_stats.append({
                                'Champion': champion,
                                'Role': role,
                                'Win': win
                            })
                
                # For Team2
                for i in range(1, 6):
                    if row.get(f'Team2Role{i}') == role:
                        champion = row.get(f'Team2Pick{i}')
                        if pd.notna(champion) and champion != '':
                            win = 1 if str(row.get('Winner', '')) == '2' else 0
                            champions_stats.append({
                                'Champion': champion,
                                'Role': role,
                                'Win': win
                            })

    df_stats = pd.DataFrame(champions_stats)

    def create_role_stats(role_name):
        role_data = df_stats[df_stats['Role'] == role_name].groupby('Champion').agg({
            'Win': ['sum', 'count', 'mean']
        }).reset_index()
        
        role_data.columns = ['Champion', 'Wins', 'Games', 'Winrate']
        role_data['Winrate'] = (role_data['Winrate'] * 100).round(1)
        role_data = role_data.sort_values('Games', ascending=False)
        
        return role_data[['Champion', 'Games', 'Wins', 'Winrate']].reset_index(drop=True)

    role_stats = {
        'Top': create_role_stats('Top'),
        'Jungle': create_role_stats('Jungle'),
        'Mid': create_role_stats('Mid'),
        'Adc': create_role_stats('Bot'),
        'Support': create_role_stats('Support')
    }
    
    def get_winrate_color(winrate):
        if winrate >= 60:
            return 'rgba(76, 175, 80, 0.4)'
        elif winrate >= 50:
            return 'rgba(76, 175, 80, 0.25)'
        elif winrate >= 40:
            return 'rgba(76, 175, 80, 0.15)'
        else:
            return 'rgba(220, 38, 38, 0.2)'
    
    def generate_role_table_html(role_name, role_df):
        role_icon = get_role_icon(role_name.lower() if role_name != 'Adc' else 'bot')
        
        html = f"""
        <div class="role-section">
            <div class="role-header">
                <img src="{role_icon}" alt="{role_name}" class="role-icon-large">
                <h2>{role_name}</h2>
            </div>
            <table class="champion-table">
                <thead>
                    <tr>
                        <th>Champion</th>
                        <th>Games</th>
                        <th>W-L</th>
                        <th>Winrate</th>
                    </tr>
                </thead>
                <tbody>
        """
        
        for _, row in role_df.iterrows():
            champion = row['Champion']
            games = int(row['Games'])
            wins = int(row['Wins'])
            losses = games - wins
            winrate = row['Winrate']
            winrate_color = get_winrate_color(winrate)
            
            html += f"""
                    <tr>
                        <td class="champion-cell">
                            <img src="{normalize_champion(champion)}" alt="{champion}" class="champion-icon">
                            <span class="champion-name">{champion}</span>
                        </td>
                        <td class="games-cell">{games}</td>
                        <td class="wl-cell">{wins}-{losses}</td>
                        <td class="winrate-cell" style="background-color: {winrate_color};">{winrate:.1f}%</td>
                    </tr>
            """
        
        html += """
                </tbody>
            </table>
        </div>
        """
        
        return html
    
    all_tables_html = ""
    for role_name, role_df in role_stats.items():
        all_tables_html += generate_role_table_html(role_name, role_df)
    
    full_html = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>{title}</title>
        {_get_champions_css_styles()}
    </head>
    <body>
        <div class="main-container">
            <h1>{title}</h1>
            <div class="roles-grid">
                {all_tables_html}
            </div>
        </div>
    </body>
    </html>
    """
    
    with open(output_filename, 'w', encoding='utf-8') as f:
        f.write(full_html)
    
    print(f"\n✅ Page web créée: {output_filename}")
    print(f"Titre: {title}")
    print(f"Total de games analysées: {len(df)}")


# ============================================================================
# CSS STYLES
# ============================================================================

def _get_css_styles():
    """Returns CSS styles for drafts and pick order page"""
    return """
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            background: #0a0a0a;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            padding: 20px;
        }
        
        /* ===== STYLES POUR LES STATS ===== */
        .stats-section {
            background: linear-gradient(180deg, #1a1a1a 0%, #0d0d0d 100%);
            border: 1px solid #2a2a2a;
            border-radius: 6px;
            padding: 30px 20px;
            margin-bottom: 40px;
            max-width: 1200px;
            margin-left: auto;
            margin-right: auto;
        }
        
        h1 {
            text-align: center;
            color: #fff;
            margin-bottom: 30px;
            font-size: 1.8rem;
            text-transform: uppercase;
            letter-spacing: 1px;
        }
        
        .stats-container {
            max-width: 100%;
            margin: 0 auto;
        }
        
        .stats-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 30px;
        }
        
        h2 {
            color: #e4e6eb;
            margin-bottom: 15px;
            font-size: 1rem;
            text-align: center;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        
        .stats-table {
            width: 100%;
            border-collapse: collapse;
            background: rgba(20, 22, 28, 0.8);
            border-radius: 6px;
            overflow: hidden;
            border: 1px solid #2a2a2a;
        }
        
        .stats-table th {
            background: rgba(255, 255, 255, 0.05);
            color: #fff;
            padding: 12px;
            text-align: center;
            font-weight: 600;
            border-bottom: 1px solid #2a2a2a;
            font-size: 0.85rem;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        
        .stats-table td {
            padding: 8px;
            text-align: center;
            border-bottom: 1px solid rgba(255, 255, 255, 0.05);
            color: #e4e6eb;
            font-size: 0.85rem;
            font-weight: 600;
        }
        
        .stats-table td.role-cell {
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        
        .stats-table td.pick-cell {
            padding: 6px;
        }
        
        .pick-rate {
            font-size: 0.9rem;
            font-weight: 700;
            margin-bottom: 2px;
        }
        
        .win-loss {
            font-size: 0.75rem;
            font-weight: 600;
            opacity: 0.9;
        }
        
        .stats-table tr:last-child td {
            border-bottom: none;
        }
        
        .stats-table tbody tr:hover {
            background: rgba(255, 255, 255, 0.02);
        }
        
        /* ===== STYLES POUR LES DRAFTS ===== */
        .drafts-section {
            margin-top: 20px;
        }
        
        .draft-container {
            display: flex;
            flex-wrap: wrap;
            gap: 20px;
            justify-content: center;
            max-width: 1400px;
            margin: 0 auto;
        }
        
        .draft-card {
            background: linear-gradient(180deg, #1a1a1a 0%, #0d0d0d 100%);
            border: 1px solid #2a2a2a;
            border-radius: 6px;
            padding: 0.5rem;
            width: 280px;
        }
        
        .draft-header-main {
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 0.5rem 0.3rem;
            margin-bottom: 0.5rem;
            border-bottom: 1px solid #2a2a2a;
        }
        
        .draft-team-name-left, .draft-team-name-right {
            font-weight: 700;
            font-size: 0.75rem;
            color: #fff;
            text-transform: uppercase;
            flex: 1;
        }
        
        .draft-team-name-left {
            text-align: left;
        }
        
        .draft-team-name-right {
            text-align: right;
        }
        
        .draft-team-name-left.winner, .draft-team-name-right.winner {
            color: #4CAF50;
        }
        
        .draft-score-container {
            display: flex;
            align-items: center;
            gap: 0.3rem;
            padding: 0 0.5rem;
        }
        
        .score {
            font-weight: 700;
            font-size: 1.2rem;
            color: #666;
        }
        
        .score.winner-score {
            color: #4CAF50;
        }
        
        .score-separator {
            font-weight: 400;
            font-size: 1rem;
            color: #444;
        }
        
        .draft-picks-section-new {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 0.5rem;
            margin-top: 0.3rem;
        }
        
        .draft-picks-team1-new, .draft-picks-team2-new {
            display: flex;
            flex-direction: column;
            gap: 0.25rem;
        }
        
        .draft-pick-row {
            display: flex;
            align-items: center;
            gap: 0.4rem;
            padding: 0.25rem 0.4rem;
            background: rgba(20, 22, 28, 0.6);
            border-radius: 4px;
            border: 1px solid rgba(255, 255, 255, 0.05);
        }
        
        .draft-ban-row {
            background: rgba(139, 0, 0, 0.15);
            border-left: 2px solid rgba(220, 38, 38, 0.4);
        }
        
        .draft-pick-row.highlighted {
            background: rgba(255, 215, 0, 0.3) !important;
            border: 2px solid #CDB700 !important;
            box-shadow: 0 0 10px rgba(255, 215, 0, 0.5);
        }
        
        .draft-pick-row.highlighted .draft-champ-icon-small {
            border: 2px solid #CDB700;
            box-shadow: 0 0 8px rgba(255, 215, 0, 0.8);
        }
        
        .draft-pick-row.highlighted .draft-champ-name {
            color: #CDB700;
            font-weight: 700;
        }
        
        .draft-role-icon {
            width: 20px;
            height: 20px;
            opacity: 0.85;
        }
        
        .draft-champ-icon-small {
            width: 28px;
            height: 28px;
            border-radius: 4px;
            border: 1px solid rgba(255, 255, 255, 0.15);
        }
        
        .draft-champ-name {
            font-size: 0.75rem;
            font-weight: 600;
            color: #e4e6eb;
            flex: 1;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
            max-width: 80px;
        }
        
        .draft-meta {
            display: flex;
            justify-content: center;
            padding-top: 0.3rem;
            margin-top: 0.3rem;
            border-top: 1px solid #2a2a2a;
            font-size: 0.7rem;
            color: #888;
        }
        
        @media (max-width: 1024px) {
            .stats-grid {
                grid-template-columns: 1fr;
                gap: 20px;
            }
        }
    </style>
    """


def _get_champions_css_styles():
    """Returns CSS styles for champions by role page"""
    return """
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            background: #0a0a0a;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            padding: 20px;
        }
        
        .main-container {
            max-width: 1800px;
            margin: 0 auto;
        }
        
        h1 {
            text-align: center;
            color: #fff;
            margin-bottom: 40px;
            font-size: 2rem;
            text-transform: uppercase;
            letter-spacing: 1px;
        }
        
        .roles-grid {
            display: grid;
            grid-template-columns: repeat(5, 1fr);
            gap: 20px;
        }
        
        .role-section {
            background: linear-gradient(180deg, #1a1a1a 0%, #0d0d0d 100%);
            border: 1px solid #2a2a2a;
            border-radius: 6px;
            padding: 20px;
        }
        
        .role-header {
            display: flex;
            align-items: center;
            gap: 15px;
            margin-bottom: 20px;
            padding-bottom: 15px;
            border-bottom: 1px solid #2a2a2a;
        }
        
        .role-icon-large {
            width: 40px;
            height: 40px;
            opacity: 0.9;
        }
        
        h2 {
            color: #e4e6eb;
            font-size: 1.3rem;
            text-transform: uppercase;
            letter-spacing: 1px;
        }
        
        .champion-table {
            width: 100%;
            border-collapse: collapse;
        }
        
        .champion-table thead {
            background: rgba(255, 255, 255, 0.05);
        }
        
        .champion-table th {
            color: #fff;
            padding: 10px 8px;
            text-align: left;
            font-weight: 600;
            font-size: 0.75rem;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            border-bottom: 1px solid #2a2a2a;
        }
        
        .champion-table th:nth-child(2),
        .champion-table th:nth-child(3),
        .champion-table th:nth-child(4) {
            text-align: center;
        }
        
        .champion-table td {
            padding: 8px;
            border-bottom: 1px solid rgba(255, 255, 255, 0.05);
            color: #e4e6eb;
            font-size: 0.8rem;
        }
        
        .champion-table tr:last-child td {
            border-bottom: none;
        }
        
        .champion-table tbody tr:hover {
            background: rgba(255, 255, 255, 0.02);
        }
        
        .champion-cell {
            display: flex;
            align-items: center;
            gap: 8px;
        }
        
        .champion-icon {
            width: 28px;
            height: 28px;
            border-radius: 4px;
            border: 1px solid rgba(255, 255, 255, 0.15);
        }
        
        .champion-name {
            font-weight: 600;
            color: #e4e6eb;
            font-size: 0.8rem;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }
        
        .games-cell,
        .wl-cell,
        .winrate-cell {
            text-align: center;
            font-weight: 600;
        }
        
        .winrate-cell {
            border-radius: 4px;
            font-weight: 700;
        }
        
        @media (max-width: 1600px) {
            .roles-grid {
                grid-template-columns: repeat(3, 1fr);
            }
        }
        
        @media (max-width: 1024px) {
            .roles-grid {
                grid-template-columns: repeat(2, 1fr);
            }
        }
        
        @media (max-width: 768px) {
            .roles-grid {
                grid-template-columns: 1fr;
            }
        }
    </style>
    """


# ============================================================================
# ANALYSIS FUNCTION: BANS BY PICK TIMING (FLEXIBLE VERSION)
# ============================================================================

def analyze_bans_OLD(
    site,
    tournaments,
    champion,
    pick_moments=None,
    champion_duo=None,
    team_filter=None,
    patches=None,
    output_filename=None,
    limit=None
):
    """
    Analyzes bans from both teams when a champion (or duo) is picked
    
    FLEXIBLE USAGE:
    - No pick_moments: Analyzes all games where champion is picked (any position)
    - Single pick_moment: "Team1Pick1" (specific position)
    - Multiple pick_moments: ["Team2Pick1", "Team2Pick2"] (any of these positions)
    - Champion duo: champion="Azir", champion_duo="Rumble" (both in same team)
    
    Args:
        site: mwclient Site object
        tournaments: List of tournament names
        champion: Champion to analyze (ex: "Azir")
        pick_moments: Pick moment(s) - string or list (optional)
                     Ex: "Team1Pick1" or ["Team2Pick1", "Team2Pick2"]
                     If None, analyzes all positions
        champion_duo: Second champion for duo analysis (optional)
                      Finds games where BOTH champions are in same team
        team_filter: Filter by specific team (optional)
        patches: Filter by specific patches (optional)
        output_filename: Output HTML filename (optional, if None only prints)
        limit: Limit matches per tournament (optional)
        
    Returns:
        tuple: (df_team1_bans, df_team2_bans, games_list) or None
        
    EXAMPLES:
    # All games where Corki is picked (any position)
    analyze_bans_by_pick_timing(site, ["LEC"], "Corki")
    
    # Corki in Team2Pick1 OR Team2Pick2
    analyze_bans_by_pick_timing(site, ["LEC"], "Corki", pick_moments=["Team2Pick1", "Team2Pick2"])
    
    # Azir + Rumble together in same team
    analyze_bans_by_pick_timing(site, ["LEC"], "Azir", champion_duo="Rumble")
    """
    from collections import Counter
    
    # Scrape data
    df = scrape_draft_data(site, tournaments, limit=limit)
    
    if df is None or len(df) == 0:
        print("❌ Pas de données à analyser")
        return None
    
    # Apply filters
    df_filtered = filter_dataframe(df, team_filter=team_filter, patches=patches)
    
    if len(df_filtered) == 0:
        print("❌ Aucune donnée après filtrage")
        return None
    
    # Normalize pick_moments to list
    if pick_moments is None:
        # All positions
        pick_moments_list = [f'Team{t}Pick{i}' for t in [1, 2] for i in range(1, 6)]
        pick_description = "ANY POSITION"
    elif isinstance(pick_moments, str):
        pick_moments_list = [pick_moments]
        pick_description = pick_moments
    elif isinstance(pick_moments, list):
        pick_moments_list = pick_moments
        pick_description = " OR ".join(pick_moments)
    else:
        print("❌ pick_moments doit être None, un string, ou une liste")
        return None
    
    team1_bans = []
    team2_bans = []
    games_found = []
    
    for _, row in df_filtered.iterrows():
        champion_found = False
        picking_team_side = None
        
        # DUO MODE: Check if both champions are in same team
        if champion_duo:
            # Check Team1
            team1_picks = [row.get(f'Team1Pick{i}', '') for i in range(1, 6)]
            team1_has_champ1 = any(pd.notna(p) and p.lower() == champion.lower() for p in team1_picks)
            team1_has_champ2 = any(pd.notna(p) and p.lower() == champion_duo.lower() for p in team1_picks)
            
            # Check Team2
            team2_picks = [row.get(f'Team2Pick{i}', '') for i in range(1, 6)]
            team2_has_champ1 = any(pd.notna(p) and p.lower() == champion.lower() for p in team2_picks)
            team2_has_champ2 = any(pd.notna(p) and p.lower() == champion_duo.lower() for p in team2_picks)
            
            if team1_has_champ1 and team1_has_champ2:
                champion_found = True
                picking_team_side = 'Team1'
            elif team2_has_champ1 and team2_has_champ2:
                champion_found = True
                picking_team_side = 'Team2'
        
        # SINGLE CHAMPION MODE: Check if champion is picked in specified positions
        else:
            for pick_moment in pick_moments_list:
                picked_champ = row.get(pick_moment, '')
                if pd.notna(picked_champ) and picked_champ.lower() == champion.lower():
                    champion_found = True
                    if pick_moment.startswith('Team1'):
                        picking_team_side = 'Team1'
                    else:
                        picking_team_side = 'Team2'
                    break
        
        # If champion(s) found, record the bans
        if champion_found:
            games_found.append({
                'GameId': row['GameId'],
                'Team1': row['Team1'],
                'Team2': row['Team2'],
                'PickingTeamSide': picking_team_side,
                'Winner': row.get('Winner', ''),
                'Patch': row.get('Patch', '')
            })
            
            # Get all Team1 bans
            for i in range(1, 6):
                ban = row.get(f'Team1Ban{i}', '')
                if pd.notna(ban) and ban != '':
                    team1_bans.append(ban)
            
            # Get all Team2 bans
            for i in range(1, 6):
                ban = row.get(f'Team2Ban{i}', '')
                if pd.notna(ban) and ban != '':
                    team2_bans.append(ban)
    
    if not games_found:
        if champion_duo:
            print(f"❌ Aucune game trouvée avec {champion} + {champion_duo} ensemble")
        else:
            print(f"❌ Aucune game trouvée avec {champion} pick")
        if team_filter:
            print(f"   (avec filtre d'équipe: {team_filter})")
        if patches:
            print(f"   (avec filtre de patches: {patches})")
        return None
    
    # Count bans
    team1_ban_counts = Counter(team1_bans)
    team2_ban_counts = Counter(team2_bans)
    
    total_games = len(games_found)
    
    # Create DataFrames
    df_team1_bans = pd.DataFrame([
        {
            'Champion': ban,
            'Count': count,
            'Frequency': f"{(count/total_games)*100:.1f}%",
            'PerGame': f"{count/total_games:.2f}"
        }
        for ban, count in team1_ban_counts.most_common()
    ])
    
    df_team2_bans = pd.DataFrame([
        {
            'Champion': ban,
            'Count': count,
            'Frequency': f"{(count/total_games)*100:.1f}%",
            'PerGame': f"{count/total_games:.2f}"
        }
        for ban, count in team2_ban_counts.most_common()
    ])
    
    # Display title
    if champion_duo:
        analysis_title = f"{champion.upper()} + {champion_duo.upper()} DUO"
    else:
        analysis_title = f"{champion.upper()} @ {pick_description}"
    
    # Display results (console)
    print(f"\n{'='*80}")
    print(f"📊 ANALYSE DES BANS: {analysis_title}")
    print(f"{'='*80}")
    print(f"Tournois: {', '.join(tournaments)}")
    if team_filter:
        print(f"Équipe filtrée: {team_filter}")
    if patches:
        print(f"Patches filtrés: {patches}")
    print(f"Games trouvées: {total_games}")
    
    # Generate HTML if requested
    if output_filename:
        _create_bans_analysis_html(
            champion=champion,
            champion_duo=champion_duo,
            pick_description=pick_description,
            tournaments=tournaments,
            team_filter=team_filter,
            patches=patches,
            total_games=total_games,
            df_team1_bans=df_team1_bans,
            df_team2_bans=df_team2_bans,
            games_found=games_found,
            output_filename=output_filename
        )
    else:
        # Console output
        print(f"\n{'='*80}")
        print(f"🔵 BANS DE TEAM1")
        print(f"{'='*80}")
        if len(df_team1_bans) > 0:
            print(df_team1_bans.to_string(index=False))
        else:
            print("Aucun ban")
        
        print(f"\n{'='*80}")
        print(f"🔴 BANS DE TEAM2")
        print(f"{'='*80}")
        if len(df_team2_bans) > 0:
            print(df_team2_bans.to_string(index=False))
        else:
            print("Aucun ban")
        
        print(f"\n{'='*80}")
        print(f"📋 GAMES CONCERNÉES")
        print(f"{'='*80}")
        for game in games_found[:5]:
            print(f"   {game['Team1']} vs {game['Team2']} - Patch {game['Patch']}")
        if len(games_found) > 5:
            print(f"   ... et {len(games_found) - 5} autres games")
        print(f"{'='*80}\n")
    
    return df_team1_bans, df_team2_bans, games_found


def _create_bans_analysis_html(champion, champion_duo, pick_description, tournaments, team_filter, patches, 
                                total_games, df_team1_bans, df_team2_bans, games_found, output_filename):
    """Internal function to create HTML for bans analysis"""
    
    def generate_bans_table_html(df_bans, team_name, color):
        """Generate HTML table for bans"""
        if len(df_bans) == 0:
            return f"<p style='text-align: center; color: #888;'>Aucun ban pour {team_name}</p>"
        
        html = f'<table class="bans-table">\n'
        html += '<thead>\n<tr>\n'
        html += '<th>Champion</th>\n'
        html += '<th>Count</th>\n'
        html += '<th>Frequency</th>\n'
        html += '<th>Per Game</th>\n'
        html += '</tr>\n</thead>\n<tbody>\n'
        
        for _, row in df_bans.iterrows():
            champ = row['Champion']
            count = row['Count']
            freq = row['Frequency']
            per_game = row['PerGame']
            
            # Color gradient based on frequency
            freq_val = float(freq.rstrip('%'))
            if freq_val >= 50:
                bg_color = 'rgba(220, 38, 38, 0.3)'
            elif freq_val >= 30:
                bg_color = 'rgba(220, 38, 38, 0.2)'
            elif freq_val >= 15:
                bg_color = 'rgba(220, 38, 38, 0.1)'
            else:
                bg_color = 'rgba(20, 22, 28, 0.6)'
            
            html += f'<tr style="background-color: {bg_color};">\n'
            html += f'<td class="champ-cell">'
            html += f'<img src="{normalize_champion(champ)}" class="champ-icon-small" alt="{champ}">'
            html += f'<span>{champ}</span></td>\n'
            html += f'<td class="center-cell">{count}</td>\n'
            html += f'<td class="center-cell"><strong>{freq}</strong></td>\n'
            html += f'<td class="center-cell">{per_game}</td>\n'
            html += '</tr>\n'
        
        html += '</tbody>\n</table>\n'
        return html
    
    # Generate games list HTML
    games_html = ""
    for game in games_found[:10]:
        winner_icon = "🏆" if game['Winner'] else ""
        games_html += f"""
        <div class="game-item">
            <span class="game-teams">{game['Team1']} vs {game['Team2']}</span>
            <span class="game-patch">Patch {game['Patch']}</span>
            <span class="game-winner">{winner_icon}</span>
        </div>
        """
    if len(games_found) > 10:
        games_html += f'<p style="text-align: center; color: #888; margin-top: 10px;">... et {len(games_found) - 10} autres games</p>'
    
    # Filters info
    filters_html = f"<p><strong>Tournois:</strong> {', '.join(tournaments)}</p>"
    if team_filter:
        filters_html += f"<p><strong>Équipe:</strong> {team_filter}</p>"
    if patches:
        filters_html += f"<p><strong>Patches:</strong> {', '.join(patches)}</p>"
    
    # Title
    if champion_duo:
        title = f"Bans Analysis: {champion} + {champion_duo} Duo"
    else:
        title = f"Bans Analysis: {champion} @ {pick_description}"
    
    # CSS
    css = """
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            background: #0a0a0a;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            padding: 20px;
            color: #e4e6eb;
        }
        
        .container {
            max-width: 1400px;
            margin: 0 auto;
        }
        
        .header {
            background: linear-gradient(180deg, #1a1a1a 0%, #0d0d0d 100%);
            border: 1px solid #2a2a2a;
            border-radius: 6px;
            padding: 30px;
            margin-bottom: 30px;
            text-align: center;
        }
        
        h1 {
            color: #fff;
            font-size: 2rem;
            text-transform: uppercase;
            letter-spacing: 1px;
            margin-bottom: 20px;
        }
        
        .info-section {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 20px;
            margin-top: 20px;
        }
        
        .info-box {
            background: rgba(255, 255, 255, 0.05);
            padding: 15px;
            border-radius: 4px;
        }
        
        .info-box p {
            margin: 5px 0;
            color: #b0b0b0;
        }
        
        .stats-highlight {
            color: #4CAF50;
            font-weight: 700;
            font-size: 1.2rem;
        }
        
        .tables-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 30px;
            margin-bottom: 30px;
        }
        
        .table-section {
            background: linear-gradient(180deg, #1a1a1a 0%, #0d0d0d 100%);
            border: 1px solid #2a2a2a;
            border-radius: 6px;
            padding: 20px;
        }
        
        h2 {
            color: #fff;
            font-size: 1.3rem;
            margin-bottom: 20px;
            text-transform: uppercase;
            letter-spacing: 1px;
            text-align: center;
            padding-bottom: 10px;
            border-bottom: 2px solid #2a2a2a;
        }
        
        .team1-header {
            border-bottom-color: #3B82F6;
        }
        
        .team2-header {
            border-bottom-color: #EF4444;
        }
        
        .bans-table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 15px;
        }
        
        .bans-table th {
            background: rgba(255, 255, 255, 0.05);
            color: #fff;
            padding: 12px;
            text-align: left;
            font-weight: 600;
            font-size: 0.85rem;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            border-bottom: 1px solid #2a2a2a;
        }
        
        .bans-table td {
            padding: 10px 12px;
            border-bottom: 1px solid rgba(255, 255, 255, 0.05);
            font-size: 0.9rem;
        }
        
        .bans-table tr:last-child td {
            border-bottom: none;
        }
        
        .bans-table tbody tr:hover {
            background: rgba(255, 255, 255, 0.03) !important;
        }
        
        .champ-cell {
            display: flex;
            align-items: center;
            gap: 10px;
        }
        
        .champ-icon-small {
            width: 32px;
            height: 32px;
            border-radius: 4px;
            border: 1px solid rgba(255, 255, 255, 0.2);
        }
        
        .center-cell {
            text-align: center;
        }
        
        .games-section {
            background: linear-gradient(180deg, #1a1a1a 0%, #0d0d0d 100%);
            border: 1px solid #2a2a2a;
            border-radius: 6px;
            padding: 20px;
        }
        
        .game-item {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 10px 15px;
            margin: 5px 0;
            background: rgba(20, 22, 28, 0.6);
            border-radius: 4px;
            border: 1px solid rgba(255, 255, 255, 0.05);
        }
        
        .game-teams {
            flex: 1;
            font-weight: 600;
        }
        
        .game-patch {
            color: #888;
            font-size: 0.85rem;
            margin: 0 15px;
        }
        
        @media (max-width: 1024px) {
            .tables-grid {
                grid-template-columns: 1fr;
            }
            
            .info-section {
                grid-template-columns: 1fr;
            }
        }
    </style>
    """
    
    # HTML
    full_html = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>{title}</title>
        {css}
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>📊 {title}</h1>
                <div class="info-section">
                    <div class="info-box">
                        {filters_html}
                    </div>
                    <div class="info-box">
                        <p><strong>Games found:</strong> <span class="stats-highlight">{total_games}</span></p>
                    </div>
                </div>
            </div>
            
            <div class="tables-grid">
                <div class="table-section">
                    <h2 class="team1-header">🔵 Team1 Bans</h2>
                    {generate_bans_table_html(df_team1_bans, "Team1", "#3B82F6")}
                </div>
                
                <div class="table-section">
                    <h2 class="team2-header">🔴 Team2 Bans</h2>
                    {generate_bans_table_html(df_team2_bans, "Team2", "#EF4444")}
                </div>
            </div>
            
            <div class="games-section">
                <h2>📋 Games Analyzed</h2>
                {games_html}
            </div>
        </div>
    </body>
    </html>
    """
    
    # Save file
    with open(output_filename, 'w', encoding='utf-8') as f:
        f.write(full_html)
    
    print(f"\n✅ Page HTML créée: {output_filename}")
    print(f"Total de games: {total_games}")
    print(f"Ouvre le fichier dans ton navigateur!")
    """Internal function to create HTML for bans analysis"""
    
    def generate_bans_table_html(df_bans, team_name, color):
        """Generate HTML table for bans"""
        if len(df_bans) == 0:
            return f"<p style='text-align: center; color: #888;'>Aucun ban pour {team_name}</p>"
        
        html = f'<table class="bans-table">\n'
        html += '<thead>\n<tr>\n'
        html += '<th>Champion</th>\n'
        html += '<th>Count</th>\n'
        html += '<th>Frequency</th>\n'
        html += '<th>Per Game</th>\n'
        html += '</tr>\n</thead>\n<tbody>\n'
        
        for _, row in df_bans.iterrows():
            champ = row['Champion']
            count = row['Count']
            freq = row['Frequency']
            per_game = row['PerGame']
            
            # Color gradient based on frequency
            freq_val = float(freq.rstrip('%'))
            if freq_val >= 50:
                bg_color = 'rgba(220, 38, 38, 0.3)'
            elif freq_val >= 30:
                bg_color = 'rgba(220, 38, 38, 0.2)'
            elif freq_val >= 15:
                bg_color = 'rgba(220, 38, 38, 0.1)'
            else:
                bg_color = 'rgba(20, 22, 28, 0.6)'
            
            html += f'<tr style="background-color: {bg_color};">\n'
            html += f'<td class="champ-cell">'
            html += f'<img src="{normalize_champion(champ)}" class="champ-icon-small" alt="{champ}">'
            html += f'<span>{champ}</span></td>\n'
            html += f'<td class="center-cell">{count}</td>\n'
            html += f'<td class="center-cell"><strong>{freq}</strong></td>\n'
            html += f'<td class="center-cell">{per_game}</td>\n'
            html += '</tr>\n'
        
        html += '</tbody>\n</table>\n'
        return html
    
    # Generate games list HTML
    games_html = ""
    for game in games_found[:10]:
        winner_icon = "🏆" if game['Winner'] else ""
        games_html += f"""
        <div class="game-item">
            <span class="game-teams">{game['Team1']} vs {game['Team2']}</span>
            <span class="game-patch">Patch {game['Patch']}</span>
            <span class="game-winner">{winner_icon}</span>
        </div>
        """
    if len(games_found) > 10:
        games_html += f'<p style="text-align: center; color: #888; margin-top: 10px;">... et {len(games_found) - 10} autres games</p>'
    
    # Filters info
    filters_html = f"<p><strong>Tournois:</strong> {', '.join(tournaments)}</p>"
    if team_filter:
        filters_html += f"<p><strong>Équipe:</strong> {team_filter}</p>"
    if patches:
        filters_html += f"<p><strong>Patches:</strong> {', '.join(patches)}</p>"
    
    # CSS
    css = """
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            background: #0a0a0a;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            padding: 20px;
            color: #e4e6eb;
        }
        
        .container {
            max-width: 1400px;
            margin: 0 auto;
        }
        
        .header {
            background: linear-gradient(180deg, #1a1a1a 0%, #0d0d0d 100%);
            border: 1px solid #2a2a2a;
            border-radius: 6px;
            padding: 30px;
            margin-bottom: 30px;
            text-align: center;
        }
        
        h1 {
            color: #fff;
            font-size: 2rem;
            text-transform: uppercase;
            letter-spacing: 1px;
            margin-bottom: 20px;
        }
        
        .info-section {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 20px;
            margin-top: 20px;
        }
        
        .info-box {
            background: rgba(255, 255, 255, 0.05);
            padding: 15px;
            border-radius: 4px;
        }
        
        .info-box p {
            margin: 5px 0;
            color: #b0b0b0;
        }
        
        .stats-highlight {
            color: #4CAF50;
            font-weight: 700;
            font-size: 1.2rem;
        }
        
        .tables-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 30px;
            margin-bottom: 30px;
        }
        
        .table-section {
            background: linear-gradient(180deg, #1a1a1a 0%, #0d0d0d 100%);
            border: 1px solid #2a2a2a;
            border-radius: 6px;
            padding: 20px;
        }
        
        h2 {
            color: #fff;
            font-size: 1.3rem;
            margin-bottom: 20px;
            text-transform: uppercase;
            letter-spacing: 1px;
            text-align: center;
            padding-bottom: 10px;
            border-bottom: 2px solid #2a2a2a;
        }
        
        .team1-header {
            border-bottom-color: #3B82F6;
        }
        
        .team2-header {
            border-bottom-color: #EF4444;
        }
        
        .bans-table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 15px;
        }
        
        .bans-table th {
            background: rgba(255, 255, 255, 0.05);
            color: #fff;
            padding: 12px;
            text-align: left;
            font-weight: 600;
            font-size: 0.85rem;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            border-bottom: 1px solid #2a2a2a;
        }
        
        .bans-table td {
            padding: 10px 12px;
            border-bottom: 1px solid rgba(255, 255, 255, 0.05);
            font-size: 0.9rem;
        }
        
        .bans-table tr:last-child td {
            border-bottom: none;
        }
        
        .bans-table tbody tr:hover {
            background: rgba(255, 255, 255, 0.03) !important;
        }
        
        .champ-cell {
            display: flex;
            align-items: center;
            gap: 10px;
        }
        
        .champ-icon-small {
            width: 32px;
            height: 32px;
            border-radius: 4px;
            border: 1px solid rgba(255, 255, 255, 0.2);
        }
        
        .center-cell {
            text-align: center;
        }
        
        .games-section {
            background: linear-gradient(180deg, #1a1a1a 0%, #0d0d0d 100%);
            border: 1px solid #2a2a2a;
            border-radius: 6px;
            padding: 20px;
        }
        
        .game-item {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 10px 15px;
            margin: 5px 0;
            background: rgba(20, 22, 28, 0.6);
            border-radius: 4px;
            border: 1px solid rgba(255, 255, 255, 0.05);
        }
        
        .game-teams {
            flex: 1;
            font-weight: 600;
        }
        
        .game-patch {
            color: #888;
            font-size: 0.85rem;
            margin: 0 15px;
        }
        
        @media (max-width: 1024px) {
            .tables-grid {
                grid-template-columns: 1fr;
            }
            
            .info-section {
                grid-template-columns: 1fr;
            }
        }
    </style>
    """
    
    # HTML
    full_html = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>{title}</title>
        {css}
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>📊 {title}</h1>
                <div class="info-section">
                    <div class="info-box">
                        {filters_html}
                    </div>
                    <div class="info-box">
                        <p><strong>Games found:</strong> <span class="stats-highlight">{total_games}</span></p>
                    </div>
                </div>
            </div>
            
            <div class="tables-grid">
                <div class="table-section">
                    <h2 class="team1-header">🔵 Team1 Bans</h2>
                    {generate_bans_table_html(df_team1_bans, "Team1", "#3B82F6")}
                </div>
                
                <div class="table-section">
                    <h2 class="team2-header">🔴 Team2 Bans</h2>
                    {generate_bans_table_html(df_team2_bans, "Team2", "#EF4444")}
                </div>
            </div>
            
            <div class="games-section">
                <h2>📋 Games Analyzed</h2>
                {games_html}
            </div>
        </div>
    </body>
    </html>
    """
    
    # Save file
    with open(output_filename, 'w', encoding='utf-8') as f:
        f.write(full_html)
    
    print(f"\n✅ Page HTML créée: {output_filename}")
    print(f"Total de games: {total_games}")
    print(f"Ouvre le fichier dans ton navigateur!")


# ============================================================================
# NEW SIMPLIFIED API - 4 MAIN FUNCTIONS
# ============================================================================

def analyze_drafts(site, tournaments, output_filename='drafts.html', title=None, team_filter=None, 
                   patches=None, filter_champion=None, filter_champion_picks_only=False, 
                   highlight_champion=None, limit=None):
    """
    Visualizes draft cards (SIMPLIFIED API)
    
    Same as old analyze_drafts_and_pickorder but without pick order stats.
    For pick order stats, use analyze_pick_order() separately.
    """
    # Just generate drafts HTML without pick order stats
    df = scrape_draft_data(site, tournaments, limit=limit)
    if df is None or len(df) == 0:
        print("❌ Pas de données à analyser")
        return None
    
    df_filtered = filter_dataframe(df, team_filter=team_filter, patches=patches, 
                                   filter_champion=filter_champion, 
                                   filter_champion_picks_only=filter_champion_picks_only)
    
    if len(df_filtered) == 0:
        print("❌ Aucune donnée après filtrage")
        return None
    
    if title is None:
        title = f"Draft Cards ({len(df_filtered)} Games)"
        if team_filter:
            title = f"Draft Cards - {team_filter} ({len(df_filtered)} Games)"
    
    # Generate only draft cards HTML
    all_drafts_html = ""
    for idx, row in df_filtered.iterrows():
        all_drafts_html += _generate_draft_card_html(row, highlight_champion)
    
    full_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    {_get_css_styles()}
</head>
<body>
    <div class="main-container">
        <h1>{title}</h1>
        <div class="draft-container">
            {all_drafts_html}
        </div>
    </div>
</body>
</html>"""
    
    with open(output_filename, 'w', encoding='utf-8') as f:
        f.write(full_html)
    
    print(f"\n✅ Page HTML créée: {output_filename}")
    print(f"Total de drafts: {len(df_filtered)}")
    return df_filtered


def analyze_pick_order(site, tournaments, output_filename='pick_order.html', title=None, 
                      team_filter=None, patches=None, filter_champion=None, 
                      filter_champion_picks_only=False, limit=None):
    """
    Analyzes pick order statistics with winrates (SIMPLIFIED API)
    
    Same as the pick order part of old analyze_drafts_and_pickorder.
    """
    df = scrape_draft_data(site, tournaments, limit=limit)
    if df is None or len(df) == 0:
        print("❌ Pas de données à analyser")
        return None
    
    df_filtered = filter_dataframe(df, team_filter=team_filter, patches=patches, 
                                   filter_champion=filter_champion,
                                   filter_champion_picks_only=filter_champion_picks_only)
    
    if len(df_filtered) == 0:
        print("❌ Aucune donnée après filtrage")
        return None
    
    if title is None:
        title = f"Pick Order Stats ({len(df_filtered)} Games)"
        if team_filter:
            title = f"Pick Order - {team_filter} ({len(df_filtered)} Games)"
    
    # Analyze pick order
    first_pick_stats, second_pick_stats = _analyze_pick_order_with_winrates(df_filtered, team_filter=team_filter)
    
    stats_html = f"""
    <div class="stats-section">
        <h1>{title}</h1>
        <div class="stats-container">
            <div class="stats-grid">
                <div>
                    {_generate_pickorder_table_html(first_pick_stats, 'First Pick (Team1)')}
                </div>
                <div>
                    {_generate_pickorder_table_html(second_pick_stats, 'Second Pick (Team2)')}
                </div>
            </div>
        </div>
    </div>
    """
    
    full_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    {_get_css_styles()}
</head>
<body>
    {stats_html}
</body>
</html>"""
    
    with open(output_filename, 'w', encoding='utf-8') as f:
        f.write(full_html)
    
    print(f"\n✅ Page HTML créée: {output_filename}")
    print(f"Total de games: {len(df_filtered)}")
    return df_filtered


def analyze_champions(site, tournaments, output_filename='champions.html', title=None, 
                     team_filter=None, patches=None, filter_champion=None, 
                     filter_champion_picks_only=False, limit=None):
    """
    Analyzes champion statistics by role (SIMPLIFIED API)
    
    Same as old analyze_champions_by_role with cleaner name.
    """
    return analyze_champions_by_role_OLD(site, tournaments, output_filename, title, 
                                        team_filter, patches, limit)


def analyze_bans(site, tournaments, champion, pick_moments=None, champion_duo=None, 
                team_filter=None, patches=None, output_filename=None, limit=None):
    """
    Analyzes bans when champion(s) are picked (SIMPLIFIED API)
    
    Same as old analyze_bans_by_pick_timing with cleaner name.
    Uses new parameter name 'pick_moments' (was 'pick_moment' before).
    """
    return analyze_bans_OLD(site, tournaments, champion, pick_moments=pick_moments, 
                          champion_duo=champion_duo, team_filter=team_filter, 
                          patches=patches, output_filename=output_filename, limit=limit)


def get_team_players(site, team, year=None, tournaments=None):
    """
    Retrieves all players from a team for a given year or tournaments
    
    Args:
        site: mwclient Site object
        team: Team name (e.g., "SK Gaming", "HRTS RED")
        year: Year to filter (e.g., "2025") - optional if tournaments provided
        tournaments: List of tournament names - optional if year provided
        
    Returns:
        list: List of unique player names
    
    Example:
        players = get_team_players(site, "SK Gaming", year="2026")
        players = get_team_players(site, "HRTS RED", tournaments=["EM 2025 Spring"])
    """
    print(f"🔍 Recherche des joueurs de {team}...")
    
    # Build WHERE clause
    where_parts = [f'SP.Team="{team}"']
    
    if tournaments:
        tournament_conditions = " OR ".join([f'SG.Tournament="{t}"' for t in tournaments])
        where_parts.append(f"({tournament_conditions})")
    elif year:
        where_parts.append(f'To.Year="{year}"')
    else:
        raise ValueError("Either 'year' or 'tournaments' must be provided")
    
    where_clause = " AND ".join(where_parts)
    
    response = cargo_query(
        site,
        tables='ScoreboardPlayers=SP, ScoreboardGames=SG, Tournaments=To',
        fields='SP.Link',
        where=where_clause,
        join_on='SP.GameId=SG.GameId, SG.OverviewPage=To.OverviewPage',
        group_by='SP.Link',
        limit=500
    )
    
    if not response:
        print(f"❌ Aucun joueur trouvé pour {team}")
        return []
    
    players = [r.get('Link', r.get('SP.Link', '')) for r in response if r.get('Link') or r.get('SP.Link')]
    players = list(set(players))  # Remove duplicates
    players.sort()
    
    print(f"✅ {len(players)} joueurs trouvés: {', '.join(players)}")
    return players


def analyze_player_champions(site, player, year=None, tournaments=None, output_filename=None, title=None):
    """
    Analyzes a player's champion statistics (games, W-L, winrate) with HTML output
    
    Args:
        site: mwclient Site object
        player: Player name (e.g., "Tracyn", "Caps")
        year: Year to filter (e.g., "2025") - optional if tournaments provided
        tournaments: List of tournament names - optional if year provided
        output_filename: Output HTML filename (auto-generated if not provided)
        title: Custom title (optional)
        
    Returns:
        pandas.DataFrame: Champion statistics
    
    Example:
        analyze_player_champions(site, "Tracyn", year="2025")
        analyze_player_champions(site, "Caps", tournaments=["LEC 2026 Versus"])
    """
    print(f"\n{'='*60}")
    print(f"🔍 Récupération des stats de {player}...")
    print(f"{'='*60}")
    
    # Build WHERE clause
    where_parts = [f'PR._pageName="{player}"']
    
    if tournaments:
        tournament_conditions = " OR ".join([f'SG.Tournament="{t}"' for t in tournaments])
        where_parts.append(f"({tournament_conditions})")
    elif year:
        where_parts.append(f'To.Year="{year}"')
    else:
        raise ValueError("Either 'year' or 'tournaments' must be provided")
    
    where_clause = " AND ".join(where_parts)
    
    # Query ScoreboardPlayers for player stats
    response = cargo_query(
        site,
        tables='ScoreboardPlayers=SP, ScoreboardGames=SG, Tournaments=To, PlayerRedirects=PR',
        fields='SP.Champion, SP.Kills, SP.Deaths, SP.Assists, SG.Winner, SP.Side, SG.Tournament',
        where=where_clause,
        join_on='SP.GameId=SG.GameId, SG.OverviewPage=To.OverviewPage, SP.Link=PR.AllName',
        order_by='SP.Champion',
        limit=5000
    )
    
    if not response:
        print(f"❌ Aucune donnée trouvée pour {player}")
        return None
    
    print(f"✅ {len(response)} games trouvées")
    
    # Process data
    df = pd.DataFrame(response)
    
    # Calculate win for each game
    # Side is 1 (Blue) or 2 (Red), Winner is 1 or 2
    df['Win'] = df.apply(lambda row: 1 if str(row.get('Side', '')) == str(row.get('Winner', '')) else 0, axis=1)
    
    # Aggregate by champion
    champion_stats = df.groupby('Champion').agg({
        'Win': ['sum', 'count']
    }).reset_index()
    
    champion_stats.columns = ['Champion', 'Wins', 'Games']
    champion_stats['Losses'] = champion_stats['Games'] - champion_stats['Wins']
    champion_stats['Winrate'] = (champion_stats['Wins'] / champion_stats['Games'] * 100).round(1)
    champion_stats = champion_stats.sort_values('Games', ascending=False).reset_index(drop=True)
    
    # Get tournaments list for display
    tournaments_played = df['Tournament'].unique().tolist()
    total_games = len(df)
    total_champions = len(champion_stats)
    
    print(f"📊 {total_games} games sur {total_champions} champions")
    
    # Generate HTML
    if output_filename is None:
        suffix = year if year else "_".join([t.replace(" ", "") for t in tournaments[:2]])
        output_filename = f"player_{player.replace(' ', '')}_{suffix}.html"
    
    if title is None:
        title = f"{player} - Champion Stats ({total_games} Games)"
    
    _create_player_champions_html(champion_stats, output_filename, title, player, tournaments_played, total_games)
    
    return champion_stats


def analyze_player_career(site, player, output_filename=None, title=None):
    """
    Analyzes a player's FULL CAREER champion statistics (all games ever played)
    
    Args:
        site: mwclient Site object
        player: Player name (e.g., "Tracyn", "Caps", "Faker")
        output_filename: Output HTML filename (auto-generated if not provided)
        title: Custom title (optional)
        
    Returns:
        pandas.DataFrame: Champion statistics across entire career
    
    Example:
        analyze_player_career(site, "Caps")
        analyze_player_career(site, "Faker")
        analyze_player_career(site, "Tracyn")
    """
    print(f"\n{'='*60}")
    print(f"🔍 Récupération de la carrière complète de {player}...")
    print(f"{'='*60}")
    
    # Query ALL games for this player (no year/tournament filter)
    where_clause = f'PR._pageName="{player}"'
    
    response = cargo_query(
        site,
        tables='ScoreboardPlayers=SP, ScoreboardGames=SG, Tournaments=To, PlayerRedirects=PR',
        fields='SP.Champion, SG.Winner, SP.Side, SG.Tournament, To.Year',
        where=where_clause,
        join_on='SP.GameId=SG.GameId, SG.OverviewPage=To.OverviewPage, SP.Link=PR.AllName',
        order_by='To.Year DESC, SP.Champion',
        limit=10000  # Higher limit for full career
    )
    
    if not response:
        print(f"❌ Aucune donnée trouvée pour {player}")
        return None
    
    print(f"✅ {len(response)} games trouvées")
    
    # Process data
    df = pd.DataFrame(response)
    
    # Calculate win for each game
    df['Win'] = df.apply(lambda row: 1 if str(row.get('Side', '')) == str(row.get('Winner', '')) else 0, axis=1)
    
    # Get career span
    years = sorted(df['Year'].dropna().unique().tolist())
    if years:
        career_span = f"{years[0]} - {years[-1]}" if len(years) > 1 else years[0]
    else:
        career_span = "Unknown"
    
    # Aggregate by champion
    champion_stats = df.groupby('Champion').agg({
        'Win': ['sum', 'count']
    }).reset_index()
    
    champion_stats.columns = ['Champion', 'Wins', 'Games']
    champion_stats['Losses'] = champion_stats['Games'] - champion_stats['Wins']
    champion_stats['Winrate'] = (champion_stats['Wins'] / champion_stats['Games'] * 100).round(1)
    champion_stats = champion_stats.sort_values('Games', ascending=False).reset_index(drop=True)
    
    # Get tournaments list for display
    tournaments_played = df['Tournament'].unique().tolist()
    total_games = len(df)
    total_champions = len(champion_stats)
    
    print(f"📊 {total_games} games sur {total_champions} champions")
    print(f"📅 Carrière: {career_span}")
    
    # Generate HTML
    if output_filename is None:
        output_filename = f"player_{player.replace(' ', '').replace('(', '').replace(')', '')}_career.html"
    
    if title is None:
        title = f"{player} - Full Career ({total_games} Games)"
    
    _create_player_career_html(champion_stats, output_filename, title, player, 
                                tournaments_played, total_games, career_span, years)
    
    return champion_stats


def _create_player_career_html(df_stats, output_filename, title, player, tournaments, total_games, career_span, years):
    """Internal function to create the HTML with player career statistics"""
    
    def get_winrate_color(winrate):
        if winrate >= 60:
            return 'rgba(76, 175, 80, 0.4)'
        elif winrate >= 50:
            return 'rgba(76, 175, 80, 0.25)'
        elif winrate >= 40:
            return 'rgba(76, 175, 80, 0.15)'
        else:
            return 'rgba(220, 38, 38, 0.2)'
    
    # Generate table rows
    rows_html = ""
    for _, row in df_stats.iterrows():
        champion = row['Champion']
        games = int(row['Games'])
        wins = int(row['Wins'])
        losses = int(row['Losses'])
        winrate = row['Winrate']
        winrate_color = get_winrate_color(winrate)
        
        rows_html += f"""
                <tr>
                    <td class="champion-cell">
                        <img src="{normalize_champion(champion)}" alt="{champion}" class="champion-icon">
                        <span class="champion-name">{champion}</span>
                    </td>
                    <td class="games-cell">{games}</td>
                    <td class="wl-cell">{wins}-{losses}</td>
                    <td class="winrate-cell" style="background-color: {winrate_color};">{winrate:.1f}%</td>
                </tr>
        """
    
    # Generate tournaments list (grouped by year if possible)
    tournaments_html = "<br>".join([f"• {t}" for t in tournaments[:30]])  # Limit to 30
    if len(tournaments) > 30:
        tournaments_html += f"<br>... and {len(tournaments) - 30} more tournaments"
    
    # Years badges
    years_html = " ".join([f'<span class="year-badge">{y}</span>' for y in years]) if years else ""
    
    css = """
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            background: #0a0a0a;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            padding: 20px;
        }
        
        .main-container {
            max-width: 800px;
            margin: 0 auto;
        }
        
        h1 {
            text-align: center;
            color: #fff;
            margin-bottom: 10px;
            font-size: 2rem;
            text-transform: uppercase;
            letter-spacing: 1px;
        }
        
        .career-span {
            text-align: center;
            color: #4CAF50;
            font-size: 1.1rem;
            margin-bottom: 5px;
            font-weight: 600;
        }
        
        .years-container {
            text-align: center;
            margin-bottom: 20px;
        }
        
        .year-badge {
            display: inline-block;
            background: rgba(76, 175, 80, 0.2);
            color: #4CAF50;
            padding: 4px 10px;
            border-radius: 12px;
            font-size: 0.75rem;
            font-weight: 600;
            margin: 2px;
            border: 1px solid rgba(76, 175, 80, 0.3);
        }
        
        .stats-summary {
            text-align: center;
            color: #888;
            margin-bottom: 30px;
            font-size: 0.9rem;
        }
        
        .stats-summary strong {
            color: #4CAF50;
        }
        
        .player-section {
            background: linear-gradient(180deg, #1a1a1a 0%, #0d0d0d 100%);
            border: 1px solid #2a2a2a;
            border-radius: 6px;
            padding: 20px;
            margin-bottom: 20px;
        }
        
        .champion-table {
            width: 100%;
            border-collapse: collapse;
        }
        
        .champion-table thead {
            background: rgba(255, 255, 255, 0.05);
        }
        
        .champion-table th {
            color: #fff;
            padding: 12px 10px;
            text-align: left;
            font-weight: 600;
            font-size: 0.8rem;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            border-bottom: 1px solid #2a2a2a;
        }
        
        .champion-table th:nth-child(2),
        .champion-table th:nth-child(3),
        .champion-table th:nth-child(4) {
            text-align: center;
        }
        
        .champion-table td {
            padding: 10px;
            border-bottom: 1px solid rgba(255, 255, 255, 0.05);
            color: #e4e6eb;
            font-size: 0.85rem;
        }
        
        .champion-table tr:last-child td {
            border-bottom: none;
        }
        
        .champion-table tbody tr:hover {
            background: rgba(255, 255, 255, 0.02);
        }
        
        .champion-cell {
            display: flex;
            align-items: center;
            gap: 10px;
        }
        
        .champion-icon {
            width: 32px;
            height: 32px;
            border-radius: 4px;
            border: 1px solid rgba(255, 255, 255, 0.15);
        }
        
        .champion-name {
            font-weight: 600;
            color: #e4e6eb;
            font-size: 0.9rem;
        }
        
        .games-cell,
        .wl-cell,
        .winrate-cell {
            text-align: center;
            font-weight: 600;
        }
        
        .winrate-cell {
            border-radius: 4px;
            font-weight: 700;
        }
        
        .tournaments-section {
            margin-top: 20px;
            padding: 15px;
            background: rgba(255, 255, 255, 0.02);
            border-radius: 6px;
            border: 1px solid rgba(255, 255, 255, 0.05);
        }
        
        .tournaments-section h3 {
            color: #888;
            font-size: 0.8rem;
            text-transform: uppercase;
            margin-bottom: 10px;
        }
        
        .tournaments-section p {
            color: #666;
            font-size: 0.75rem;
            line-height: 1.6;
        }
    </style>
    """
    
    full_html = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>{title}</title>
        {css}
    </head>
    <body>
        <div class="main-container">
            <h1>🎮 {player}</h1>
            <p class="career-span">📅 {career_span}</p>
            <div class="years-container">
                {years_html}
            </div>
            <p class="stats-summary">
                <strong>{total_games}</strong> games played on <strong>{len(df_stats)}</strong> champions
            </p>
            
            <div class="player-section">
                <table class="champion-table">
                    <thead>
                        <tr>
                            <th>Champion</th>
                            <th>Games</th>
                            <th>W-L</th>
                            <th>Winrate</th>
                        </tr>
                    </thead>
                    <tbody>
                        {rows_html}
                    </tbody>
                </table>
            </div>
            
            <div class="tournaments-section">
                <h3>📋 Tournaments Included ({len(tournaments)})</h3>
                <p>{tournaments_html}</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    with open(output_filename, 'w', encoding='utf-8') as f:
        f.write(full_html)
    
    print(f"\n✅ Page HTML créée: {output_filename}")


def _create_player_champions_html(df_stats, output_filename, title, player, tournaments, total_games):
    """Internal function to create the HTML with player champion statistics"""
    
    def get_winrate_color(winrate):
        if winrate >= 60:
            return 'rgba(76, 175, 80, 0.4)'
        elif winrate >= 50:
            return 'rgba(76, 175, 80, 0.25)'
        elif winrate >= 40:
            return 'rgba(76, 175, 80, 0.15)'
        else:
            return 'rgba(220, 38, 38, 0.2)'
    
    # Generate table rows
    rows_html = ""
    for _, row in df_stats.iterrows():
        champion = row['Champion']
        games = int(row['Games'])
        wins = int(row['Wins'])
        losses = int(row['Losses'])
        winrate = row['Winrate']
        winrate_color = get_winrate_color(winrate)
        
        rows_html += f"""
                <tr>
                    <td class="champion-cell">
                        <img src="{normalize_champion(champion)}" alt="{champion}" class="champion-icon">
                        <span class="champion-name">{champion}</span>
                    </td>
                    <td class="games-cell">{games}</td>
                    <td class="wl-cell">{wins}-{losses}</td>
                    <td class="winrate-cell" style="background-color: {winrate_color};">{winrate:.1f}%</td>
                </tr>
        """
    
    # Generate tournaments list
    tournaments_html = "<br>".join([f"• {t}" for t in tournaments])
    
    css = """
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            background: #0a0a0a;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            padding: 20px;
        }
        
        .main-container {
            max-width: 800px;
            margin: 0 auto;
        }
        
        h1 {
            text-align: center;
            color: #fff;
            margin-bottom: 15px;
            font-size: 2rem;
            text-transform: uppercase;
            letter-spacing: 1px;
        }
        
        .stats-summary {
            text-align: center;
            color: #888;
            margin-bottom: 30px;
            font-size: 0.9rem;
        }
        
        .stats-summary strong {
            color: #4CAF50;
        }
        
        .player-section {
            background: linear-gradient(180deg, #1a1a1a 0%, #0d0d0d 100%);
            border: 1px solid #2a2a2a;
            border-radius: 6px;
            padding: 20px;
            margin-bottom: 20px;
        }
        
        .champion-table {
            width: 100%;
            border-collapse: collapse;
        }
        
        .champion-table thead {
            background: rgba(255, 255, 255, 0.05);
        }
        
        .champion-table th {
            color: #fff;
            padding: 12px 10px;
            text-align: left;
            font-weight: 600;
            font-size: 0.8rem;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            border-bottom: 1px solid #2a2a2a;
        }
        
        .champion-table th:nth-child(2),
        .champion-table th:nth-child(3),
        .champion-table th:nth-child(4) {
            text-align: center;
        }
        
        .champion-table td {
            padding: 10px;
            border-bottom: 1px solid rgba(255, 255, 255, 0.05);
            color: #e4e6eb;
            font-size: 0.85rem;
        }
        
        .champion-table tr:last-child td {
            border-bottom: none;
        }
        
        .champion-table tbody tr:hover {
            background: rgba(255, 255, 255, 0.02);
        }
        
        .champion-cell {
            display: flex;
            align-items: center;
            gap: 10px;
        }
        
        .champion-icon {
            width: 32px;
            height: 32px;
            border-radius: 4px;
            border: 1px solid rgba(255, 255, 255, 0.15);
        }
        
        .champion-name {
            font-weight: 600;
            color: #e4e6eb;
            font-size: 0.9rem;
        }
        
        .games-cell,
        .wl-cell,
        .winrate-cell {
            text-align: center;
            font-weight: 600;
        }
        
        .winrate-cell {
            border-radius: 4px;
            font-weight: 700;
        }
        
        .tournaments-section {
            margin-top: 20px;
            padding: 15px;
            background: rgba(255, 255, 255, 0.02);
            border-radius: 6px;
            border: 1px solid rgba(255, 255, 255, 0.05);
        }
        
        .tournaments-section h3 {
            color: #888;
            font-size: 0.8rem;
            text-transform: uppercase;
            margin-bottom: 10px;
        }
        
        .tournaments-section p {
            color: #666;
            font-size: 0.75rem;
            line-height: 1.6;
        }
    </style>
    """
    
    full_html = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>{title}</title>
        {css}
    </head>
    <body>
        <div class="main-container">
            <h1>🎮 {player}</h1>
            <p class="stats-summary">
                <strong>{total_games}</strong> games played on <strong>{len(df_stats)}</strong> champions
            </p>
            
            <div class="player-section">
                <table class="champion-table">
                    <thead>
                        <tr>
                            <th>Champion</th>
                            <th>Games</th>
                            <th>W-L</th>
                            <th>Winrate</th>
                        </tr>
                    </thead>
                    <tbody>
                        {rows_html}
                    </tbody>
                </table>
            </div>
            
            <div class="tournaments-section">
                <h3>📋 Tournaments Included</h3>
                <p>{tournaments_html}</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    with open(output_filename, 'w', encoding='utf-8') as f:
        f.write(full_html)
    
    print(f"\n✅ Page HTML créée: {output_filename}")


def analyze_team_players_champions(site, team, year=None, tournaments=None, output_dir=".",
                                    roster_year=None, stats_year=None, stats_tournaments=None):
    """
    Analyzes all players from a team and generates individual HTML files
    
    Args:
        site: mwclient Site object
        team: Team name (e.g., "SK Gaming")
        year: Year for BOTH roster lookup AND stats (simple mode)
        tournaments: Tournaments for BOTH roster lookup AND stats (simple mode)
        output_dir: Directory for output files
        
        --- SCOUTING MODE (roster ≠ stats) ---
        roster_year: Year to get the team's current roster (e.g., "2026")
        stats_year: Year to analyze player stats (e.g., "2025")
        stats_tournaments: Tournaments to analyze stats (alternative to stats_year)
        
    Returns:
        dict: Dictionary of player -> DataFrame
    
    Example:
        # Simple mode: same year for roster and stats
        analyze_team_players_champions(site, "SK Gaming", year="2026")
        
        # SCOUTING MODE: Get 2026 roster, analyze their 2025 stats
        analyze_team_players_champions(
            site, "Team Heretics", 
            roster_year="2026",  # Who is on the team NOW
            stats_year="2025"    # What they played LAST YEAR
        )
        
        # Scouting with specific tournaments for stats
        analyze_team_players_champions(
            site, "Team Heretics",
            roster_year="2026",
            stats_tournaments=["EM 2025 Spring", "EM 2025 Summer Main Event"]
        )
    """
    # Determine roster lookup parameters
    if roster_year:
        # Scouting mode: use roster_year for players
        lookup_year = roster_year
        lookup_tournaments = None
    else:
        # Simple mode: use year/tournaments for both
        lookup_year = year
        lookup_tournaments = tournaments
    
    # Determine stats parameters
    if stats_year or stats_tournaments:
        # Scouting mode: different year/tournaments for stats
        analysis_year = stats_year
        analysis_tournaments = stats_tournaments
    else:
        # Simple mode: same as roster
        analysis_year = year
        analysis_tournaments = tournaments
    
    # Get all players from roster
    players = get_team_players(site, team, year=lookup_year, tournaments=lookup_tournaments)
    
    if not players:
        return {}
    
    # Build suffix for filenames
    if stats_year:
        suffix = f"roster{roster_year}_stats{stats_year}"
    elif stats_tournaments:
        suffix = f"roster{roster_year}_custom"
    else:
        suffix = year if year else "custom"
    
    results = {}
    for player in players:
        print(f"\n{'='*60}")
        print(f"📊 Processing {player}...")
        
        # Clean player name for filename (handle special chars)
        clean_name = player.replace(' ', '').replace('(', '').replace(')', '').replace("'", '')
        output_filename = f"{output_dir}/player_{clean_name}_{suffix}.html"
        
        df = analyze_player_champions(
            site, 
            player, 
            year=analysis_year, 
            tournaments=analysis_tournaments,
            output_filename=output_filename
        )
        
        if df is not None:
            results[player] = df
    
    print(f"\n{'='*60}")
    print(f"✅ DONE! Generated stats for {len(results)} players")
    print(f"   Team roster: {team} ({lookup_year})")
    if stats_year:
        print(f"   Stats from: {analysis_year}")
    elif stats_tournaments:
        print(f"   Stats from: {', '.join(analysis_tournaments[:3])}...")
    print(f"{'='*60}")
    
    return results


def scout_team(site, team, roster_year, stats_year, output_dir="."):
    """
    🔍 SCOUTING MODE - Simple wrapper for opponent preparation
    
    Get current roster of a team, then see what those players played LAST YEAR
    (regardless of which team they were on).
    
    Args:
        site: mwclient Site object
        team: Team name (e.g., "Team Heretics")
        roster_year: Year to get roster from (e.g., "2026" = current team)
        stats_year: Year to get stats from (e.g., "2025" = previous season)
        output_dir: Directory for output files
        
    Returns:
        dict: Dictionary of player -> DataFrame
    
    Example:
        # Scout Team Heretics before playing them:
        # - Get their 2026 roster: Ice, Serin, Sheo, Stend, Tracyn
        # - See what they played in 2025 (from ANY team)
        
        scout_team(site, "Team Heretics", roster_year="2026", stats_year="2025")
    """
    print(f"\n{'='*60}")
    print(f"🔍 SCOUTING: {team}")
    print(f"   📋 Roster: {roster_year}")
    print(f"   📊 Stats:  {stats_year}")
    print(f"{'='*60}")
    
    return analyze_team_players_champions(
        site, 
        team, 
        roster_year=roster_year, 
        stats_year=stats_year, 
        output_dir=output_dir
    )


def analyze_team_players_careers(site, team, roster_year, output_dir="."):
    """
    Analyzes FULL CAREER stats for all players on a team's current roster
    
    Args:
        site: mwclient Site object
        team: Team name (e.g., "Team Heretics")
        roster_year: Year to get the current roster (e.g., "2026")
        output_dir: Directory for output files
        
    Returns:
        dict: Dictionary of player -> DataFrame
    
    Example:
        # Get full career stats for all Team Heretics 2026 players
        analyze_team_players_careers(site, "Team Heretics", roster_year="2026")
        
        # This will generate:
        # - player_Ice_career.html (all his games from LCK, etc.)
        # - player_Serin_career.html
        # - player_Sheo_career.html
        # - player_Stend_career.html
        # - player_Tracyn_career.html
    """
    print(f"\n{'='*60}")
    print(f"🎮 FULL CAREER STATS: {team} ({roster_year} roster)")
    print(f"{'='*60}")
    
    # Get current roster
    players = get_team_players(site, team, year=roster_year)
    
    if not players:
        return {}
    
    results = {}
    for player in players:
        print(f"\n{'='*60}")
        print(f"📊 Processing {player} (full career)...")
        
        clean_name = player.replace(' ', '').replace('(', '').replace(')', '').replace("'", '')
        output_filename = f"{output_dir}/player_{clean_name}_career.html"
        
        df = analyze_player_career(site, player, output_filename=output_filename)
        
        if df is not None:
            results[player] = df
    
    print(f"\n{'='*60}")
    print(f"✅ DONE! Generated CAREER stats for {len(results)} players from {team}")
    print(f"{'='*60}")
    
    return results
