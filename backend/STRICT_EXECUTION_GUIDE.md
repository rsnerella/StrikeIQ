# 🚨 STRICT EXECUTION GUIDE

## 📊 Current Status (VERIFIED)

**Strict Verification Result**: ❌ FAILED
- ❌ formula_id is NULL (MUST be INTEGER)
- ❌ fk_prediction constraint missing
- ❌ Indexes missing
- ❌ Real data test not possible until schema fixed

## 🔧 STEP-BY-STEP EXECUTION

### STEP 1: Execute Schema Fix (SUPABASE)

**Location**: Supabase SQL Editor
**File**: `migrations/strict_supabase_fix.sql`

**Copy and paste EXACTLY**:
```sql
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

ALTER TABLE ai_signal_logs
ALTER COLUMN formula_id TYPE INTEGER
USING NULLIF(formula_id, '')::int;

ALTER TABLE outcome_log
ADD CONSTRAINT fk_prediction
FOREIGN KEY (prediction_id)
REFERENCES ai_signal_logs(id);

ALTER TABLE paper_trade_log
ADD COLUMN IF NOT EXISTS prediction_id_uuid UUID;

CREATE INDEX IF NOT EXISTS idx_ai_signal_formula 
ON ai_signal_logs(formula_id);

CREATE INDEX IF NOT EXISTS idx_outcome_prediction 
ON outcome_log(prediction_id);

ANALYZE ai_signal_logs;
ANALYZE outcome_log;
ANALYZE paper_trade_log;
```

**Execute**: Click "Run" in Supabase SQL Editor
**Expected**: No errors, command completes successfully

### STEP 2: Verify Schema (MANDATORY)

**Location**: Supabase SQL Editor
**File**: `migrations/verify_schema.sql`

**Copy and paste EXACTLY**:
```sql
-- Check formula_id type
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_name='ai_signal_logs'
AND column_name='formula_id';

-- Check foreign key constraint
SELECT constraint_name
FROM information_schema.table_constraints
WHERE table_name='outcome_log';

-- Check indexes
SELECT indexname
FROM pg_indexes
WHERE tablename IN ('ai_signal_logs','outcome_log');
```

**Expected Results**:
- formula_id: `integer`
- constraint_name: `fk_prediction` (among others)
- indexname: `idx_ai_signal_formula`, `idx_outcome_prediction`

### STEP 3: Real Data Test (CRITICAL)

**Location**: Supabase SQL Editor
**File**: `migrations/real_data_test.sql`

**Copy and paste EXACTLY**:
```sql
-- clean test
DELETE FROM outcome_log;
DELETE FROM ai_signal_logs;

-- insert test data
INSERT INTO ai_signal_logs (id, formula_id) VALUES (1, 100);
INSERT INTO outcome_log (prediction_id) VALUES (1);

-- JOIN test
SELECT *
FROM ai_signal_logs p
JOIN outcome_log o
ON p.id = o.prediction_id;
```

**Expected Results**:
- DELETE commands execute (no errors)
- INSERT commands execute (no errors)
- JOIN returns exactly 1 row with both table data

### STEP 4: Python Verification (FINAL)

**Run in terminal**:
```bash
cd d:\StrikeIQ\backend
python strict_verification.py
```

**Expected Output**:
```
🎉 STRICT VERIFICATION PASSED
✅ formula_id is INTEGER
✅ fk_prediction constraint exists
✅ All indexes created
✅ INSERT into both tables works
✅ JOIN returns 1 row WITHOUT casting
✅ System is PRODUCTION READY

🚀 SUCCESS: p.id = o.prediction_id works WITHOUT hacks
```

## ❌ FAILURE CONDITIONS

**STOP IMMEDIATELY if ANY of these occur**:
- FK constraint error during execution
- INSERT fails with any error
- JOIN fails with type mismatch
- Empty JOIN result after valid insert
- Python verification returns FAILED

## ✅ SUCCESS CONDITIONS

**ALL must pass**:
- formula_id is INTEGER type
- fk_prediction constraint exists
- Both indexes created
- INSERT into both tables works
- JOIN returns exactly 1 row
- JOIN uses NO casting: `p.id = o.prediction_id`

## 🚨 CRITICAL NOTES

- **DO NOT** assume anything - verify each step
- **DO NOT** continue to UUID migration until this passes
- **DO NOT** accept "0 rows" as success
- **DO NOT** skip any verification step

## 📁 Files Created

1. **Schema Fix**: `migrations/strict_supabase_fix.sql`
2. **Schema Verify**: `migrations/verify_schema.sql`
3. **Data Test**: `migrations/real_data_test.sql`
4. **Python Verify**: `strict_verification.py`

## 🏁 Status: READY FOR STRICT EXECUTION

All scripts are prepared exactly as specified. Execute in order and verify each step. System is ONLY considered correct when `p.id = o.prediction_id` works WITHOUT any casting or hacks.
