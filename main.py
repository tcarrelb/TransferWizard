# -*- coding: utf-8 -*-
import hattrick_manager.readers as read
import hattrick_manager.visualizers as visu

df = read.collect_team_data()
df_top_scorers = visu.display_top_scorers()
