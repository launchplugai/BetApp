# S20 Beta Run Checklist

**Sprint:** S20 - Notifications + Protocol Observers  
**Beta Duration:** 48 hours  
**Start Date:** ___________  
**Beta Cohort:** ___________  
**Run Lead:** ___________  

---

## Day 0: Setup & Enable

### Pre-Flight Checks

- [ ] Database migration `005_add_notification_system` applied
- [ ] Environment variables configured:
  - [ ] `NOTIFICATIONS_ENABLED=false` (start disabled)
  - [ ] `NOTIFICATIONS_KILL_SWITCH=false`
  - [ ] `NOTIFICATIONS_DAILY_CAP=5`
  - [ ] `NOTIFICATIONS_COOLDOWN_MINUTES=120`
  - [ ] `NOTIFICATIONS_MAX_DAILY_PER_USER=5`
  - [ ] `INCENTIVE_ACTIVATION_WEIGHT=minimal`
  - [ ] `FEATURE_SHERLOCK_INCENTIVES=true`
- [ ] Beta user IDs list prepared and validated
- [ ] Rollback plan reviewed with on-call engineer
- [ ] Monitoring dashboards accessible
- [ ] Alert channels configured

### Enable Cohort

- [ ] Set `NOTIFICATIONS_BETA_USER_IDS` to beta cohort user IDs
- [ ] Verify cohort size: _____ users
- [ ] Confirm no production users in cohort (double-check)

### Start Observer

- [ ] Deploy with observer enabled: `NOTIFICATIONS_ENABLED=true`
- [ ] Verify health check: `/health/config` returns `notifications.status="active"`
- [ ] Confirm observer logs show: `[STARTUP] ProtocolObserver initialized`
- [ ] Verify no immediate errors in logs

### Validate Receipts

- [ ] Trigger test opportunity (or wait for natural signal)
- [ ] Verify receipt created: `notification_events` table has entry
- [ ] Confirm receipt includes:
  - [ ] `user_id`
  - [ ] `notification_type`
  - [ ] `trigger_signals` (JSON)
  - [ ] `constraint_checks` (JSON)
  - [ ] `created_at` timestamp
- [ ] Validate receipt data is complete and parseable

### Enable Notifications

- [ ] Set `NOTIFICATIONS_ENABLED=true` (if not already)
- [ ] Verify health endpoint shows: `"enabled": true`
- [ ] Send test notification to beta cohort
- [ ] Confirm delivery via webhook or in-app

---

## Day 1 Checkpoint (24 hours)

### Spam Rate Check

- [ ] Query notification volume: `SELECT COUNT(*) FROM notification_events WHERE created_at > NOW() - INTERVAL '24 hours'`
- [ ] Count per user: `SELECT user_id, COUNT(*) FROM notification_events WHERE created_at > NOW() - INTERVAL '24 hours' GROUP BY user_id`
- [ ] **VERIFY:** No user exceeded `NOTIFICATIONS_DAILY_CAP=5`
- [ ] **VERIFY:** Daily cap enforcement working (check `notification_logs` for cap hits)

**Day 1 Volume:**
- Total sent: _____
- Max per user: _____
- Daily cap hits: _____

### Error Rate Check

- [ ] Check error logs: `grep "ERROR" /var/log/dna-matrix/app.log | grep -i notification | wc -l`
- [ ] Check failed deliveries: `SELECT COUNT(*) FROM notification_events WHERE status='failed'`
- [ ] Calculate error rate: _____%
- [ ] **VERIFY:** Error rate < 1%

**Day 1 Errors:**
- Total errors: _____
- Failed deliveries: _____
- Error rate: _____%
- **Status:** ☐ PASS / ☐ FAIL

### Constraint Violations

- [ ] Query constraint violations: `SELECT * FROM notification_logs WHERE violation_type IS NOT NULL`
- [ ] Check logs for "CONSTRAINT_VIOLATION"
- [ ] **VERIFY:** Zero constraint violations

**Day 1 Constraint Check:**
- Violations found: _____
- **Status:** ☐ PASS (0 violations) / ☐ FAIL

### Observer Health

- [ ] Check observer uptime in logs
- [ ] Verify no restarts or crashes
- [ ] Confirm protocol watching is continuous

**Day 1 Observer:**
- Uptime: _____%
- Restarts: _____
- **Status:** ☐ PASS / ☐ FAIL

---

## Day 2 Checkpoint (48 hours)

### Engagement Metrics

- [ ] Query notification opens: `SELECT COUNT(*) FROM notification_events WHERE read_at IS NOT NULL`
- [ ] Query notification clicks: (from analytics/webhook data)
- [ ] Calculate open rate: _____%
- [ ] Calculate click-through rate: _____%

**Day 2 Engagement:**
- Total sent: _____
- Total opened: _____
- Total clicked: _____
- Open rate: _____%
- Click-through rate: _____%

### Drift Analysis

- [ ] Query incentive adjustments: `SELECT * FROM notification_logs WHERE adjustment_type IS NOT NULL`
- [ ] Analyze distribution of adjustments:
  - Positive adjustments: _____
  - Negative adjustments: _____
  - Neutral: _____
- [ ] Check for systematic bias (are adjustments consistently positive/negative?)

**Day 2 Drift:**
- Mean adjustment: _____
- Distribution: _____
- **Status:** ☐ Nominal / ☐ Investigate

### Final Verification

- [ ] All Day 1 checks still passing
- [ ] No new error patterns emerged
- [ ] No user complaints received
- [ ] System performance stable

---

## Rollback Triggers

**STOP IMMEDIATELY if any of the following occur:**

| Trigger | Detection | Action |
|---------|-----------|--------|
| **Any constraint violation** | Check `notification_logs.violation_type` | Rollback |
| **Error spike >5%** | Monitor error rate | Rollback |
| **Notification spam** | Any user > daily cap + 1 | Rollback |
| **Receipt gaps** | Missing receipts for sent notifications | Rollback |
| **Kill switch activated** | Manual intervention | Rollback |
| **User complaints** | Support tickets or feedback | Evaluate & Rollback |
| **Performance degradation** | Response time >2x baseline | Rollback |

### Rollback Action

If rollback triggered:

1. **Immediate (30 seconds):**
   ```bash
   export NOTIFICATIONS_ENABLED=false
   export INCENTIVE_ACTIVATION_WEIGHT=off
   ```

2. **Verify stop:**
   ```bash
   curl /health/config | jq '.notifications.status, .sherlock_incentives.status'
   # Expected: "disabled", "off"
   ```

3. **Notify team:**
   - Post in #incidents channel
   - Page on-call engineer
   - Update status page

4. **Preserve data:**
   - Export `notification_events` table
   - Export `notification_logs` table
   - Save recent application logs

5. **Post-mortem:**
   - Schedule within 24 hours
   - Document root cause
   - Create fix tickets

---

## Sign-Off

### Day 0 Sign-Off

| Role | Name | Signature | Time |
|------|------|-----------|------|
| Run Lead | | | |
| On-Call Engineer | | | |
| Product Owner | | | |

### Day 1 Sign-Off

| Role | Name | Signature | Time |
|------|------|-----------|------|
| Run Lead | | | |
| On-Call Engineer | | | |

### Day 2 Sign-Off

| Role | Name | Signature | Time |
|------|------|-----------|------|
| Run Lead | | | |
| On-Call Engineer | | | |
| Product Owner | | | |

---

## Next Steps

### If Beta Successful

- [ ] Update `NOTIFICATIONS_BETA_USER_IDS` to expand cohort
- [ ] Or set to `""` for all users (GA)
- [ ] Consider increasing `INCENTIVE_ACTIVATION_WEIGHT` to `low`
- [ ] Schedule 1-week review

### If Beta Failed

- [ ] Execute rollback (if not already)
- [ ] Preserve all data
- [ ] Schedule post-mortem within 24 hours
- [ ] Update S20 sprint with findings
- [ ] Create fix tickets
- [ ] Plan next beta attempt

---

**Document Version:** 1.0  
**Last Updated:** 2026-02-14  
**Owner:** Engineering Team
