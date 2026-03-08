from sqlalchemy import create_engine, inspect
engine=create_engine('postgresql://strikeiq:strikeiq123@localhost:5432/strikeiq')
insp=inspect(engine)
print(insp.get_table_names())
for t in ['ai_signal_logs', 'signal_outcomes', 'ai_features', 'ai_models', 'ai_predictions']:
    if t in insp.get_table_names():
        print(f'{t} exists: {[c.get("name") for c in insp.get_columns(t)]}')
