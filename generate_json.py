import pandas as pd
import json
import sys
import re
from collections import defaultdict
from datetime import date

# ── OWNER NAME → JSON KEY MAPPING ─────────────────────────────────────────────
NAME_TO_KEY = {
    'Alex Vander Linden': 'alex',
    'Andy Jacobs': 'andy',
    'Brian Thackston': 'brian',
    'Daniel Brenner': 'daniel',
    'Dylan Thackston': 'dylan',
    'Jack Corcoran': 'jack',
    'Jonathan Franks': 'jon',
    'Jon Franks': 'jon',
    'Jordan Powell': 'jordan',
    'Kyle Gilbreath': 'kyle',
    'Lucas Bradshaw': 'luke',
    'Luke Bradshaw': 'luke',
    'Mateo Martinez': 'matt',
    'Matt Martinez': 'matt',
    'Mike Merrick': 'mike',
    'Scott Murphy': 'scott',
    'Tim Hermann': 'tim',
    'Wade Alger': 'wade',
    # Historical owners
    'Alex McGrew': 'alex_m',
    'Anthony Brown': 'anthony_b',
    'Anthony Monaco': 'anthony_m',
    'Christine Boluda': 'christine',
    'James Trueblood': 'james',
    'Michael Vinup': 'mike_v',
    'Michelle Conklin': 'michelle_c',
    'Michelle Trueblood': 'michelle_t',
    'Pauly Rodney': 'pauly',
    'Taylor Ely': 'taylor',
    'Tim Campbell': 'tim_c',
    'Tyler Trueblood': 'tyler',
}

ACTIVE_KEYS = {'alex','andy','brian','daniel','dylan','jack','jordan','kyle','luke','matt','mike','scott','tim','wade'}

DISPLAY_NAMES = {
    'alex': 'Alex V.', 'andy': 'Andy', 'brian': 'Brian', 'daniel': 'Daniel',
    'dylan': 'Dylan', 'jack': 'Jack', 'jordan': 'Jordan', 'kyle': 'Kyle',
    'luke': 'Luke', 'matt': 'Matt', 'mike': 'Mike M.', 'scott': 'Scott',
    'tim': 'Tim H.', 'wade': 'Wade',
}

# Display names for career records tables (matches what the HTML expects)
CAREER_DISPLAY_NAMES = {
    'alex': 'Alex V.', 'andy': 'Andy', 'brian': 'Brian', 'daniel': 'Daniel',
    'dylan': 'Dylan', 'jack': 'Jack', 'jordan': 'Jordan', 'kyle': 'Kyle',
    'luke': 'Luke', 'matt': 'Matt', 'mike': 'Mike M.', 'scott': 'Scott',
    'tim': 'Tim H.', 'wade': 'Wade',
    'alex_m': 'Alex M.', 'anthony_b': 'Anthony B.', 'anthony_m': 'Anthony M.',
    'christine': 'Christine', 'james': 'James', 'mike_v': 'Michael V.',
    'michelle_c': 'Michelle C.', 'michelle_t': 'Michelle T.',
    'pauly': 'Pauly', 'taylor': 'Taylor', 'tim_c': 'Tim C.', 'tyler': 'Tyler',
    'jon': 'Jon',
}

def get_key(name):
    if not isinstance(name, str):
        return None
    return NAME_TO_KEY.get(name.strip())

def load_xlsx(path):
    xl = pd.read_excel(path, sheet_name=None)
    matchups = xl['High.Low and All Matchups']
    season_stats = xl['Season Stats']
    all_time_lucky = xl['All-Time Lucky']
    matchups = matchups[matchups['Year'].between(2014, 2030)].copy()
    matchups['Year'] = matchups['Year'].astype(int)
    matchups['Week'] = matchups['Week'].astype(int)
    matchups['Away Score'] = pd.to_numeric(matchups['Away Score'], errors='coerce')
    matchups['Home Score'] = pd.to_numeric(matchups['Home Score'], errors='coerce')

    # Capture upcoming games (blank scores) BEFORE dropping them
    upcoming_raw = matchups[matchups['Away Score'].isna() | matchups['Home Score'].isna()].copy()
    upcoming_raw['away_key'] = upcoming_raw['Away Owner'].apply(get_key)
    upcoming_raw['home_key'] = upcoming_raw['Home Owner'].apply(get_key)
    upcoming_raw['game_type'] = upcoming_raw['Regular/Playoff/Consolation'].str.strip()

    # Build nextGame lookup: owner_key -> {week, year, opponent, opponentKey, type}
    next_game = {}
    for _, row in upcoming_raw.iterrows():
        ak = row['away_key']
        hk = row['home_key']
        yr = int(row['Year'])
        wk = int(row['Week'])
        gtype = row['game_type'] if isinstance(row['game_type'], str) else 'Regular'
        if ak and hk:
            next_game[ak] = {
                'week': wk,
                'year': yr,
                'opponent': DISPLAY_NAMES.get(hk, hk),
                'opponentKey': hk,
                'type': gtype,
            }
            next_game[hk] = {
                'week': wk,
                'year': yr,
                'opponent': DISPLAY_NAMES.get(ak, ak),
                'opponentKey': ak,
                'type': gtype,
            }

    matchups = matchups.dropna(subset=['Away Score','Home Score'])
    matchups['away_key'] = matchups['Away Owner'].apply(get_key)
    matchups['home_key'] = matchups['Home Owner'].apply(get_key)
    matchups['game_type'] = matchups['Regular/Playoff/Consolation'].str.strip()
    return matchups, season_stats, all_time_lucky, next_game

def compute_career_stats(matchups):
    stats = defaultdict(lambda: {
        'wins': 0, 'losses': 0,
        'reg_wins': 0, 'reg_losses': 0,
        'po_wins': 0, 'po_losses': 0,
        'con_wins': 0, 'con_losses': 0,
        'pts_for': 0.0, 'pts_against': 0.0,
        'reg_pts_for': 0.0, 'reg_pts_against': 0.0,
        'po_pts_for': 0.0, 'po_pts_against': 0.0,
        'con_pts_for': 0.0, 'con_pts_against': 0.0,
        'games': 0, 'reg_games': 0, 'po_games': 0, 'con_games': 0,
        'high_score': 0.0,
        'weekly_highs': 0,
        'boom_games': 0, 'start_games': 0, 'bust_games': 0, 'mid_games': 0,
        'playoff_apps': set(), 'playoff_wins': 0,
        'final_fours': set(), 'finals': set(), 'championships': set(),
        'consolation_wins': 0,
        'seasons': set(),
    })

    reg = matchups[matchups['game_type'] == 'Regular'].copy()
    season_avgs = {}
    for yr, grp in reg.groupby('Year'):
        all_scores = list(grp['Away Score']) + list(grp['Home Score'])
        season_avgs[yr] = sum(all_scores) / len(all_scores) if all_scores else 100.0

    weekly_highs = {}
    for (yr, wk, gtype), grp in matchups.groupby(['Year','Week','game_type']):
        if gtype == 'Regular':
            scores = []
            for _, row in grp.iterrows():
                ak, hk = row['away_key'], row['home_key']
                if ak: scores.append((row['Away Score'], ak))
                if hk: scores.append((row['Home Score'], hk))
            if scores:
                max_score = max(s for s,_ in scores)
                winners = [k for s,k in scores if s == max_score]
                for k in winners:
                    weekly_highs[(yr, wk, k)] = True

    for _, row in matchups.iterrows():
        yr = row['Year']
        ak = row['away_key']
        hk = row['home_key']
        asc = float(row['Away Score'])
        hsc = float(row['Home Score'])
        gtype = row['game_type']
        wk = row['Week']
        away_won = asc > hsc

        for key, score, opp_score, won in [(ak, asc, hsc, away_won), (hk, hsc, asc, not away_won)]:
            if not key:
                continue
            s = stats[key]
            s['seasons'].add(yr)
            s['high_score'] = max(s['high_score'], score)

            if gtype == 'Regular':
                s['reg_games'] += 1
                s['reg_pts_for'] += score
                s['reg_pts_against'] += opp_score
                s['games'] += 1
                s['pts_for'] += score
                s['pts_against'] += opp_score
                if won:
                    s['wins'] += 1
                    s['reg_wins'] += 1
                else:
                    s['losses'] += 1
                    s['reg_losses'] += 1
                avg = season_avgs.get(yr, 100.0)
                if score >= avg * 1.20:
                    s['boom_games'] += 1
                    s['start_games'] += 1
                elif score >= avg:
                    s['start_games'] += 1
                elif score <= avg * 0.80:
                    s['bust_games'] += 1
                else:
                    s['mid_games'] += 1
                if (yr, wk, key) in weekly_highs:
                    s['weekly_highs'] += 1

            elif gtype == 'Playoff':
                s['po_games'] += 1
                s['po_pts_for'] += score
                s['po_pts_against'] += opp_score
                s['games'] += 1
                s['pts_for'] += score
                s['pts_against'] += opp_score
                if won:
                    s['wins'] += 1
                    s['po_wins'] += 1
                else:
                    s['losses'] += 1
                    s['po_losses'] += 1
                s['playoff_apps'].add(yr)
                s['playoff_wins'] += 1 if won else 0

            elif gtype == 'Consolation':
                s['con_games'] += 1
                s['con_pts_for'] += score
                s['con_pts_against'] += opp_score
                s['games'] += 1
                s['pts_for'] += score
                s['pts_against'] += opp_score
                if won:
                    s['wins'] += 1
                    s['con_wins'] += 1
                else:
                    s['losses'] += 1
                    s['con_losses'] += 1

    return stats, season_avgs, weekly_highs

def compute_playoff_structure(matchups):
    playoff_games = matchups[matchups['game_type'] == 'Playoff'].copy()
    finals = defaultdict(set)
    final_fours = defaultdict(set)
    championships = defaultdict(set)

    for yr, grp in playoff_games.groupby('Year'):
        max_wk = grp['Week'].max()
        semi_wk = max_wk - 1

        for _, row in grp.iterrows():
            ak, hk = row['away_key'], row['home_key']
            wk = row['Week']
            away_won = float(row['Away Score']) > float(row['Home Score'])

            if wk == max_wk:
                for k in [ak, hk]:
                    if k: finals[k].add(yr)
                winner = ak if away_won else hk
                if winner: championships[winner].add(yr)
            elif wk == semi_wk:
                for k in [ak, hk]:
                    if k: final_fours[k].add(yr)

    return finals, final_fours, championships

def compute_h2h(matchups):
    h2h_summary = defaultdict(lambda: defaultdict(lambda: {'all': [0,0], 'reg': [0,0], 'playoff': [0,0], 'consolation': [0,0]}))
    h2h_logs = defaultdict(list)

    for _, row in matchups.iterrows():
        ak = row['away_key']
        hk = row['home_key']
        if not ak or not hk:
            continue
        asc = float(row['Away Score'])
        hsc = float(row['Home Score'])
        gtype = row['game_type']
        yr = row['Year']
        wk = row['Week']
        away_won = asc > hsc

        pair = tuple(sorted([ak, hk]))
        p0, p1 = pair
        p0_won = (p0 == ak and away_won) or (p0 == hk and not away_won)
        p0_score = asc if p0 == ak else hsc
        p1_score = hsc if p0 == ak else asc

        h2h_logs[f"{p0}||{p1}"].append({
            'y': yr, 'w': wk,
            't': gtype,
            's0': round(p0_score, 2),
            's1': round(p1_score, 2),
            'w0': 1 if p0_won else 0,
        })

        gtype_key = gtype.lower() if gtype.lower() in ['regular','playoff','consolation'] else 'regular'
        for owner, won in [(ak, away_won), (hk, not away_won)]:
            opp = hk if owner == ak else ak
            if not owner or not opp:
                continue
            idx = 0 if won else 1
            h2h_summary[owner][opp]['all'][idx] += 1
            if gtype_key == 'regular':
                h2h_summary[owner][opp]['reg'][idx] += 1
            elif gtype_key == 'playoff':
                h2h_summary[owner][opp]['playoff'][idx] += 1
            elif gtype_key == 'consolation':
                h2h_summary[owner][opp]['consolation'][idx] += 1

    return h2h_summary, h2h_logs

def compute_season_records(matchups):
    records = defaultdict(lambda: defaultdict(lambda: {
        'wins': 0, 'losses': 0, 'pts_for': 0.0, 'pts_against': 0.0, 'games': 0
    }))
    reg = matchups[matchups['game_type'] == 'Regular']
    for _, row in reg.iterrows():
        ak, hk = row['away_key'], row['home_key']
        asc, hsc = float(row['Away Score']), float(row['Home Score'])
        yr = row['Year']
        away_won = asc > hsc
        for key, score, opp_score, won in [(ak, asc, hsc, away_won), (hk, hsc, asc, not away_won)]:
            if not key: continue
            r = records[key][yr]
            r['pts_for'] += score
            r['pts_against'] += opp_score
            r['games'] += 1
            if won: r['wins'] += 1
            else: r['losses'] += 1
    return records

def compute_standings(matchups, year):
    reg = matchups[(matchups['game_type'] == 'Regular') & (matchups['Year'] == year)]
    wins = defaultdict(int)
    losses = defaultdict(int)
    pts = defaultdict(float)
    for _, row in reg.iterrows():
        ak, hk = row['away_key'], row['home_key']
        asc, hsc = float(row['Away Score']), float(row['Home Score'])
        away_won = asc > hsc
        if ak:
            pts[ak] += asc
            if away_won: wins[ak] += 1
            else: losses[ak] += 1
        if hk:
            pts[hk] += hsc
            if not away_won: wins[hk] += 1
            else: losses[hk] += 1
    all_keys = set(list(wins.keys()) + list(losses.keys()))
    ranked = sorted(all_keys, key=lambda k: (-wins[k], -pts[k]))
    standings = {k: i+1 for i, k in enumerate(ranked)}
    return standings

def get_last_game(matchups, key, year):
    owner_games = matchups[
        ((matchups['away_key'] == key) | (matchups['home_key'] == key)) &
        (matchups['Year'] == year)
    ].sort_values(['Week'], ascending=False)
    if owner_games.empty:
        return None
    row = owner_games.iloc[0]
    is_away = row['away_key'] == key
    my_score = float(row['Away Score']) if is_away else float(row['Home Score'])
    opp_score = float(row['Home Score']) if is_away else float(row['Away Score'])
    opp_key = row['home_key'] if is_away else row['away_key']
    result = 'W' if my_score > opp_score else 'L'
    gtype = row['game_type']
    return {
        'week': int(row['Week']),
        'result': result,
        'score': round(my_score, 2),
        'oppScore': round(opp_score, 2),
        'opponent': DISPLAY_NAMES.get(opp_key, opp_key.capitalize()) if opp_key else '—',
        'opponentKey': opp_key,
        'type': gtype,
    }

def rank_owners(stat_dict, reverse=True):
    active = {k: v for k, v in stat_dict.items() if k in ACTIVE_KEYS}
    sorted_owners = sorted(active.items(), key=lambda x: x[1], reverse=reverse)
    ranks = {}
    for i, (k, v) in enumerate(sorted_owners):
        ranks[k] = i + 1
    return ranks

def safe_round(v, n=2):
    try:
        return round(float(v), n)
    except:
        return None

def safe_div(a, b, n=2):
    try:
        return safe_round(a / b, n) if b else None
    except:
        return None

def build_career_records(career_stats, finals, final_fours, championships, career_earnings,
                         career_power_scores, career_luck_lookup, existing_json):
    """
    Build the careerRecords section for all owners.
    Active owners: computed fresh from matchup log.
    Historical owners: preserved from existing JSON (frozen).
    """
    existing_cr = existing_json.get('careerRecords', {})

    all_keys = set(CAREER_DISPLAY_NAMES.keys())
    records = {}

    for key in all_keys:
        display = CAREER_DISPLAY_NAMES[key]
        is_active = key in ACTIVE_KEYS

        if is_active:
            s = career_stats.get(key, {})
            if not s:
                records[key] = existing_cr.get(key, {'display': display})
                continue

            rg = s['reg_games']
            pg = s['po_games']
            cg = s['con_games']
            ag = rg + pg + cg

            seasons_count = len(s['seasons'])

            # wins/losses
            wins_all = s['reg_wins'] + s['po_wins'] + s['con_wins']
            losses_all = s['reg_losses'] + s['po_losses'] + s['con_losses']

            # pts for
            pf_all = s['reg_pts_for'] + s['po_pts_for'] + s['con_pts_for']
            pa_all = s['reg_pts_against'] + s['po_pts_against'] + s['con_pts_against']

            # win pct (include null for con if no con games)
            def wpct(w, l):
                total = w + l
                return safe_round(w / total, 4) if total else None

            # PPG
            ppg_all = safe_div(pf_all, ag)
            ppg_reg = safe_div(s['reg_pts_for'], rg)
            ppg_po  = safe_div(s['po_pts_for'], pg)
            ppg_con = safe_div(s['con_pts_for'], cg)

            # PAG
            pag_all = safe_div(pa_all, ag)
            pag_reg = safe_div(s['reg_pts_against'], rg)
            pag_po  = safe_div(s['po_pts_against'], pg)
            pag_con = safe_div(s['con_pts_against'], cg)

            # career champs/finals with year lists
            champ_years = sorted([str(y) for y in championships.get(key, set())])
            finals_years = sorted([str(y) for y in finals.get(key, set())])
            ff_years     = sorted([str(y) for y in final_fours.get(key, set())])
            po_apps      = sorted([str(y) for y in s['playoff_apps']])

            # career power score — from existing JSON manual field
            existing_active_cr = existing_cr.get(key, {})
            career_ps = existing_active_cr.get('careerPowerScore')

            # career luck — from existing JSON manual field
            career_luck = existing_active_cr.get('careerLuckRate')

            records[key] = {
                'display': display,
                'active': True,
                'seasons': seasons_count,
                'wins':   [wins_all,     s['reg_wins'],  s['po_wins'],  s['con_wins']],
                'losses': [losses_all,   s['reg_losses'],s['po_losses'],s['con_losses']],
                'pf':     [safe_round(pf_all), safe_round(s['reg_pts_for']), safe_round(s['po_pts_for']) if pg else None, safe_round(s['con_pts_for']) if cg else None],
                'pa':     [safe_round(pa_all), safe_round(s['reg_pts_against']), safe_round(s['po_pts_against']) if pg else None, safe_round(s['con_pts_against']) if cg else None],
                'winPct': [wpct(wins_all, losses_all), wpct(s['reg_wins'], s['reg_losses']), wpct(s['po_wins'], s['po_losses']) if pg else None, wpct(s['con_wins'], s['con_losses']) if cg else None],
                'ppg':    [ppg_all, ppg_reg, ppg_po if pg else None, ppg_con if cg else None],
                'pag':    [pag_all, pag_reg, pag_po if pg else None, pag_con if cg else None],
                'careerPowerScore': career_ps,
                'careerLuckRate': career_luck,
                'careerEarnings': safe_round(career_earnings.get(key, 0), 2),
                'championships': [len(champ_years), champ_years],
                'finals':        [len(finals_years), finals_years],
                'finalFours':    [len(ff_years), ff_years],
                'playoffApps':   [len(po_apps), po_apps],
                'playoffWins':   s['playoff_wins'],
            }
        else:
            # Historical: preserve frozen data from existing JSON, never overwrite
            if key in existing_cr:
                records[key] = existing_cr[key]
            # If not yet in existing JSON, leave absent (will be seeded manually)

    return records

def build_boom_bust(career_stats, existing_json):
    """
    Build the boomBust section.
    Active owners: computed fresh.
    Historical owners: preserved frozen from existing JSON.
    """
    existing_bb = existing_json.get('boomBust', {})

    def archetype(key, boom, start, bust, seasons):
        if seasons < 1:
            return 'Pending'
        if key == 'kyle':
            return 'Outlier'
        if boom >= 0.28:
            if bust >= 0.20:
                return 'High Variance'
            return 'Boom Machine'
        if start >= 0.55:
            if bust <= 0.10:
                return 'Reliable'
        if bust >= 0.25 and boom <= 0.18:
            return 'Underperforming'
        if start >= 0.45:
            return 'Reliable'
        if boom <= 0.18 and bust <= 0.20:
            return 'Middling'
        return 'Underperforming'

    def photo_id(key):
        overrides = {'mike': 'mike', 'tim': 'tim', 'alex': 'alex'}
        return overrides.get(key, key)

    records = {}

    for key in ACTIVE_KEYS:
        s = career_stats.get(key, {})
        rg = s.get('reg_games', 0)
        seasons_count = len(s.get('seasons', set()))

        def rate(n):
            return safe_round(n / rg, 4) if rg else 0

        boom_r  = rate(s.get('boom_games', 0))
        start_r = rate(s.get('start_games', 0))
        mid_r   = rate(s.get('mid_games', 0))
        bust_r  = rate(s.get('bust_games', 0))

        def split_stats(gtype):
            sg = s.get(f'{gtype}_games', 0)
            if not sg:
                return None
            # Need per-gtype boom/bust — not tracked separately yet, use overall reg for now
            return None  # placeholder; reg split is below

        # Regular season split (same as overall boom/bust since we only track reg)
        reg_stats = {
            'games': rg,
            'boom_rate': boom_r,
            'start_rate': start_r,
            'mid_rate': mid_r,
            'bust_rate': bust_r,
        } if rg else None

        # Preserve existing playoff/consolation splits from existing JSON if present
        existing_entry = existing_json.get('boomBust', {}).get('active', {}).get(
            DISPLAY_NAMES.get(key, key), {}
        )
        ex_stats = existing_entry.get('stats', {})

        arch = archetype(key, boom_r, start_r, bust_r, seasons_count)

        records[key] = {
            'display': DISPLAY_NAMES[key],
            'active': True,
            'archetype': arch,
            'photoId': photo_id(key),
            'stats': {
                'all': {
                    'games': rg,
                    'boom_rate': boom_r,
                    'start_rate': start_r,
                    'mid_rate': mid_r,
                    'bust_rate': bust_r,
                } if rg else None,
                'regular': reg_stats,
                # Preserve existing playoff/consolation from prior JSON
                'playoff':    ex_stats.get('playoff'),
                'consolation': ex_stats.get('consolation'),
            }
        }

    # Historical: frozen, preserved from existing JSON
    historical = existing_json.get('boomBust', {}).get('historical', {})

    return {'active': records, 'historical': historical}

def build_team_names(matchups, season_stats, existing_json):
    """
    Collect all team names from xlsx, merge with existing list in JSON,
    deduplicate (case-insensitive, strip whitespace), return sorted list.
    """
    existing_names = set(existing_json.get('teamNames', []))

    new_names = set()
    # From matchups sheet
    for col in ['Away Team Name', 'Home Team Name']:
        if col in matchups.columns:
            for n in matchups[col].dropna():
                new_names.add(str(n).strip())
    # From season stats sheet
    if 'Team Name' in season_stats.columns:
        for n in season_stats['Team Name'].dropna():
            new_names.add(str(n).strip())

    # Merge: add any genuinely new names (case-insensitive check)
    existing_lower = {n.lower(): n for n in existing_names}
    merged = dict(existing_lower)  # lower -> canonical form
    for name in new_names:
        if name and name.lower() not in merged:
            merged[name.lower()] = name

    result = sorted(merged.values(), key=lambda x: x.lower())
    return result

def build_h2h_data(matchups, h2h_logs):
    out = {}
    for pair_key, games in h2h_logs.items():
        p0, p1 = pair_key.split('||')
        sorted_games = sorted(games, key=lambda g: (g['y'], g['w']))

        # Compute win totals
        all_w0 = sum(g['w0'] for g in sorted_games)
        all_w1 = len(sorted_games) - all_w0
        reg_games   = [g for g in sorted_games if g['t'] == 'Regular']
        po_games    = [g for g in sorted_games if g['t'] == 'Playoff']
        con_games   = [g for g in sorted_games if g['t'] == 'Consolation']

        def w_counts(gs):
            w0 = sum(g['w0'] for g in gs)
            return {'w0': w0, 'w1': len(gs) - w0}

        out[pair_key] = {
            'p0': DISPLAY_NAMES.get(p0, p0),
            'p1': DISPLAY_NAMES.get(p1, p1),
            'p0key': p0,
            'p1key': p1,
            'all':        w_counts(sorted_games),
            'reg':        w_counts(reg_games),
            'playoff':    w_counts(po_games),
            'consolation':w_counts(con_games),
            'games': sorted_games,
        }
    return out

def build_profiles_data(matchups, season_stats, all_time_lucky, existing_json, next_game=None):
    if next_game is None:
        next_game = {}
    today = date.today().isoformat()
    current_year = matchups['Year'].max()

    career_stats, season_avgs, weekly_highs = compute_career_stats(matchups)
    finals, final_fours, championships = compute_playoff_structure(matchups)
    h2h_summary, h2h_logs = compute_h2h(matchups)
    season_records = compute_season_records(matchups)
    standings = compute_standings(matchups, current_year)

    ss_lookup = {}
    ss_valid = season_stats[season_stats['Year'].between(2014, 2030)].copy()
    for _, row in ss_valid.iterrows():
        key = get_key(str(row['Owner']))
        if key:
            yr = int(row['Year'])
            ss_lookup[(key, yr)] = row

    lucky_lookup = {}
    for _, row in all_time_lucky.head(20).iterrows():
        key = get_key(str(row['Owner']))
        if key and pd.notna(row.get('Lucky/Unlucky %')):
            lucky_lookup[key] = row

    career_earnings = defaultdict(float)
    for _, row in ss_valid.iterrows():
        k = get_key(str(row['Owner']))
        if k and pd.notna(row.get('Net Earnings')):
            career_earnings[k] += float(row['Net Earnings'])

    career_power_scores = defaultdict(list)
    career_weeks_at_1 = defaultdict(int)
    for _, row in ss_valid.iterrows():
        k = get_key(str(row['Owner']))
        if k:
            ps = row.get('Regular Season Power Score')
            if pd.notna(ps):
                career_power_scores[k].append(float(ps))
            w1 = row.get('Regular Season Weeks at #1')
            if pd.notna(w1):
                career_weeks_at_1[k] += int(w1)

    def make_rank_dict(stat_fn):
        d = {k: stat_fn(career_stats[k]) for k in ACTIVE_KEYS if k in career_stats}
        return rank_owners(d)

    reg_wins_ranks = make_rank_dict(lambda s: s['reg_wins'])
    win_pct_ranks = make_rank_dict(lambda s: s['reg_wins']/s['reg_games'] if s['reg_games'] else 0)
    ppg_ranks = make_rank_dict(lambda s: s['reg_pts_for']/s['reg_games'] if s['reg_games'] else 0)
    pts_against_ranks = make_rank_dict(lambda s: s['reg_pts_against']/s['reg_games'] if s['reg_games'] else 0)
    high_score_ranks = make_rank_dict(lambda s: s['high_score'])
    weekly_high_ranks = make_rank_dict(lambda s: s['weekly_highs'])
    boom_ranks = make_rank_dict(lambda s: s['boom_games']/s['reg_games'] if s['reg_games'] else 0)
    start_ranks = make_rank_dict(lambda s: s['start_games']/s['reg_games'] if s['reg_games'] else 0)
    total_pts = sum(career_stats[k]['reg_pts_for'] for k in ACTIVE_KEYS if k in career_stats)
    pt_share_ranks = rank_owners({k: career_stats[k]['reg_pts_for']/total_pts for k in ACTIVE_KEYS if k in career_stats})
    playoff_app_ranks = make_rank_dict(lambda s: len(s['playoff_apps']))
    playoff_win_ranks = make_rank_dict(lambda s: s['playoff_wins'])
    earnings_ranks = rank_owners({k: career_earnings[k] for k in ACTIVE_KEYS if k in career_earnings})
    career_ps_ranks = rank_owners({k: sum(career_power_scores[k])/len(career_power_scores[k]) for k in ACTIVE_KEYS if career_power_scores.get(k)})
    weeks_at_1_ranks = rank_owners({k: career_weeks_at_1[k] for k in ACTIVE_KEYS})

    owners_out = {}
    for key in ACTIVE_KEYS:
        existing_owner = existing_json.get('owners', {}).get(key, {})
        s = career_stats.get(key, {})
        if not s:
            owners_out[key] = existing_owner
            continue

        reg_games = s['reg_games']
        reg_wins = s['reg_wins']
        reg_losses = s['reg_losses']
        reg_pts = s['reg_pts_for']
        reg_pts_against = s['reg_pts_against']
        ppg = reg_pts / reg_games if reg_games else 0
        ppga = reg_pts_against / reg_games if reg_games else 0
        win_pct = reg_wins / reg_games if reg_games else 0
        boom_rate = s['boom_games'] / reg_games if reg_games else 0
        start_rate = s['start_games'] / reg_games if reg_games else 0
        pt_share = reg_pts / total_pts if total_pts else 0

        curr = season_records[key].get(current_year, {})
        curr_wins = curr.get('wins', 0)
        curr_losses = curr.get('losses', 0)
        curr_games = curr.get('games', 0)
        curr_ppg = curr['pts_for'] / curr_games if curr_games else 0
        curr_standing = standings.get(key, '—')
        last_game = get_last_game(matchups, key, current_year)

        ss_row = ss_lookup.get((key, current_year), {})
        team_name_curr = ss_row.get('Team Name', '') if hasattr(ss_row, 'get') else ''
        power_score_curr = safe_round(ss_row.get('Regular Season Power Score')) if hasattr(ss_row, 'get') else None
        weeks_at_1_curr = safe_round(ss_row.get('Regular Season Weeks at #1', 0), 0) if hasattr(ss_row, 'get') else 0
        luck_curr = safe_round(ss_row.get('Lucky/Unlucky %'), 4) if hasattr(ss_row, 'get') else None
        prestige_curr = safe_round(ss_row.get('Prestige Earned'), 0) if hasattr(ss_row, 'get') else None
        net_earn_curr = safe_round(ss_row.get('Net Earnings'), 2) if hasattr(ss_row, 'get') else None

        lucky_row = lucky_lookup.get(key, {})
        career_luck = safe_round(lucky_row.get('Lucky/Unlucky %'), 4) if hasattr(lucky_row, 'get') else None

        all_seasons = sorted(s['seasons'])
        seasons_list = []
        for yr in all_seasons:
            yr_rec = season_records[key].get(yr, {})
            yr_ss = ss_lookup.get((key, yr), {})
            yr_wins = yr_rec.get('wins', 0)
            yr_losses = yr_rec.get('losses', 0)
            yr_games = yr_rec.get('games', 0)
            yr_ppg = yr_rec['pts_for'] / yr_games if yr_games else 0

            existing_seasons = {s_['year']: s_ for s_ in existing_owner.get('seasons', []) if 'year' in s_}
            existing_yr = existing_seasons.get(yr, {})

            team_name = yr_ss.get('Team Name', existing_yr.get('teamName', '')) if hasattr(yr_ss, 'get') else existing_yr.get('teamName', '')
            power_score = safe_round(yr_ss.get('Regular Season Power Score')) if hasattr(yr_ss, 'get') else existing_yr.get('powerScore')
            prestige_earned = safe_round(yr_ss.get('Prestige Earned'), 0) if hasattr(yr_ss, 'get') else existing_yr.get('prestigeEarned')
            net_earnings = safe_round(yr_ss.get('Net Earnings'), 2) if hasattr(yr_ss, 'get') else existing_yr.get('winnings')

            all_yr_games = matchups[(matchups['Year'] == yr) &
                                    ((matchups['away_key'] == key) | (matchups['home_key'] == key))]
            total_pts_yr = sum(
                float(r['Away Score']) if r['away_key'] == key else float(r['Home Score'])
                for _, r in all_yr_games.iterrows()
            )
            total_games_yr = len(all_yr_games)
            total_league_pts = sum(
                float(r['Away Score']) + float(r['Home Score'])
                for _, r in matchups[matchups['Year'] == yr].iterrows()
            )
            pt_share_yr = total_pts_yr / total_league_pts if total_league_pts else 0

            yr_finals = key in finals and yr in finals[key]
            yr_champion = key in championships and yr in championships[key]
            yr_ff = key in final_fours and yr in final_fours[key]
            yr_playoff = yr in s['playoff_apps']

            if yr_champion:
                result = 'champion'
            elif yr_finals:
                result = 'finalist'
            elif yr_ff:
                result = 'semifinal'
            elif yr_playoff:
                result = 'playoff'
            else:
                result = existing_yr.get('result', 'missed')

            seasons_list.append({
                'year': yr,
                'teamName': str(team_name) if team_name and str(team_name) != 'nan' else None,
                'record': f"{yr_wins}-{yr_losses}",
                'finish': existing_yr.get('finish'),
                'ptsPerGame': safe_round(yr_ppg),
                'pointShare': safe_round(pt_share_yr, 4),
                'powerScore': power_score,
                'prestigeEarned': int(prestige_earned) if prestige_earned is not None else None,
                'winnings': net_earnings,
                'result': result,
                'playoffResult': existing_yr.get('playoffResult'),
            })

        chart_years = sorted(s['seasons'])
        wins_chart = [season_records[key].get(yr, {}).get('wins', 0) for yr in chart_years]
        pt_share_chart = []
        for yr in chart_years:
            yr_all = matchups[matchups['Year'] == yr]
            total_league = sum(float(r['Away Score']) + float(r['Home Score']) for _, r in yr_all.iterrows())
            owner_games = yr_all[(yr_all['away_key'] == key) | (yr_all['home_key'] == key)]
            owner_pts = sum(float(r['Away Score']) if r['away_key'] == key else float(r['Home Score']) for _, r in owner_games.iterrows())
            pt_share_chart.append(safe_round(owner_pts / total_league if total_league else 0, 4))

        prestige_chart = []
        winnings_chart = []
        for yr in chart_years:
            yr_ss = ss_lookup.get((key, yr), {})
            prestige_chart.append(int(safe_round(yr_ss.get('Prestige Earned', 0), 0)) if hasattr(yr_ss, 'get') else None)
            winnings_chart.append(safe_round(yr_ss.get('Net Earnings'), 2) if hasattr(yr_ss, 'get') else None)

        owner_h2h = {}
        for opp_key, records in h2h_summary.get(key, {}).items():
            opp_display = DISPLAY_NAMES.get(opp_key, opp_key)
            owner_h2h[opp_display] = {
                'all': records['all'],
                'reg': records['reg'],
                'playoff': records['playoff'],
                'consolation': records['consolation'],
            }

        owner_out = {
            'name': existing_owner.get('name', key.capitalize()),
            'nickname': existing_owner.get('nickname'),
            'photo': existing_owner.get('photo'),
            'location': existing_owner.get('location'),
            'locationEmoji': existing_owner.get('locationEmoji'),
            'memberSince': existing_owner.get('memberSince'),
            'broughtInBy': existing_owner.get('broughtInBy'),
            'ryderCup': existing_owner.get('ryderCup'),
            'statusLines': existing_owner.get('statusLines', []),
            'traits': existing_owner.get('traits', []),
            'narrative': existing_owner.get('narrative'),
            'dossierNotes': existing_owner.get('dossierNotes'),
            'rivalries': existing_owner.get('rivalries', {}),
            'trophies': existing_owner.get('trophies', []),
            'lastUpdated': existing_owner.get('lastUpdated'),
            'currentSeason': {
                'year': int(current_year),
                'record': f"{curr_wins}-{curr_losses}",
                'standing': curr_standing,
                'ptsPerGame': safe_round(curr_ppg),
                'teamName': str(team_name_curr) if team_name_curr and str(team_name_curr) != 'nan' else None,
                'powerScore': power_score_curr,
                'weeksAt1': int(weeks_at_1_curr) if (weeks_at_1_curr and not pd.isna(weeks_at_1_curr)) else 0,
                'luckRate': luck_curr,
                'prestigeEarned': int(prestige_curr) if (prestige_curr and not pd.isna(prestige_curr)) else 0,
                'netEarnings': net_earn_curr,
                'lastGame': last_game,
                'nextGame': next_game.get(key) or None,
            },
            'careerStats': {
                'general': existing_owner.get('careerStats', {}).get('general', []),
                'regularSeason': [
                    {'stat': 'Wins', 'value': reg_wins, 'rank': reg_wins_ranks.get(key), 'explainer': 'Regular season wins only'},
                    {'stat': 'Win %', 'value': safe_round(win_pct, 4), 'rank': win_pct_ranks.get(key), 'explainer': 'Regular season win percentage'},
                    {'stat': 'PPG', 'value': safe_round(ppg, 2), 'rank': ppg_ranks.get(key), 'explainer': 'Points per game (regular season)'},
                    {'stat': 'Point Share', 'value': safe_round(pt_share, 4), 'rank': pt_share_ranks.get(key), 'explainer': 'Share of all regular season points scored'},
                    {'stat': 'High Score', 'value': safe_round(s['high_score'], 2), 'rank': high_score_ranks.get(key), 'explainer': 'Highest single game score'},
                    {'stat': 'Weekly High Scores', 'value': s['weekly_highs'], 'rank': weekly_high_ranks.get(key), 'explainer': 'Number of weekly high scores'},
                    {'stat': 'Boom Rate', 'value': safe_round(boom_rate, 4), 'rank': boom_ranks.get(key), 'explainer': '% of weeks scoring 120%+ of league average'},
                    {'stat': 'Start Rate', 'value': safe_round(start_rate, 4), 'rank': start_ranks.get(key), 'explainer': '% of weeks scoring at or above league average'},
                    {'stat': 'Points Against/Game', 'value': safe_round(ppga, 2), 'rank': pts_against_ranks.get(key), 'explainer': 'Average points scored against per game'},
                    {'stat': 'Luck Rate', 'value': career_luck, 'rank': None, 'explainer': 'Win rate vs expected all-play win rate'},
                    {'stat': 'Power Score', 'value': safe_round(sum(career_power_scores[key])/len(career_power_scores[key])) if career_power_scores.get(key) else None, 'rank': career_ps_ranks.get(key), 'explainer': 'Career average power score'},
                    {'stat': 'Weeks at #1', 'value': career_weeks_at_1.get(key, 0), 'rank': weeks_at_1_ranks.get(key), 'explainer': 'Weeks ranked #1 in power score'},
                    {'stat': 'Net Earnings', 'value': safe_round(career_earnings.get(key, 0), 2), 'rank': earnings_ranks.get(key), 'explainer': 'Total career net earnings', 'isEarnings': True},
                ],
                'playoffs': [
                    {'stat': 'Playoff Appearances', 'value': len(s['playoff_apps']), 'rank': playoff_app_ranks.get(key), 'explainer': 'Number of playoff appearances'},
                    {'stat': 'Playoff Wins', 'value': s['playoff_wins'], 'rank': playoff_win_ranks.get(key), 'explainer': 'Total playoff wins'},
                    {'stat': 'Final Fours', 'value': len(final_fours.get(key, set())), 'rank': None, 'explainer': 'Semifinal appearances'},
                    {'stat': 'Finals', 'value': len(finals.get(key, set())), 'rank': None, 'explainer': 'Championship game appearances'},
                    {'stat': 'Championships', 'value': len(championships.get(key, set())), 'rank': None, 'explainer': 'League championships won'},
                ],
            },
            'charts': {
                'years': chart_years,
                'wins': {'values': wins_chart, 'label': 'Wins'},
                'pointShare': {'values': pt_share_chart, 'label': 'Point Share'},
                'prestige': {'values': prestige_chart, 'label': 'Prestige'},
                'winnings': {'values': winnings_chart, 'label': 'Net Earnings'},
            },
            'seasons': seasons_list,
            'headToHead': owner_h2h,
        }

        owners_out[key] = owner_out

    return owners_out

def main(xlsx_path, profiles_json_path, output_profiles_path, output_h2h_path):
    print("Loading data...")
    matchups, season_stats, all_time_lucky, next_game = load_xlsx(xlsx_path)

    with open(profiles_json_path) as f:
        existing_json = json.load(f)

    print(f"Processing {len(matchups)} matchup rows...")

    career_stats, _, _ = compute_career_stats(matchups)
    finals, final_fours, championships = compute_playoff_structure(matchups)
    _, h2h_logs = compute_h2h(matchups)

    career_earnings = defaultdict(float)
    ss_valid = season_stats[season_stats['Year'].between(2014, 2030)].copy()
    for _, row in ss_valid.iterrows():
        k = get_key(str(row['Owner']))
        if k and pd.notna(row.get('Net Earnings')):
            career_earnings[k] += float(row['Net Earnings'])

    career_power_scores = defaultdict(list)
    for _, row in ss_valid.iterrows():
        k = get_key(str(row['Owner']))
        if k:
            ps = row.get('Regular Season Power Score')
            if pd.notna(ps):
                career_power_scores[k].append(float(ps))

    print("Building profiles data...")
    owners_out = build_profiles_data(matchups, season_stats, all_time_lucky, existing_json, next_game)

    print("Building career records...")
    career_records = build_career_records(
        career_stats, finals, final_fours, championships,
        career_earnings, career_power_scores, {}, existing_json
    )

    print("Building boom/bust data...")
    boom_bust = build_boom_bust(career_stats, existing_json)

    print("Building team names...")
    team_names = build_team_names(matchups, season_stats, existing_json)

    print("Building H2H data...")
    h2h_out = build_h2h_data(matchups, h2h_logs)

    # Assemble final profiles-data.json
    profiles_out = {
        'owners': owners_out,
        'pageUpdates': existing_json.get('pageUpdates', {}),
        'intercontinental': existing_json.get('intercontinental', {}),
        # NEW SECTIONS
        'careerRecords': career_records,
        'boomBust': boom_bust,
        'teamNames': team_names,
        # Prestige is 100% editorial — NEVER overwrite, always preserve
        'prestige': existing_json.get('prestige', []),
    }

    # Update page dates
    today = date.today().isoformat()
    profiles_out['pageUpdates']['profiles'] = today
    profiles_out['pageUpdates']['head-to-head'] = today
    profiles_out['pageUpdates']['career-records'] = today
    profiles_out['pageUpdates']['boom-start-bust'] = today
    profiles_out['pageUpdates']['intercontinental'] = today
    profiles_out['pageUpdates']['prestige-rankings'] = today
    profiles_out['pageUpdates']['single-game-records'] = today

    print(f"Writing {output_profiles_path}...")
    with open(output_profiles_path, 'w') as f:
        json.dump(profiles_out, f, indent=2, default=str)

    print(f"Writing {output_h2h_path}...")
    with open(output_h2h_path, 'w') as f:
        json.dump(h2h_out, f, indent=2)

    print("Done.")
    print(f"  Owners processed: {len(owners_out)}")
    print(f"  Career records entries: {len(career_records)}")
    print(f"  Boom/bust active: {len(boom_bust['active'])}")
    print(f"  Team names total: {len(team_names)}")
    print(f"  H2H pairs: {len(h2h_out)}")

if __name__ == '__main__':
    xlsx = sys.argv[1] if len(sys.argv) > 1 else '/mnt/user-data/uploads/All_Time_Slingshot_Matchups.xlsx'
    profiles_in = sys.argv[2] if len(sys.argv) > 2 else '/mnt/user-data/uploads/profiles-data.json'
    profiles_out = sys.argv[3] if len(sys.argv) > 3 else '/mnt/user-data/outputs/profiles-data.json'
    h2h_out = sys.argv[4] if len(sys.argv) > 4 else '/mnt/user-data/outputs/h2h-data.json'
    main(xlsx, profiles_in, profiles_out, h2h_out)
