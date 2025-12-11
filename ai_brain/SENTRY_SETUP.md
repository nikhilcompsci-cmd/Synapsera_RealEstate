# Sentry Integration Guide

## Overview

Sentry is integrated for centralized error tracking, performance monitoring, and admin notifications. All critical errors and system issues are automatically reported to Sentry with full context.

## Setup

### 1. Create Sentry Account
1. Go to https://sentry.io and sign up
2. Create a new organization (or use existing)
3. Create a new project:
   - Platform: **Python/FastAPI**
   - Project name: **AI Brain - Real Estate**

### 2. Get DSN (Data Source Name)
1. In Sentry dashboard, go to **Settings** > **Projects** > **[Your Project]** > **Client Keys (DSN)**
2. Copy the DSN (looks like: `https://abc123@o123456.ingest.sentry.io/789`)

### 3. Configure Environment Variables
Add to your `.env` file:

```bash
# Sentry Configuration
SENTRY_DSN=https://YOUR_KEY@YOUR_ORG.ingest.sentry.io/YOUR_PROJECT
SENTRY_ENVIRONMENT=production  # or development, staging
SENTRY_ENABLED=true
SENTRY_TRACES_SAMPLE_RATE=0.1  # 10% of transactions (adjust as needed)
```

**Sample rates:**
- `1.0` = 100% (development - capture everything)
- `0.1` = 10% (production - sample to reduce costs)
- `0.01` = 1% (high-traffic production)

### 4. Restart Application
```powershell
python run_server.py
```

You should see in the logs:
```
✅ Sentry initialized successfully
   Environment: production
   Traces sample rate: 10.0%
```

---

## What Gets Tracked

### 1. **Automatic Error Capture**
All unhandled exceptions are automatically sent to Sentry:
- API errors (500, 503, etc.)
- Celery task failures  
- Database errors
- Any uncaught exceptions

### 2. **Failed Document Ingestion**
When a document fails to process:
```python
track_failed_document(
    filename="contract.pdf",
    error_type="transient",
    error_message="Redis timeout",
    project_id=123,
    user_id=456
)
```

**Captured:**
- Filename
- Error type and message (sanitized)
- Project and user IDs
- Full stack trace

### 3. **Admin Alerts**
System issues that require immediate admin attention:
```python
alert_admin(
    message="Celery/Redis unavailable in production",
    error_type="system_issue",
    context={'impact': 'Document uploads blocked'}
)
```

**Triggers:**
- Redis/Celery connection loss (production)
- Disk space issues
- Rate limit exceeded
- Infrastructure problems

### 4. **Performance Monitoring**
Automatically tracks:
- API endpoint response times
- Database query performance
- Celery task execution time
- Slow transactions

---

## Configure Notifications

### Email Alerts
1. Go to **Settings** > **Projects** > **[Your Project]** > **Alerts**
2. Click **Create Alert Rule**
3. Choose trigger:
   - **Issue Alert**: When error occurs
   - **Metric Alert**: When error rate exceeds threshold
4. Set conditions:
   - Error level: `error` or `fatal`
   - Tags: `alert_type:admin` or `error_type:system_issue`
5. Choose action: **Send email to team**
6. Add recipients

### Slack Integration
1. Go to **Settings** > **Integrations** > **Slack**
2. Click **Add to Slack**
3. Choose channel (e.g., `#alerts` or `#errors`)
4. Configure alert routing:
   - Critical errors → `#alerts`
   - All errors → `#errors`
   - Performance issues → `#performance`

### Alert Routing Examples
```
# Route by error type
IF tags.error_type = "system_issue" THEN notify #alerts
IF tags.error_type = "transient" THEN notify #errors

# Route by severity
IF level = "fatal" THEN notify #alerts @oncall
IF level = "error" AND tags.alert_type = "admin" THEN notify #alerts

# Rate-based alerts
IF error rate > 10/minute THEN notify #alerts
IF failed_document count > 50/hour THEN notify #admin
```

---

## Sentry Dashboard

### Key Metrics to Monitor

**1. Issues Overview**
- Total errors
- Error rate trend
- Top error types
- Affected users

**2. Failed Documents**
- Filter by tag: `event_type:failed_document`
- Group by: `error_type`
- See: filename, project_id, user_id

**3. Admin Alerts**
- Filter by tag: `alert_type:admin`
- Level: `error` or `fatal`
- Shows: system issues, infrastructure problems

**4. Performance**
- Slow API endpoints
- Slow database queries
- Celery task duration

### Custom Searches

**Find all admin alerts:**
```
tags.alert_type:admin level:error
```

**Find failed documents:**
```
tags.event_type:failed_document
```

**Find production errors:**
```
environment:production level:error
```

**Find Celery failures:**
```
tags.error_type:celery_unavailable
```

---

## Testing

### Test Sentry Integration
```python
# In Python console or test file
from config.sentry_config import alert_admin, track_failed_document
from config.settings import get_settings

settings = get_settings()

# Test 1: Simple alert
alert_admin(
    message="Test alert from dev",
    error_type="test",
    context={'test': True}
)

# Test 2: Failed document
track_failed_document(
    filename="test.pdf",
    error_type="test",
    error_message="This is a test",
    project_id=999,
    user_id=999
)

print("✅ Check Sentry dashboard for test events")
```

### Verify in Sentry Dashboard
1. Go to **Issues**
2. You should see:
   - "⚠️ ADMIN ALERT: Test alert from dev"
   - "Document ingestion failed: test.pdf"

---

## Production Checklist

Before going live:

- [ ] Sentry DSN configured in production `.env`
- [ ] `SENTRY_ENVIRONMENT=production` set
- [ ] Traces sample rate adjusted (0.1 for 10%)
- [ ] Email alerts configured for admins
- [ ] Slack integration set up
- [ ] Alert rules created:
  - [ ] System issues → immediate notification
  - [ ] High error rate → team notification
  - [ ] Failed documents → daily summary
- [ ] Team members invited to Sentry project
- [ ] On-call rotation configured (if applicable)

---

## Cost Optimization

Sentry has usage-based pricing:

**Free Tier:**
- 5,000 errors/month
- 10,000 transactions/month
- Good for development and small production

**Optimize Usage:**
1. **Adjust sample rate** in production:
   ```bash
   SENTRY_TRACES_SAMPLE_RATE=0.1  # 10% instead of 100%
   ```

2. **Filter events** in code:
   - Don't send debug/info in production
   - Filter out known errors (e.g., 404s)

3. **Set data retention**:
   - Keep only last 30 days
   - Archive old issues

4. **Use rate limits**:
   ```python
   # In sentry_config.py
   # Add to filter_event() function
   if environment == "production":
       # Drop non-critical warnings
       if level == 'warning' and error_type not in ['system_issue']:
           return None
   ```

---

## Troubleshooting

### Sentry not sending events
1. **Check DSN**: Ensure `SENTRY_DSN` is set correctly
2. **Check enabled**: Ensure `SENTRY_ENABLED=true`
3. **Check logs**: Look for "✅ Sentry initialized successfully"
4. **Test manually**:
   ```python
   from config.sentry_config import alert_admin
   alert_admin("Test", "test", {})
   ```

### Too many events
1. Lower `SENTRY_TRACES_SAMPLE_RATE` to `0.1` or `0.01`
2. Add filters in `filter_event()` function
3. Set error rate limits in Sentry dashboard

### Not receiving notifications
1. Check **Settings** > **Projects** > **Alerts**
2. Verify email/Slack integration configured
3. Check alert rules match error conditions
4. Look for alert in Sentry dashboard first

---

## Summary

✅ **What you get:**
- Automatic error tracking with stack traces
- Admin alerts via email/Slack
- Performance monitoring
- Failed document tracking
- Production error notifications
- Centralized monitoring dashboard

✅ **What admins see:**
- Real-time errors
- Error trends and rates
- Affected users and projects
- Full context for debugging
- Performance bottlenecks

✅ **No code changes needed** once configured - everything is automatic!
