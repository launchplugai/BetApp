# S20 Deployment Checklist

**Sprint:** S20 - Notifications + Protocol Observers  
**Deploy Date:** 2026-02-14  
**Feature Flag Status:** NOTIFICATIONS_ENABLED=false (default)  

---

## Pre-Deploy Checklist

### Code Review
- [x] All S20 services reviewed
- [x] Feature flags implemented correctly
- [x] Kill switch functional
- [x] No hardcoded secrets
- [x] Database migrations prepared

### Testing
- [x] Unit tests passing (96%)
- [x] Integration tests passing
- [x] Guardrails tested (cooldown, daily caps)
- [x] Feature flag behavior verified
- [x] Kill switch tested

### Configuration
- [x] Environment variables documented
- [x] Default values safe for production
- [x] Feature flags default to OFF

---

## Migration Steps

### 1. Database Migration
```bash
# Run migration for notification system
python -m migrations.005_add_notification_system
```

**Migration includes:**
- `notification_events` table
- `notification_logs` table
- `eligible_opportunities` table
- Indexes for performance

### 2. Environment Variables

Add to production environment:

```bash
# Feature flags (default disabled)
NOTIFICATIONS_ENABLED=false
NOTIFICATIONS_KILL_SWITCH=false

# Rate limiting (defaults are safe)
NOTIFICATIONS_MAX_DAILY_PER_USER=10
NOTIFICATIONS_COOLDOWN_MINUTES=60

# Webhook configuration (optional)
NOTIFICATION_WEBHOOK_URL=""
NOTIFICATION_WEBHOOK_SECRET=""
```

### 3. Deploy Application
```bash
# Standard deployment
./scripts/deploy.sh

# Or via Railway
git push railway main
```

### 4. Verification
```bash
# Check deployment health
curl https://api.dna-matrix.com/health

# Verify feature flags
curl https://api.dna-matrix.com/health/config
```

Expected response:
```json
{
  "notifications": {
    "enabled": false,
    "kill_switch_active": false,
    "status": "disabled"
  }
}
```

---

## Feature Flag Enablement Process

### Phase 1: Observer Only (No Notifications)
**Status:** Observer runs, no notifications sent

```bash
NOTIFICATIONS_ENABLED=false
```

**Verification:**
- Observer logs show opportunity detection
- No notifications queued
- No delivery attempts

### Phase 2: Internal Testing
**Status:** Enable for specific test users

```python
# In admin panel or database
user.notification_preferences.enabled = True
```

**Checklist:**
- [ ] Test users receive notifications
- [ ] Guardrails enforce daily caps
- [ ] Cooldowns prevent duplicates
- [ ] Quiet hours respected
- [ ] Templates render correctly

### Phase 3: Beta Users
**Status:** Enable for beta cohort

```bash
# Enable for 10% of users
NOTIFICATIONS_ENABLED=true
NOTIFICATIONS_BETA_COHORT=10
```

**Monitoring:**
- Watch error rates
- Monitor notification volume
- Track user engagement
- Check for spam complaints

### Phase 4: General Availability
**Status:** Full rollout

```bash
NOTIFICATIONS_ENABLED=true
NOTIFICATIONS_BETA_COHORT=100
```

**Success Criteria:**
- False positive rate < 5%
- User engagement > 30%
- Zero spam complaints
- 99.9% observer uptime

---

## Rollback Plan

### Emergency Rollback (Kill Switch)

**Immediate stop of all notifications:**
```bash
# Activate kill switch
NOTIFICATIONS_KILL_SWITCH=true
```

**Effect:** All notifications blocked immediately, no restart required.

### Full Rollback

**If kill switch insufficient:**
```bash
# 1. Disable feature flag
NOTIFICATIONS_ENABLED=false

# 2. Restart application
./scripts/restart.sh

# 3. Clear queued notifications (optional)
python -c "from app.services.notification_delivery import get_notification_delivery; get_notification_delivery()._queue.queue.clear()"
```

### Database Rollback

**If migration needs rollback:**
```bash
# Revert migration
python -m migrations.rollback 005_add_notification_system
```

---

## Monitoring & Alerting

### Key Metrics

| Metric | Warning Threshold | Critical Threshold |
|--------|------------------|-------------------|
| Notification queue depth | > 100 | > 1000 |
| Failed deliveries / hour | > 5 | > 20 |
| Kill switch active | N/A (immediate alert) | N/A |
| Daily cap hits / hour | > 50 | > 200 |

### Logs to Watch

```bash
# Watch for errors
tail -f /var/log/dna-matrix/app.log | grep -E "(ERROR|notification|guardrail)"

# Monitor notification volume
tail -f /var/log/dna-matrix/app.log | grep "notification" | wc -l
```

### Health Check Endpoints

```bash
# Config health
curl /health/config

# Notification service health
curl /health/notifications
```

---

## Post-Deploy Verification

### Immediate (0-30 minutes)
- [ ] Application starts without errors
- [ ] Health checks pass
- [ ] Feature flags show correct state
- [ ] No errors in logs

### Short Term (1-4 hours)
- [ ] Observer is watching protocols
- [ ] No unexpected notification sends
- [ ] Queue depth is 0 or stable
- [ ] Database connections healthy

### Long Term (24-48 hours)
- [ ] Observer uptime > 99.9%
- [ ] No memory leaks
- [ ] Notification volume as expected
- [ ] User feedback positive

---

## Support Contacts

| Role | Contact | Escalation |
|------|---------|------------|
| On-call Engineer | @engineering-oncall | @engineering-lead |
| Product Owner | @product-s20 | @cto |
| Infrastructure | @devops | @sre-lead |

---

## Appendix

### Environment Variable Reference

| Variable | Default | Description |
|----------|---------|-------------|
| `NOTIFICATIONS_ENABLED` | `false` | Master feature flag |
| `NOTIFICATIONS_KILL_SWITCH` | `false` | Emergency stop |
| `NOTIFICATIONS_MAX_DAILY_PER_USER` | `10` | Daily cap per user |
| `NOTIFICATIONS_COOLDOWN_MINUTES` | `60` | Cooldown between same-game notifications |
| `NOTIFICATION_WEBHOOK_URL` | `None` | Webhook endpoint (optional) |
| `NOTIFICATION_WEBHOOK_SECRET` | `None` | Webhook signing secret |

### Database Schema

```sql
-- notification_events
CREATE TABLE notification_events (
    id INTEGER PRIMARY KEY,
    user_id VARCHAR NOT NULL,
    notification_type VARCHAR NOT NULL,
    title VARCHAR NOT NULL,
    body TEXT NOT NULL,
    data JSON,
    priority VARCHAR DEFAULT 'normal',
    status VARCHAR DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    sent_at TIMESTAMP,
    read_at TIMESTAMP
);

-- Indexes
CREATE INDEX idx_notifications_user ON notification_events(user_id);
CREATE INDEX idx_notifications_created ON notification_events(created_at);
CREATE INDEX idx_notifications_status ON notification_events(status);
```

### API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/notifications` | GET | List user notifications |
| `/api/notifications/preferences` | GET/POST | Notification preferences |
| `/api/notifications/{id}/read` | POST | Mark as read |
| `/health/config` | GET | Config health including flags |

---

**Last Updated:** 2026-02-14  
**Document Owner:** Engineering Team  
**Review Cycle:** Per deployment
