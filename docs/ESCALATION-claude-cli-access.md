# 🔺 ESCALATION: Claude Code CLI Access Required for Coding Work

**Date:** 2026-02-09  
**Priority:** HIGH  
**Issue:** Cannot access Claude Code CLI for cost-efficient development  
**Impact:** $6-12/day in unnecessary API costs

---

## Problem

**Current State:**
- SSH to EC2 blocked (no keys configured)
- SSM access denied (IAM role lacks permissions)
- Claude Code CLI on EC2 unusable from OpenClaw agent
- All coding work uses Anthropic API ($3-6/1M tokens)

**Desired State:**
- Agent uses Claude Code CLI on EC2 (Pro plan, $0/token)
- API calls reserved for lightweight tasks only
- Target cost: <$1/day for routine work

---

## Why This Matters

**Cost Comparison (S18-E + S19 bundle):**

| Method | Tokens | Cost |
|--------|--------|------|
| **Anthropic API (current)** | ~1.3M | ~$3.90 |
| **Claude Code CLI (Pro)** | ~1.3M | $0.00 |
| **Savings** | - | **$3.90/bundle** |

**Projected Monthly:**
- 2 bundles/week = ~$31/month API cost
- With Claude CLI = $0/month
- **Annual savings: ~$372**

---

## Root Cause

1. **SSH blocked:** No SSH key pair configured for EC2 access
2. **SSM blocked:** IAM role `EC2SSM` lacks permissions:
   - `ssm:StartSession`
   - `ssm:SendCommand`
   - `ssm:DescribeInstanceInformation`

**Current IAM Role:**
```
arn:aws:sts::053863271299:assumed-role/EC2SSM/i-0dd3b26129b0681ce
```

**Missing Policies:**
- `AmazonSSMFullAccess` (or custom minimal SSM policy)

---

## Solutions (Pick One)

### Option 1: Fix SSH Access (Recommended)
**Steps:**
1. Generate SSH key pair on OpenClaw gateway instance
2. Add public key to EC2 instance `~/.ssh/authorized_keys`
3. Update `/root/.ssh/config` with host entry

**Pros:** Simple, standard SSH workflow  
**Cons:** Requires manual key setup  
**Time:** 10 minutes

---

### Option 2: Fix SSM Permissions
**Steps:**
1. Attach `AmazonSSMFullAccess` policy to IAM role `EC2SSM`
2. OR attach custom policy:
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ssm:StartSession",
        "ssm:SendCommand",
        "ssm:DescribeInstanceInformation"
      ],
      "Resource": "*"
    }
  ]
}
```
3. Test: `aws ssm start-session --target i-<instance-id>`

**Pros:** No key management, works from anywhere  
**Cons:** Requires AWS console access  
**Time:** 5 minutes

---

### Option 3: Manual Claude CLI Workflow
**Steps:**
1. User runs Claude CLI on EC2 manually
2. Agent provides commands via Telegram
3. User pastes output back

**Pros:** No infra changes needed  
**Cons:** Slow, manual, error-prone  
**Time:** N/A (ongoing overhead)

---

## Recommendation

**Use Option 2 (SSM permissions):**
1. Most scalable (works across instances)
2. No key management overhead
3. Auditable (CloudTrail logs all SSM sessions)
4. Works from OpenClaw gateway environment

**Implementation:**
```bash
# From AWS Console or CLI with admin access:
aws iam attach-role-policy \
  --role-name EC2SSM \
  --policy-arn arn:aws:iam::aws:policy/AmazonSSMFullAccess

# Verify:
aws sts get-caller-identity
aws ssm describe-instance-information
```

---

## Impact Analysis

### Without Fix (Current)
- ✅ Bundles complete successfully
- ❌ High API costs ($3-6/bundle)
- ❌ Slow iteration (API rate limits)
- ❌ Limited by token budget

### With Fix (Claude CLI)
- ✅ $0 API cost for coding
- ✅ Faster iteration (no rate limits)
- ✅ Can use extended thinking modes
- ✅ Unlimited token budget (Pro plan)

---

## Action Items

**Immediate:**
- [ ] Choose solution (Option 1 or 2)
- [ ] Implement selected solution
- [ ] Test Claude CLI access from agent
- [ ] Document updated workflow

**Verification:**
```bash
# Test SSM access (from OpenClaw gateway):
aws ssm start-session --target i-<ec2-instance-id>

# OR test SSH access:
ssh root@100.101.182.58

# Run Claude CLI:
cd /var/lib/openbot/workdir/target
claude "List all files in app/routers/"
```

---

## Cost Protocol (Reminder)

**API Usage Hierarchy:**
1. **Claude Code CLI** (Pro plan, $0) ← **BLOCKED**
2. **Kimi 2.5** (~$0.50/1M tokens) ← Current fallback
3. **GPT-4 mini** (sub-agents only)
4. **Sonnet** (Kimi failover)
5. **Sonnet 4.5 / Opus** (escalate if >$0.50)

**Once Claude CLI is accessible:**
- All coding work → Claude CLI
- API reserved for lightweight tasks only
- Target <$1/day API usage

---

**Status:** ⚠️ AWAITING DECISION  
**Blocker:** Need SSH or SSM access to EC2  
**Next:** User chooses Option 1 or 2
