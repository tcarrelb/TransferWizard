import hattrick_manager as hatman

import os
import pandas as pd


def display_top_scorers():
    def keep_latest(df):
        df2 = df.sort_values(by=['goals_for_team', 'weeks_in_club'], ascending=[False, False])
        df2 = df2.iloc[0].to_frame().transpose()  # keep only the first column

        return df2

    out_dir = os.path.join(hatman.__path__[0], 'output')
    team_data_csv = 'complete_team_data.csv'
    top_scorers_csv = 'top_scorers_data.csv'
    team_data_path = os.path.join(out_dir, team_data_csv)
    top_scorers_path = os.path.join(out_dir, top_scorers_csv)
    df_team = pd.read_csv(team_data_path, index_col=False)
    df_score = pd.read_csv(top_scorers_path, index_col=False)

    # Combining the two dataframes:
    columns = list(df_score.columns.to_list())
    columns.remove('goals_per_week')
    df_team_red = df_team[columns]
    df_concat = pd.concat([df_team_red, df_score], ignore_index=True)

    # Creating the new top scorer dataframe:
    df_top_scorers = df_concat.groupby('player_id', as_index=False).apply(keep_latest)
    df_top_scorers.sort_values(by=['goals_for_team', 'weeks_in_club'], ascending=[False, False], inplace=True)
    df_top_scorers.reset_index(drop=True, inplace=True)
    df_top_scorers['goals_per_week'] = df_top_scorers['goals_for_team'] / df_top_scorers['weeks_in_club']
    df_top_scorers['goals_per_week'] = df_top_scorers['goals_per_week'].astype(float)
    df_top_scorers['goals_per_week'] = df_top_scorers['goals_per_week'].round(decimals=5)
    df_top_scorers.to_csv(top_scorers_path, index=False)

    return df_top_scorers


def display_top_hattricks():
    return
