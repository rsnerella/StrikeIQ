# 🚨 CORRECTED STRICT EXECUTION GUIDE

## 📊 CURRENT STATE (VERIFIED)

**Status**: ❌ NOT READY
- formula_id: NULL (MUST be INTEGER)
- Real data test: Cannot run until schema fixed

## 🔧 EXECUTION STEPS (CORRECTED)

### ✅ STEP 1: RUN SCHEMA FIX

**File**: `migrations/final_strict_fix.sql`
**Location**: Supabase SQL Editor
**Action**: Copy, paste, click "Run"
**Expected**: No errors

### ✅ STEP 2: VERIFY TYPE (ONLY THIS MATTERS)

**File**: `migrations/verify_type.sql`
**Location**: Supabase SQL Editor
**SQL**:
```sql
SELECT data_type
FROM information_schema.columns
WHERE table_name='ai_signal_logs'
AND column_name='formula_id';
```

**Expected Result**: `integer`
**Note**: NULL value is allowed

### ✅ STEP 3: REAL DATA TEST (MANDATORY)

**File**: `migrations/real_data_test_strict.sql`
**Location**: Supabase SQL Editor
**SQL**:
```sql
DELETE FROM outcome_log;
DELETE FROM ai_signal_logs;

INSERT INTO ai_signal_logs (id, formula_id)
VALUES (1, 100);

INSERT INTO outcome_log (prediction_id)
VALUES (1);

SELECT *
FROM ai_signal_logs p
JOIN outcome_log o
ON p.id = o.prediction_id;
```

## ❌ FAILURE CONDITIONS (STOP IF ANY)

- INSERT fails with any error
- FK constraint error
- JOIN fails with type mismatch
- JOIN returns 0 rows

## ✅ SUCCESS CONDITIONS (ALL REQUIRED)

- formula_id TYPE = INTEGER
- FK constraint exists
- INSERT into both tables works
- JOIN returns exactly 1 row
- NO casting used in JOIN

## 🚨 FINAL RULE

**System is ONLY correct if**:
```sql
p.id = o.prediction_id
```
**works directly WITHOUT hacks, casting, or workarounds.**

## 📋 EXECUTION CHECKLIST

### Before Execution:
- [ ] Current state verified (❌ formula_id is NULL)
- [ ] Scripts ready (✅ All prepared)

### After Step 1:
- [ ] Schema fix executed without errors
- [ ] Extension created
- [ ] Column type changed
- [ ] FK constraint added
- [ ] Indexes created

### After Step 2:
- [ ] Type verification returns `integer`
- [ ] NULL value is acceptable

### After Step 3:
- [ ] DELETE commands execute
- [ ] INSERT commands execute
- [ ] JOIN returns exactly 1 row
- [ ] No casting used in JOIN

### Final Verification:
- [ ] Python verification passes
- [ ] All success conditions met
- [ ] No failure conditions triggered

## ⛔ CRITICAL WARNING

**DO NOT PROCEED TO UUID MIGRATION UNTIL THIS PASSES**

## 📁 Files Ready

1. **Schema Fix**: `migrations/final_strict_fix.sql`
2. **Type Verify**: `migrations/verify_type.sql`
3. **Data Test**: `migrations/real_data_test_strict.sql`
4. **Python Verify**: `strict_verification.py`

## 🏁 Status: READY FOR CORRECTED EXECUTION

All scripts prepared with corrected requirements. Execute in strict order and verify each step. System is only considered production-ready when `p.id = o.prediction_id` works directly without any casting or hacks.
