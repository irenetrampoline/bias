"""
Code by Maggie Makar
https://github.com/mlhc17mit/pset1materials/blob/master/mort_icu_cleanup.py

"""

# for those interested, the following notebooks are useful to understan 
# how the data are organized 

# Import libraries
import numpy as np
import pandas as pd
import psycopg2
from scipy.stats import ks_2samp
import os 
import random 
import py.test
# from bs4 import BeautifulSoup 

DIAG_BOOL = True

mimicdir = os.path.expanduser("~/Documents/mimic-data")

random.seed(22891)

# create a database connection
sqluser = 'postgres'
dbname = 'mimic'
schema_name = 'mimiciii'

# Connect to local postgres version of mimic
con = psycopg2.connect(dbname=dbname, user=sqluser)
cur = con.cursor()
cur.execute('SET search_path to ' + schema_name)

#========helper function for imputing missing values 


def replace(group):
  """
  takes in a pandas group, and replaces the 
  null value with the mean of the none null
  values of the same group 
  """
  mask = group.isnull()
  group[mask] = group[~mask].mean()
  return group


#========get the icu details 

# this query extracts the following:
#   Unique ids for the admission, patient and icu stay 
#   Patient gender 
#   admission & discharge times 
#   length of stay 
#   age 
#   ethnicity 
#   admission type 
#   in hospital death?
#   in icu death?
#   one year from admission death?
#   first hospital stay 
#   icu intime, icu outime 
#   los in icu 
#   first icu stay?

denquery = \
"""
-- This query extracts useful demographic/administrative information for patient ICU stays
--DROP MATERIALIZED VIEW IF EXISTS icustay_detail CASCADE;
--CREATE MATERIALIZED VIEW icustay_detail as
--ie is the icustays table 
--adm is the admissions table 
SELECT ie.subject_id, ie.hadm_id, ie.icustay_id
, pat.gender
, adm.admittime, adm.dischtime, adm.diagnosis
, ROUND( (CAST(adm.dischtime AS DATE) - CAST(adm.admittime AS DATE)) , 4) AS los_hospital
, ROUND( (CAST(adm.admittime AS DATE) - CAST(pat.dob AS DATE))  / 365, 4) AS age
, adm.ethnicity, adm.ADMISSION_TYPE
--, adm.hospital_expire_flag
, CASE when adm.deathtime between adm.admittime and adm.dischtime THEN 1 ELSE 0 END AS mort_hosp
, CASE when adm.deathtime between ie.intime and ie.outtime THEN 1 ELSE 0 END AS mort_icu
, CASE when adm.deathtime between adm.admittime and adm.admittime + interval '365' day  THEN 1 ELSE 0 END AS mort_oneyr
, DENSE_RANK() OVER (PARTITION BY adm.subject_id ORDER BY adm.admittime) AS hospstay_seq
, CASE
    WHEN DENSE_RANK() OVER (PARTITION BY adm.subject_id ORDER BY adm.admittime) = 1 THEN 1
    ELSE 0 END AS first_hosp_stay
-- icu level factors
, ie.intime, ie.outtime
, ie.FIRST_CAREUNIT
, ROUND( (CAST(ie.outtime AS DATE) - CAST(ie.intime AS DATE)) , 4) AS los_icu
, DENSE_RANK() OVER (PARTITION BY ie.hadm_id ORDER BY ie.intime) AS icustay_seq
-- first ICU stay *for the current hospitalization*
, CASE
    WHEN DENSE_RANK() OVER (PARTITION BY ie.hadm_id ORDER BY ie.intime) = 1 THEN 1
    ELSE 0 END AS first_icu_stay
, diag.icd9_code
, diag.seq_num as seq_icd9
FROM icustays ie
INNER JOIN admissions adm
    ON ie.hadm_id = adm.hadm_id
INNER JOIN patients pat
    ON ie.subject_id = pat.subject_id
 LEFT OUTER JOIN diagnoses_icd diag
   ON ie.subject_id = diag.subject_id and ie.hadm_id = diag.hadm_id
WHERE adm.has_chartevents_data = 1
ORDER BY ie.subject_id, adm.admittime, ie.intime;
"""

den = pd.read_sql_query(denquery,con)
print den.columns
print '1'

#----drop patients with less than 48 hour 
den['los_icu_hr'] = (den.outtime - den.intime).astype('timedelta64[h]')
den = den[(den.los_icu_hr >= 48)]
den = den[(den.age<300)]
den.drop('los_icu_hr', 1, inplace = True)
print 'len of den: %d' % len(den)
# den.isnull().sum()

#----clean up

# micu --> medical 
# csru --> cardiac surgery recovery unit 
# sicu --> surgical icu 
# tsicu --> Trauma Surgical Intensive Care Unit
# NICU --> Neonatal 

den['adult_icu'] = np.where(den['first_careunit'].isin(['PICU', 'NICU']), 0, 1)
den['gender'] = np.where(den['gender']=="M", 1, 0)

# h_los_dummies = pd.qcut(den['los_hospital'], [0, .25, .5, .75, 1.],labels=False) +1
# den = pd.concat([den, pd.get_dummies(h_los_dummies, prefix='admlos')], 1)

# icu_los_dummies = pd.qcut(den['los_icu'], [0, .25, .5, .75, 1.],labels=False) +1
# den = pd.concat([den, pd.get_dummies(icu_los_dummies, prefix='iculos')], 1)

# age_dummies = pd.cut(den['age'], [-1,5,10,15,20, 25, 40,60, 80, 200], 
#   labels = ['l5','5_10', '10_15', '15_20', '20_25', '25_40', '40_60',  '60_80', '80p'])
# den = pd.concat([den, pd.get_dummies(age_dummies, prefix='age')], 1)

# get ethnicity group, assuming a certain order arbitrarily
def eth(s):
  if s.contains('^white'):
    return 'white'
  elif s.contains('^black'):
    return 'black'
  elif s.contains('^hisp') or s.contains('^latin'):
    return 'hispanic'
  elif s.contains('^asian'):
    return 'asian'
  else:
    return 'other'

# no need to yell 
den.ethnicity = den.ethnicity.str.lower()
den.ethnicity.loc[(den.ethnicity.str.contains('^white'))] = 'white'
den.ethnicity.loc[(den.ethnicity.str.contains('^black'))] = 'black'
den.ethnicity.loc[(den.ethnicity.str.contains('^hisp')) | (den.ethnicity.str.contains('^latin'))] = 'hispanic'
den.ethnicity.loc[(den.ethnicity.str.contains('^asia'))] = 'asian'
den.ethnicity.loc[~(den.ethnicity.str.contains('|'.join(['white', 'black', 'hispanic', 'asian'])))] = 'other'

den = pd.concat([den, pd.get_dummies(den['ethnicity'], prefix='eth')], 1)
den = pd.concat([den, pd.get_dummies(den['admission_type'], prefix='admType')], 1)

den.drop(['diagnosis', 'hospstay_seq', 'los_icu','icustay_seq', 'admittime', 'dischtime','los_hospital', 'intime', 'outtime', 'ethnicity', 'admission_type', 'first_careunit'], 1, inplace =True) 


#======missing values (following joydeep ghosh's paper)

print den.columns
print '2'
mort_ds = den
# create means by age group and gender 
mort_ds['age_group'] = pd.cut(mort_ds['age'], [-1,5,10,15,20, 25, 40,60, 80, 200], 
   labels = ['l5','5_10', '10_15', '15_20', '20_25', '25_40', '40_60',  '60_80', '80p'])

mort_ds['had_null'] = mort_ds.isnull().any(axis=1)


# mort_ds = mort_ds.groupby(['age_group', 'gender'])
# mort_ds = mort_ds.transform(replace)
# IC: program got stuck at this line. commenting out for now.
# mort_ds.drop('age_group', inplace =True)

# one missing variable 
adult_icu = mort_ds[(mort_ds.adult_icu==1)].dropna()
print adult_icu.columns
print '3'

print 'len adult_icu: %d' % len(adult_icu)
# create training and testing labels 
# msk = np.random.rand(len(adult_icu)) < 0.7
# adult_icu['train'] = np.where(msk, 1, 0) 
adult_icu.to_csv(os.path.join(mimicdir, 'adult_icu_nullinfo_diag_big.gz'), compression='gzip',  index = False)


"""
# notes - don't need right now
adult_notes = notes48.merge(adult_icu[['train', 'subject_id', 'hadm_id', 'icustay_id', 'mort_hosp', 'mort_icu', 'mort_oneyr']], how = 'right', on = ['subject_id', 'hadm_id', 'icustay_id'])
adult_notes.to_csv(os.path.join(mimicdir, 'adult_notes.gz'), compression='gzip',  index = False)

# don't need NICU 
# nicu 
nicu_missing = mort_ds[(mort_ds.adult_icu==0)].isnull().sum()/mort_ds[(mort_ds.adult_icu==0)].shape[0]
removes = nicu_missing[(nicu_missing == 1) ]._index 
n_icu = mort_ds[(mort_ds.adult_icu==0)].drop(removes, 1).dropna()

# create training and testing 
msk = np.random.rand(len(n_icu)) < 0.7
n_icu['train'] = np.where(msk, 1, 0) 
fpath = os.path.join(mimicdir, 'n_icu.gz')
n_icu.to_csv(fpath, compression='gzip',  index = False)
print 'Created data in %s' % fpath
"""