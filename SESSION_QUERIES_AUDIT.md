# Session Queries Audit

## Overview
This document shows all places in the codebase where sessions are being queried from the database.

---

## ✅ Frontend Session Queries (Supabase Direct)

### 1. **useSessionStatus Hook** - Single Session Polling
**File:** `frontend/src/hooks/useSessionStatus.ts`

```typescript
// Query: Get single session by ID
const { data, error } = await supabase
  .from('sessions')
  .select('*')
  .eq('id', sessionId)
  .maybeSingle()
```

**Purpose:** Poll for a specific session's status (used by customers waiting for call acceptance)  
**Filter:** `id = sessionId`  
**Usage:** Customer side - tracks when pending → active

---

### 2. **usePendingSessions Hook** - Rep's Pending Sessions
**File:** `frontend/src/hooks/usePendingSessions.ts`

```typescript
// Query: Get all pending sessions for a rep
const { data, error } = await supabase
  .from('sessions')
  .select('*')
  .eq('customer_rep_id', user.id)
  .eq('status', 'pending')
  .order('created_at', { ascending: false })
```

**Purpose:** Show pending call requests to customer reps  
**Filter:** `customer_rep_id = user.id AND status = 'pending'`  
**Usage:** Agent Dashboard - PendingCalls component

**Also handles updates:**
```typescript
// Accept session
const { error } = await supabase
  .from('sessions')
  .update({ status: 'active' })
  .eq('id', sessionId)
  .eq('customer_rep_id', user?.id)

// Reject session
const { error } = await supabase
  .from('sessions')
  .update({ status: 'closed' })
  .eq('id', sessionId)
  .eq('customer_rep_id', user?.id)
```

---

### 3. **useActiveSessions Hook** - Rep's Active Sessions
**File:** `frontend/src/hooks/useActiveSessions.ts`

```typescript
// Query: Get all active sessions for a rep
const { data, error } = await supabase
  .from('sessions')
  .select('*')
  .eq('customer_rep_id', user.id)
  .eq('status', 'active')
  .order('created_at', { ascending: false })
```

**Purpose:** Show ongoing calls to customer reps  
**Filter:** `customer_rep_id = user.id AND status = 'active'`  
**Usage:** Dashboard page - Ongoing Calls section

---

### 4. **useAllSessions Hook** - Rep's All Sessions
**File:** `frontend/src/hooks/useAllSessions.ts`

```typescript
// Query: Get all sessions for a rep (any status)
const { data, error } = await supabase
  .from('sessions')
  .select('*')
  .eq('customer_rep_id', user.id)
  .order('created_at', { ascending: false })
```

**Purpose:** Show complete session history  
**Filter:** `customer_rep_id = user.id`  
**Usage:** Transcripts page - All call history

---

## ✅ Backend Session Queries (Python/Supabase)

### 5. **Create Session** - Customer Initiates Call
**File:** `backend/services/database_service.py` (Line 21-43)

```python
# Insert new session
result = self.supabase.table("sessions").insert({
    "customer_rep_id": customer_rep_id,
    "customer_name": customer_name,
    "status": "pending",
    "metadata": metadata or {}
}).execute()
```

**Purpose:** Create new session when customer requests a call  
**Endpoint:** `POST /api/customer-service/call`  
**Initial Status:** `pending`

---

### 6. **Accept Session** - Rep Accepts Call
**File:** `backend/services/database_service.py` (Line 45-53)

```python
# Update session to active
result = self.supabase.table("sessions")\
    .update({"status": "active"})\
    .eq("id", session_id)\
    .eq("customer_rep_id", customer_rep_id)\
    .execute()
```

**Purpose:** Mark session as active when rep accepts  
**Endpoint:** `POST /api/agent/sessions/{sessionId}/accept` (via usePendingSessions)

---

### 7. **Get Session by ID** - Verify Access
**File:** `backend/services/database_service.py` (Line 55-62)

```python
# Get single session with security check
result = self.supabase.table("sessions")\
    .select("*")\
    .eq("id", session_id)\
    .eq("customer_rep_id", customer_rep_id)\
    .execute()
```

**Purpose:** Fetch session details with access control  
**Filter:** `id = session_id AND customer_rep_id = customer_rep_id`

---

### 8. **Get Sessions with Filters** - Generic Query
**File:** `backend/services/database_service.py` (Line 65-84)

```python
# Get sessions with optional status filter
query = self.supabase.table("sessions")\
    .select("*")\
    .eq("customer_rep_id", customer_rep_id)

if status:
    query = query.eq("status", status)

result = query.order("created_at", desc=True)\
    .range(offset, offset + limit - 1)\
    .execute()
```

**Purpose:** Generic session retrieval with filtering  
**Endpoint:** `GET /api/sessions`

---

### 9. **Get Pending Sessions for Rep**
**File:** `backend/services/database_service.py` (Line 86-104)

```python
# Get pending sessions (backend version)
result = self.supabase.table("sessions")\
    .select("*")\
    .eq("customer_rep_id", customer_rep_id)\
    .eq("status", "pending")\
    .order("created_at", desc=True)\
    .range(0, limit - 1)\
    .execute()
```

**Purpose:** Backend endpoint for pending sessions  
**Endpoint:** `GET /api/reps/pending-sessions`  
**Note:** Duplicates frontend logic (frontend queries Supabase directly)

---

### 10. **Get Active Sessions for Rep**
**File:** `backend/services/database_service.py` (Line 106-124)

```python
# Get active sessions (backend version)
result = self.supabase.table("sessions")\
    .select("*")\
    .eq("customer_rep_id", customer_rep_id)\
    .eq("status", "active")\
    .order("created_at", desc=True)\
    .range(0, limit - 1)\
    .execute()
```

**Purpose:** Backend endpoint for active sessions  
**Endpoint:** `GET /api/reps/active-sessions`  
**Note:** Duplicates frontend logic (frontend queries Supabase directly)

---

### 11. **Update Session** - Generic Update
**File:** `backend/services/database_service.py` (Line 126-138)

```python
# Update session fields
result = self.supabase.table("sessions")\
    .update(updates)\
    .eq("id", session_id)\
    .eq("customer_rep_id", customer_rep_id)\
    .execute()
```

**Purpose:** Generic session update with access control

---

### 12. **Close Session** - End Call
**File:** `backend/services/database_service.py` (Line 140-148)

```python
# Close session
result = self.supabase.table("sessions")\
    .update({"status": "closed"})\
    .eq("id", session_id)\
    .eq("customer_rep_id", customer_rep_id)\
    .execute()
```

**Purpose:** Mark session as closed  
**Endpoint:** `POST /api/sessions/{sessionId}/close`

---

### 13. **Session Analytics** - Aggregate Data
**File:** `backend/services/database_service.py` (Line 443-469)

```python
# Get all sessions for analytics
query = self.supabase.table("sessions")\
    .select("*")\
    .eq("customer_rep_id", customer_rep_id)

if start_date:
    query = query.gte("created_at", start_date.isoformat())
if end_date:
    query = query.lte("created_at", end_date.isoformat())

result = query.execute()
```

**Purpose:** Generate analytics for rep's sessions  
**Endpoint:** Internal analytics calculation

---

## 🔍 Key Observations

### Database Schema Pattern
All queries follow this pattern:
```
sessions
├── id (UUID, primary key)
├── customer_rep_id (UUID, foreign key → users/reps)
├── customer_name (TEXT)
├── status ('active', 'pending', 'closed', 'paused')
├── created_at (TIMESTAMP)
├── updated_at (TIMESTAMP)
├── closed_at (TIMESTAMP, nullable)
└── metadata (JSONB)
```

### Common Filters
1. **By Rep:** `.eq('customer_rep_id', user.id)` - Most common, ensures data isolation
2. **By Status:** `.eq('status', 'pending|active|closed')` - For workflow states
3. **By Session ID:** `.eq('id', sessionId)` - For specific session operations
4. **With Access Control:** Both `id` AND `customer_rep_id` together for security

### Query Methods Used
- **Frontend (Supabase-js):**
  - `.maybeSingle()` - Returns null if not found (safe for 0 rows)
  - `.single()` - Throws error if not found (avoid this!)
  - `.select('*')` - Get all columns
  - `.order()` - Sort results
  
- **Backend (Python Supabase):**
  - `.insert()` - Create new records
  - `.update()` - Modify existing records
  - `.select()` - Fetch records
  - `.range()` - Pagination

### Real-time Subscriptions
All frontend hooks use Supabase Realtime:
```typescript
supabase
  .channel('channel-name')
  .on('postgres_changes', {
    event: '*',  // or 'INSERT', 'UPDATE', 'DELETE'
    schema: 'public',
    table: 'sessions',
    filter: `customer_rep_id=eq.${user.id}`
  }, callback)
  .subscribe()
```

### Polling Strategy
- **useSessionStatus:** 2 seconds (customer waiting for call)
- **usePendingSessions:** 5 seconds (rep dashboard)
- **useActiveSessions:** 5 seconds (rep dashboard)
- **useAllSessions:** 5 seconds (transcripts page)

---

## ✅ Current Status: All Working Correctly

All session queries are correctly configured and follow consistent patterns:
1. ✅ Proper filtering by `customer_rep_id` for data isolation
2. ✅ Using `.maybeSingle()` to avoid 0-row errors
3. ✅ Real-time subscriptions for instant updates
4. ✅ Polling as backup for reliability
5. ✅ Proper security checks in backend (both ID + rep_id)

The issue you were experiencing was due to the missing initial `fetchSession()` call in `useSessionStatus`, which has now been fixed.

