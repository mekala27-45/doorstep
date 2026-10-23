select source, rule, year, flagged, rows
from read_parquet('{{ env_var('DOORSTEP_RESULTS_DIR', '../results') }}/data/quarantine.parquet')
