# Portal Telechubbiies

HR/SSO System - ระบบจัดการโครงสร้างผู้ใช้งานและยืนยันตัวตนแบบ Single Sign-On

## Features

- **OAuth2/OIDC Provider** - ให้ระบบอื่นใช้ Login with Telechubbiies
- **Hierarchical Teams** - โครงสร้างทีมแบบไม่จำกัดลำดับขั้น
- **Role-Based Access Control** - กำหนด Role และ Permission ได้อย่างละเอียด
- **Workspace Management** - จัดการพื้นที่ทำงานและกำหนดสิทธิ์
- **Invitation System** - ระบบเชิญเข้าทีม (ไม่มีการสมัครสมาชิก)
- **Activity Logging** - บันทึกกิจกรรมสำหรับ Audit Trail
- **PKCE Support** - รองรับ Public Clients อย่างปลอดภัย

## Tech Stack

- **Frontend**: Next.js 14 + Tailwind CSS + shadcn/ui
- **Backend**: FastAPI (Python 3.11+)
- **Database**: PostgreSQL 15+
- **Auth**: OAuth2/OIDC with RS256 JWT

## Quick Start

### Development

1. **Start PostgreSQL**:
```bash
cd docker
docker-compose -f docker-compose.dev.yml up -d
```

2. **Setup Backend**:
```bash
cd backend
python -m venv venv
# Windows
venv\Scripts\activate
# Linux/Mac
source venv/bin/activate

pip install -r requirements.txt

# Copy and edit environment
cp .env.example .env

# Run backend
uvicorn app.main:app --reload
```

3. **Setup Frontend**:
```bash
cd frontend
npm install

# Copy and edit environment
cp .env.example .env.local

# Run frontend
npm run dev
```

4. **Access the app**: http://localhost:3000

### Production (Docker)

```bash
cd docker
cp .env.example .env
# Edit .env with production values

docker-compose up -d
```

## Project Structure

```
portal-telechubbiies/
├── frontend/               # Next.js Application
│   ├── src/
│   │   ├── app/           # App Router pages
│   │   ├── components/    # React components
│   │   ├── lib/          # Utilities
│   │   └── hooks/        # Custom hooks
│   └── ...
│
├── backend/               # FastAPI Application
│   ├── app/
│   │   ├── api/          # API endpoints
│   │   ├── core/         # Config & security
│   │   ├── models/       # SQLAlchemy models
│   │   ├── schemas/      # Pydantic schemas
│   │   ├── services/     # Business logic
│   │   └── db/           # Database
│   └── ...
│
├── docker/                # Docker configuration
│   ├── docker-compose.yml
│   ├── docker-compose.dev.yml
│   └── nginx/
│
└── README.md
```

## Initial Setup

เมื่อเปิดระบบครั้งแรก:

1. เข้า http://localhost:3000
2. กรอก Email สำหรับ System Owner
3. ระบบจะส่ง Invitation Link ไปทาง Email (หรือแสดงใน Console สำหรับ Dev)
4. เปิด Link เพื่อสร้าง Account
5. สร้าง Team และ Role แรก
6. เริ่มเชิญคนเข้าทีม

## OAuth2/OIDC Integration

### สำหรับ Client Application

1. ไปที่ Dashboard > Applications
2. สร้าง OAuth Client ใหม่
3. ตั้งค่า Redirect URIs
4. เลือก Scopes ที่ต้องการ
5. นำ Client ID/Secret ไปใช้

### Endpoints

| Endpoint | Description |
|----------|-------------|
| `/.well-known/openid-configuration` | OIDC Discovery |
| `/.well-known/jwks.json` | JSON Web Keys |
| `/oauth/authorize` | Authorization |
| `/oauth/token` | Token |
| `/oauth/userinfo` | User Info |

### Scopes

- `openid` - Required for OIDC
- `profile` - Name and avatar
- `email` - Email address
- `teams` - Team memberships
- `roles` - Role information
- `workspaces` - Workspace access
- `permissions` - Permission list

### ID Token Claims

```json
{
  "sub": "user-uuid",
  "email": "user@example.com",
  "given_name": "John",
  "family_name": "Doe",
  "teams": [{"name": "Engineering", "slug": "engineering"}],
  "roles": [{"name": "Developer", "slug": "developer"}],
  "workspaces": [{"name": "Project A", "slug": "project_a"}],
  "permissions": [{"name": "Read Reports", "slug": "read_reports"}]
}
```

## Security Features

- RS256 JWT Tokens
- httpOnly Cookies (no localStorage)
- PKCE for Public Clients
- Refresh Token Rotation
- Rate Limiting
- Activity Audit Log
- Unique Slugs Globally

## License

MIT
