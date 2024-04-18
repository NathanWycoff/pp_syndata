#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#  match_fun.py Author "Nathan Wycoff <nathanbrwycoff@gmail.com>" Date 04.16.2024

import pandas as pd
import numpy as np
from splink.duckdb.linker import DuckDBLinker
from splink.duckdb.blocking_rule_library import block_on
import altair as alt
import splink.duckdb.comparison_library as cl
import splink.duckdb.comparison_template_library as ctl ## Hey they also have template functions

df1 = pd.read_csv('CT40_output3.csv')
df2 = pd.read_csv('../CT99.csv')

df1['unique_id'] = df1.index
df2['unique_id'] = df2.index

keepcols = ['unique_id','mailing_address_zipcode','first_name','last_name']
df1_sub = df1[keepcols]
df2_sub = df2[keepcols]

block_rule = block_on('mailing_address_zipcode')

#name_compare =  cl.levenshtein_at_thresholds("first_name", 2)
name_compare =  cl.exact_match("first_name")

from splink.duckdb.blocking_rule_library import block_on

settings = {
    "link_type": "link_and_dedupe",
    "comparisons": [
        cl.exact_match("last_name", term_frequency_adjustments=True),
        cl.exact_match("first_name", term_frequency_adjustments=True),
    ],
    "blocking_rules_to_generate_predictions": [
        block_on("mailing_address_zipcode")
    ],
    "retain_matching_columns": True,
    "retain_intermediate_calculation_columns": False,
}

linker = DuckDBLinker([df1_sub, df2_sub], settings)

### Estimate parameters
deterministic_rules = [
    "(l.mailing_address_zipcode = r.mailing_address_zipcode) AND (l.last_name=r.last_name)",
]

linker.estimate_probability_two_random_records_match(deterministic_rules, recall=0.7)
linker.estimate_u_using_random_sampling(max_pairs=1e6)

training_blocking_rule = block_on(["first_name"])
training_session_fname_sname = linker.estimate_parameters_using_expectation_maximisation(training_blocking_rule)

training_blocking_rule = block_on(["last_name"])
training_session_fname_sname = linker.estimate_parameters_using_expectation_maximisation(training_blocking_rule)

df_predictions = linker.predict(threshold_match_probability=0.1)
mdf = df_predictions.as_pandas_dataframe()

df1_key = df1[['simulant_id','unique_id']]
df1_key = df1_key.rename(dict([(v,v+'_l') for v in df1_key]), axis = 1)
mdf = mdf.merge(df1_key, on = 'unique_id_l')

df2_key = df2[['simulant_id','unique_id']]
df2_key = df2_key.rename(dict([(v,v+'_r') for v in df2_key]), axis = 1)
mdf = mdf.merge(df2_key, on = 'unique_id_r')

num_correctly_matched = np.sum(mdf['simulant_id_l']==mdf['simulant_id_r'])
common_records = len(set(df1['simulant_id']).intersection(df2['simulant_id']))

percent_matches = num_correctly_matched/common_records