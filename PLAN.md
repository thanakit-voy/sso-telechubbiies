# Portal Telechubbiies - Implementation Plan

## 🎯 Overview

ระบบ HR/SSO สำหรับจัดการโครงสร้างผู้ใช้งานและยืนยันตัวตนแบบ Single Sign-On

### Tech Stack
- **Frontend**: Next.js 14 (App Router) + Tailwind CSS + shadcn/ui
- **Backend**: FastAPI (Python 3.11+)
- **Database**: PostgreSQL 15+
- **Auth Standard**: OAuth2/OIDC with PKCE support

---

## 📁 Project Structure

```
portal-telechubbiies/
├── frontend/                    # Next.js Application
│   ├── src/
│   │   ├── app/                # App Router pages
│   │   │   ├── (auth)/        # Auth-related pages (login, invite)
│   │   │   ├── (dashboard)/   # Protected dashboard pages
│   │   │   ├── api/           # API routes (BFF pattern)
│   │   │   └── oauth/         # OAuth endpoints
│   │   ├── components/        # React components
│   │   │   ├── ui/           # shadcn/ui components
│   │   │   └── features/     # Feature-specific components
│   │   ├── lib/              # Utilities and helpers
│   │   ├── hooks/            # Custom React hooks
│   │   ├── services/         # API client services
│   │   └── types/            # TypeScript types
│   ├── middleware.ts         # Auth middleware
│   ├── tailwind.config.ts
│   └── package.json
│
├── backend/                    # FastAPI Application
│   ├── app/
│   │   ├── api/
│   │   │   ├── v1/
│   │   │   │   ├── endpoints/
│   │   │   │   │   ├── auth.py
│   │   │   │   │   ├── users.py
│   │   │   │   │   ├── teams.py
│   │   │   │   │   ├── roles.py
│   │   │   │   │   ├── workspaces.py
│   │   │   │   │   ├── permissions.py
│   │   │   │   │   ├── invitations.py
│   │   │   │   │   ├── oauth_clients.py
│   │   │   │   │   └── activity_logs.py
│   │   │   │   └── router.py
│   │   │   └── deps.py       # Dependencies (auth, db)
│   │   ├── core/
│   │   │   ├── config.py     # Settings
│   │   │   ├── security.py   # JWT, password hashing
│   │   │   └── oauth2.py     # OAuth2/OIDC implementation
│   │   ├── models/           # SQLAlchemy models
│   │   │   ├── user.py
│   │   │   ├── team.py
│   │   │   ├── role.py
│   │   │   ├── workspace.py
│   │   │   ├── permission.py
│   │   │   ├── invitation.py
│   │   │   ├── oauth_client.py
│   │   │   └── activity_log.py
│   │   ├── schemas/          # Pydantic schemas
│   │   ├── services/         # Business logic layer
│   │   │   ├── user_service.py
│   │   │   ├── team_service.py
│   │   │   ├── invitation_service.py
│   │   │   ├── permission_service.py
│   │   │   ├── oauth_service.py
│   │   │   └── email_service.py
│   │   ├── db/
│   │   │   ├── session.py
│   │   │   └── base.py
│   │   └── main.py
│   ├── alembic/              # Database migrations
│   ├── tests/
│   │   ├── unit/
│   │   └── integration/
│   ├── requirements.txt
│   └── Dockerfile
│
├── docker/
│   ├── docker-compose.yml        # Production
│   ├── docker-compose.dev.yml    # Development
│   └── nginx/
│       └── nginx.conf
│
├── uploads/                  # User uploaded files (avatars)
└── README.md
```

---

## 🗄️ Database Schema Design

### Core Tables

```sql
-- Users table
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    avatar_url VARCHAR(500),
    avatar_path VARCHAR(500),  -- Local file path if uploaded
    password_hash VARCHAR(255),
    is_system_owner BOOLEAN DEFAULT FALSE,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Teams table (hierarchical structure)
CREATE TABLE teams (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) NOT NULL,
    slug VARCHAR(100) UNIQUE NOT NULL,  -- Globally unique
    description TEXT,
    parent_team_id UUID REFERENCES teams(id) ON DELETE CASCADE,
    owner_id UUID REFERENCES users(id) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    CONSTRAINT slug_format CHECK (slug ~ '^[a-zA-Z0-9_]+$')
);

-- Roles table
CREATE TABLE roles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) NOT NULL,
    slug VARCHAR(100) UNIQUE NOT NULL,  -- Globally unique
    description TEXT,
    team_id UUID REFERENCES teams(id) ON DELETE CASCADE NOT NULL,
    is_admin BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    CONSTRAINT slug_format CHECK (slug ~ '^[a-zA-Z0-9_]+$')
);

-- Workspaces table
CREATE TABLE workspaces (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) NOT NULL,
    slug VARCHAR(100) UNIQUE NOT NULL,  -- Globally unique
    description TEXT,
    created_by UUID REFERENCES users(id) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    CONSTRAINT slug_format CHECK (slug ~ '^[a-zA-Z0-9_]+$')
);

-- Permissions table
CREATE TABLE permissions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) NOT NULL,
    slug VARCHAR(100) UNIQUE NOT NULL,  -- Globally unique
    description TEXT,
    team_id UUID REFERENCES teams(id) ON DELETE CASCADE,  -- NULL = global (owner created)
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    CONSTRAINT slug_format CHECK (slug ~ '^[a-zA-Z0-9_]+$')
);

-- User-Team membership (with role)
CREATE TABLE team_members (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE NOT NULL,
    team_id UUID REFERENCES teams(id) ON DELETE CASCADE NOT NULL,
    role_id UUID REFERENCES roles(id) ON DELETE SET NULL,
    joined_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    UNIQUE(user_id, team_id)
);

-- Role-Permission assignments
CREATE TABLE role_permissions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    role_id UUID REFERENCES roles(id) ON DELETE CASCADE NOT NULL,
    permission_id UUID REFERENCES permissions(id) ON DELETE CASCADE NOT NULL,
    granted_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    UNIQUE(role_id, permission_id)
);

-- Team workspace access (from owner/parent)
CREATE TABLE team_workspaces (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    team_id UUID REFERENCES teams(id) ON DELETE CASCADE NOT NULL,
    workspace_id UUID REFERENCES workspaces(id) ON DELETE CASCADE NOT NULL,
    granted_by UUID REFERENCES users(id) NOT NULL,
    granted_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    UNIQUE(team_id, workspace_id)
);

-- User workspace access (granted by team admin)
CREATE TABLE user_workspaces (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE NOT NULL,
    workspace_id UUID REFERENCES workspaces(id) ON DELETE CASCADE NOT NULL,
    team_id UUID REFERENCES teams(id) ON DELETE CASCADE NOT NULL,  -- Context
    granted_by UUID REFERENCES users(id) NOT NULL,
    granted_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    UNIQUE(user_id, workspace_id, team_id)
);

-- Team permission access (from owner/parent)
CREATE TABLE team_permissions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    team_id UUID REFERENCES teams(id) ON DELETE CASCADE NOT NULL,
    permission_id UUID REFERENCES permissions(id) ON DELETE CASCADE NOT NULL,
    granted_by UUID REFERENCES users(id) NOT NULL,
    granted_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    UNIQUE(team_id, permission_id)
);

-- Invitations
CREATE TABLE invitations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) NOT NULL,
    token VARCHAR(255) UNIQUE NOT NULL,
    invitation_type VARCHAR(50) NOT NULL,  -- 'system_owner', 'team_member'
    team_id UUID REFERENCES teams(id) ON DELETE CASCADE,
    role_id UUID REFERENCES roles(id) ON DELETE SET NULL,
    invited_by UUID REFERENCES users(id),
    status VARCHAR(20) DEFAULT 'pending',  -- 'pending', 'accepted', 'expired', 'cancelled'
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    accepted_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- OAuth2 Clients (Applications)
CREATE TABLE oauth_clients (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id VARCHAR(100) UNIQUE NOT NULL,
    client_secret_hash VARCHAR(255),  -- NULL for public clients
    name VARCHAR(100) NOT NULL,
    description TEXT,
    client_type VARCHAR(20) NOT NULL,  -- 'public', 'confidential'
    redirect_uris TEXT[] NOT NULL,
    allowed_scopes TEXT[] NOT NULL,
    owner_id UUID REFERENCES users(id) NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- OAuth2 Authorization Codes
CREATE TABLE oauth_authorization_codes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    code VARCHAR(255) UNIQUE NOT NULL,
    client_id UUID REFERENCES oauth_clients(id) ON DELETE CASCADE NOT NULL,
    user_id UUID REFERENCES users(id) ON DELETE CASCADE NOT NULL,
    redirect_uri VARCHAR(500) NOT NULL,
    scope TEXT,
    code_challenge VARCHAR(255),  -- For PKCE
    code_challenge_method VARCHAR(10),  -- 'S256' or 'plain'
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    used BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Refresh Tokens
CREATE TABLE refresh_tokens (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    token_hash VARCHAR(255) UNIQUE NOT NULL,
    user_id UUID REFERENCES users(id) ON DELETE CASCADE NOT NULL,
    client_id UUID REFERENCES oauth_clients(id) ON DELETE CASCADE,
    scope TEXT,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    revoked BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Activity Logs
CREATE TABLE activity_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    actor_id UUID REFERENCES users(id) NOT NULL,
    actor_team_id UUID REFERENCES teams(id),
    action VARCHAR(100) NOT NULL,
    resource_type VARCHAR(50) NOT NULL,
    resource_id UUID,
    metadata JSONB,
    ip_address INET,
    user_agent TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for performance
CREATE INDEX idx_teams_parent ON teams(parent_team_id);
CREATE INDEX idx_teams_slug ON teams(slug);
CREATE INDEX idx_roles_team ON roles(team_id);
CREATE INDEX idx_roles_slug ON roles(slug);
CREATE INDEX idx_workspaces_slug ON workspaces(slug);
CREATE INDEX idx_permissions_slug ON permissions(slug);
CREATE INDEX idx_permissions_team ON permissions(team_id);
CREATE INDEX idx_team_members_user ON team_members(user_id);
CREATE INDEX idx_team_members_team ON team_members(team_id);
CREATE INDEX idx_invitations_token ON invitations(token);
CREATE INDEX idx_invitations_email ON invitations(email);
CREATE INDEX idx_activity_logs_actor ON activity_logs(actor_id);
CREATE INDEX idx_activity_logs_team ON activity_logs(actor_team_id);
CREATE INDEX idx_activity_logs_created ON activity_logs(created_at DESC);
CREATE INDEX idx_oauth_auth_codes_code ON oauth_authorization_codes(code);
CREATE INDEX idx_refresh_tokens_hash ON refresh_tokens(token_hash);
```

---

## 🔐 Security Implementation

### 1. Authentication Flow

```
┌──────────────────────────────────────────────────────────────┐
│                    Authentication Flow                        │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐  │
│  │ Browser │────│ Next.js │────│ FastAPI │────│ Database│  │
│  │         │    │  (BFF)  │    │  (SSO)  │    │ (Postgres│  │
│  └─────────┘    └─────────┘    └─────────┘    └─────────┘  │
│       │              │              │              │         │
│       │  1. Login    │              │              │         │
│       │─────────────►│              │              │         │
│       │              │  2. Auth     │              │         │
│       │              │─────────────►│              │         │
│       │              │              │  3. Verify   │         │
│       │              │              │─────────────►│         │
│       │              │              │◄─────────────│         │
│       │              │  4. Tokens   │              │         │
│       │              │◄─────────────│              │         │
│       │  5. Set      │              │              │         │
│       │  httpOnly    │              │              │         │
│       │  Cookie      │              │              │         │
│       │◄─────────────│              │              │         │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

### 2. Token Strategy

- **Access Token**: JWT, 15 minutes expiry
- **Refresh Token**: Opaque token, 7 days expiry, stored in DB
- **ID Token**: JWT containing user identity claims (for OIDC)

### 3. Cookie Configuration (Production)

```typescript
// Next.js API Route
const cookieOptions = {
  httpOnly: true,
  secure: true,  // HTTPS only
  sameSite: 'lax',
  path: '/',
  maxAge: 60 * 60 * 24 * 7  // 7 days
};
```

### 4. PKCE Flow (for Public Clients)

```
1. Client generates code_verifier (random string)
2. Client creates code_challenge = BASE64URL(SHA256(code_verifier))
3. Authorization request includes code_challenge
4. Token request includes code_verifier
5. Server verifies: BASE64URL(SHA256(code_verifier)) === stored_code_challenge
```

---

## 🔄 OAuth2/OIDC Endpoints

### Authorization Server Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/.well-known/openid-configuration` | GET | OIDC Discovery |
| `/.well-known/jwks.json` | GET | JSON Web Key Set |
| `/oauth/authorize` | GET | Authorization endpoint |
| `/oauth/token` | POST | Token endpoint |
| `/oauth/revoke` | POST | Token revocation |
| `/oauth/userinfo` | GET | UserInfo endpoint |
| `/oauth/introspect` | POST | Token introspection |

### Supported Scopes

- `openid` - Required for OIDC
- `profile` - first_name, last_name, avatar
- `email` - email address
- `teams` - team memberships
- `roles` - role information
- `workspaces` - workspace access
- `permissions` - permission list

### ID Token Claims Structure

```json
{
  "iss": "https://sso.telechubbiies.com",
  "sub": "user-uuid",
  "aud": "client-id",
  "exp": 1234567890,
  "iat": 1234567890,
  "auth_time": 1234567890,
  "nonce": "...",

  "email": "user@example.com",
  "given_name": "John",
  "family_name": "Doe",
  "picture": "https://...",

  "teams": [
    {"name": "Engineering", "slug": "engineering"}
  ],
  "roles": [
    {"name": "Developer", "slug": "developer"}
  ],
  "workspaces": [
    {"name": "Project Alpha", "slug": "project_alpha"}
  ],
  "permissions": [
    {"name": "Read Reports", "slug": "read_reports"}
  ]
}
```

---

## 📋 Implementation Phases

### Phase 1: Foundation (Core Infrastructure)
1. Project setup (Next.js + FastAPI + PostgreSQL)
2. Database models and migrations
3. Basic authentication (login/session)
4. System Owner bootstrap flow

### Phase 2: User & Team Management
1. Invitation system with email
2. User registration via invite
3. Team CRUD with hierarchy
4. Role management

### Phase 3: Permission System
1. Workspace CRUD
2. Permission CRUD
3. Permission inheritance logic
4. Access control enforcement

### Phase 4: OAuth2/OIDC Provider
1. OAuth client management
2. Authorization flow
3. Token issuance (access, refresh, ID)
4. PKCE support

### Phase 5: Activity & Monitoring
1. Activity logging
2. Activity log viewer with filtering
3. Audit trail

### Phase 6: Production Ready
1. Docker configuration
2. Security hardening
3. Integration tests
4. Documentation

---

## 🎨 Frontend Pages

### Authentication
- `/` - Landing/Login page
- `/invite/accept` - Accept invitation
- `/register` - Registration (via invite only)

### Dashboard
- `/dashboard` - Main dashboard
- `/dashboard/teams` - Team management
- `/dashboard/teams/[slug]` - Team detail
- `/dashboard/teams/[slug]/members` - Team members
- `/dashboard/teams/[slug]/roles` - Team roles
- `/dashboard/teams/[slug]/invitations` - Pending invitations
- `/dashboard/workspaces` - Workspace management
- `/dashboard/permissions` - Permission management
- `/dashboard/applications` - OAuth clients
- `/dashboard/activity` - Activity logs
- `/dashboard/profile` - User profile

### OAuth (External)
- `/oauth/authorize` - Authorization consent
- `/oauth/callback` - Internal callback handler

---

## 🔧 API Endpoints Overview

### Auth
- `POST /api/v1/auth/login` - Login with email/password
- `POST /api/v1/auth/logout` - Logout
- `POST /api/v1/auth/refresh` - Refresh tokens
- `GET /api/v1/auth/me` - Current user info

### Users
- `GET /api/v1/users` - List users (admin)
- `GET /api/v1/users/{id}` - Get user
- `PATCH /api/v1/users/{id}` - Update user
- `POST /api/v1/users/avatar` - Upload avatar

### Teams
- `GET /api/v1/teams` - List teams
- `POST /api/v1/teams` - Create team
- `GET /api/v1/teams/{slug}` - Get team
- `PATCH /api/v1/teams/{slug}` - Update team
- `DELETE /api/v1/teams/{slug}` - Delete team
- `GET /api/v1/teams/{slug}/members` - List members
- `POST /api/v1/teams/{slug}/members` - Add member
- `DELETE /api/v1/teams/{slug}/members/{user_id}` - Remove member
- `GET /api/v1/teams/{slug}/sub-teams` - List sub-teams

### Roles
- `GET /api/v1/teams/{slug}/roles` - List roles
- `POST /api/v1/teams/{slug}/roles` - Create role
- `PATCH /api/v1/roles/{slug}` - Update role
- `DELETE /api/v1/roles/{slug}` - Delete role
- `POST /api/v1/roles/{slug}/permissions` - Assign permissions

### Workspaces
- `GET /api/v1/workspaces` - List workspaces
- `POST /api/v1/workspaces` - Create workspace (owner only)
- `GET /api/v1/workspaces/{slug}` - Get workspace
- `PATCH /api/v1/workspaces/{slug}` - Update workspace
- `DELETE /api/v1/workspaces/{slug}` - Delete workspace
- `POST /api/v1/teams/{slug}/workspaces` - Grant workspace to team
- `POST /api/v1/users/{id}/workspaces` - Grant workspace to user

### Permissions
- `GET /api/v1/permissions` - List permissions
- `POST /api/v1/permissions` - Create permission
- `PATCH /api/v1/permissions/{slug}` - Update permission
- `DELETE /api/v1/permissions/{slug}` - Delete permission

### Invitations
- `POST /api/v1/invitations` - Create invitation
- `GET /api/v1/invitations/{token}` - Validate invitation
- `POST /api/v1/invitations/{token}/accept` - Accept invitation
- `DELETE /api/v1/invitations/{id}` - Cancel invitation

### OAuth Clients
- `GET /api/v1/oauth/clients` - List clients
- `POST /api/v1/oauth/clients` - Create client
- `GET /api/v1/oauth/clients/{id}` - Get client
- `PATCH /api/v1/oauth/clients/{id}` - Update client
- `DELETE /api/v1/oauth/clients/{id}` - Delete client
- `POST /api/v1/oauth/clients/{id}/rotate-secret` - Rotate secret

### Activity Logs
- `GET /api/v1/activity` - List activity logs

### Bootstrap
- `GET /api/v1/system/status` - Check if system is initialized
- `POST /api/v1/system/bootstrap` - Create system owner invitation

---

## ⚙️ Environment Variables

### Backend (.env)

```env
# Database
DATABASE_URL=postgresql://user:password@localhost:5432/telechubbiies

# Security
SECRET_KEY=your-super-secret-key-min-32-chars
JWT_ALGORITHM=RS256
JWT_PRIVATE_KEY_PATH=/path/to/private.pem
JWT_PUBLIC_KEY_PATH=/path/to/public.pem
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=7

# SMTP (Gmail)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
SMTP_FROM_NAME=Telechubbiies SSO

# Application
FRONTEND_URL=http://localhost:3000
BACKEND_URL=http://localhost:8000
UPLOAD_DIR=/app/uploads

# Environment
ENVIRONMENT=development  # or production
```

### Frontend (.env.local)

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_APP_URL=http://localhost:3000
```

---

## 🐳 Docker Configuration

### Production Compose Services

1. **nginx** - Reverse proxy, SSL termination
2. **frontend** - Next.js app
3. **backend** - FastAPI app
4. **db** - PostgreSQL
5. **redis** - Session cache (optional)

---