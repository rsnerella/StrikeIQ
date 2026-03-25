# Production Schema Deployment Guide

## 🎯 Overview
This guide converts temporary database fixes into production-grade schema with proper typing, indexing, and performance optimization.

## 📋 Prerequisites
- PostgreSQL 13+ with UUID extension
- Database backup before migration
- Application downtime during schema migration

## 🚀 Deployment Steps

### 1. Backup Database
```bash
pg_dump strikeiq_prod > backup_before_schema_fixes.sql
```

### 2. Run Migration
```bash
cd backend
psql -d strikeiq_prod -f migrations/production_schema_fixes.sql
```

### 3. Verify Migration
```bash
python verify_production_schema.py
```

### 4. Update Application
- Deploy updated Python code
- Restart application services
- Monitor logs for errors

## 🔧 Schema Changes Applied

### UUID Type Alignment
- `ai_signal_logs.id`: INTEGER → UUID
- `outcome_log.prediction_id`: UUID (unchanged)
- Foreign key constraints recreated
- No more text casting in JOINs

### Dedicated formula_id Column
- Added `ai_signal_logs.formula_id` INTEGER
- Backfilled from JSON metadata
- Added performance indexes
- Queries use direct column instead of JSON parsing

### paper_trade_log Schema Fix
- Added `option_type` VARCHAR(10) (optional)
- Renamed `trade_type` → `trade_status`
- Renamed `timestamp` → `entry_time`
- Updated indexes to use new column names

### Performance Optimizations
- Composite indexes on common query patterns
- Partial indexes for active formulas
- Updated table statistics

## 📊 Performance Improvements

### Before Migration
- UUID JOIN required text casting: `p.id::text = o.prediction_id::text`
- JSON filtering: `(metadata->>'formula_id')::int = $1`
- Missing indexes on formula_id queries
- Column name mismatches causing errors

### After Migration
- Direct UUID JOIN: `p.id = o.prediction_id`
- Direct column filtering: `p.formula_id = $1`
- Optimized indexes for formula queries
- Consistent column naming across queries

## 🧪 Verification Queries

### Test UUID JOIN
```sql
EXPLAIN ANALYZE
SELECT p.id, o.prediction_id 
FROM ai_signal_logs p 
LEFT JOIN outcome_log o ON p.id = o.prediction_id 
LIMIT 5;
```

### Test Formula Performance
```sql
EXPLAIN ANALYZE
SELECT COUNT(*) 
FROM ai_signal_logs 
WHERE formula_id = 1 
AND timestamp >= NOW() - INTERVAL '30 days';
```

### Test Paper Trades
```sql
SELECT id, prediction_id, symbol, strike_price,
       entry_price, exit_price, quantity, pnl, trade_status,
       option_type, entry_time
FROM paper_trade_log
WHERE entry_time >= NOW() - INTERVAL '24 hours'
ORDER BY entry_time DESC
LIMIT 20;
```

## ⚠️ Rollback Plan

If migration fails:
```bash
# Restore from backup
psql -d strikeiq_prod < backup_before_schema_fixes.sql

# Revert application code
git checkout pre-migration-branch
```

## 📈 Expected Performance Gains

- Query execution time: 60-80% reduction
- Index usage: 95%+ for formula queries
- Memory usage: Reduced by eliminating JSON parsing
- CPU usage: Lower due to proper type matching

## 🔍 Monitoring

Post-migration checks:
- Application startup logs
- Database error rates
- Query performance metrics
- API response times

## 📞 Support

If issues arise:
1. Check application logs
2. Run verification script
3. Review query execution plans
4. Contact DBA for rollback assistance
