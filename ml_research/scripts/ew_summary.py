import pandas as pd, os

df = pd.read_csv('ml_research/data/processed/extreme_weather_dataset.csv')
hw = [c for c in df.columns if c.startswith('hw_')]
er = [c for c in df.columns if c.startswith('er_')]

print('=' * 60)
print('EXTREME WEATHER INTELLIGENCE DATASET — FINAL SUMMARY')
print('=' * 60)
print('Total rows            :', f'{len(df):,}')
print('Total columns         :', df.shape[1])
print('Missing values        :', df.isnull().sum().sum())
print('Heatwave features     :', len(hw))
print('Extreme rain features :', len(er))
print()

print('Heatwave Category Distribution:')
hc = df['heatwave_category'].value_counts()
for cat in ['Low', 'Medium', 'High', 'Extreme']:
    n = int(hc.get(cat, 0))
    print(f'  {cat:<8s}: {n:5,}  ({round(n/len(df)*100,1)}%)')
print()

print('Extreme Rainfall Category Distribution:')
rc = df['extreme_rainfall_category'].value_counts()
for cat in ['Low', 'Medium', 'High', 'Extreme']:
    n = int(rc.get(cat, 0))
    print(f'  {cat:<8s}: {n:5,}  ({round(n/len(df)*100,1)}%)')
print()

print('heatwave_severity_score  : min', round(df['heatwave_severity_score'].min(),4),
      '| max', round(df['heatwave_severity_score'].max(),4))
print('extreme_rainfall_score   : min', round(df['extreme_rainfall_score'].min(),4),
      '| max', round(df['extreme_rainfall_score'].max(),4))
print()

print('Output files:')
for fpath in ['ml_research/data/processed/extreme_weather_dataset.csv',
              'ml_research/reports/extreme_weather_intelligence_report.md']:
    size = os.path.getsize(fpath)
    print(f'  {fpath}  ({size:,} bytes)')
