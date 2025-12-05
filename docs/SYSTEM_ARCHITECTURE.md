# Portal Telechubbiies - System Architecture

## Overview

Portal Telechubbiies เป็นระบบ HR/SSO สำหรับจัดการทีม, บทบาท, สิทธิ์, และ Workspace

---

## Entity Relationship Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              SYSTEM OWNER                                    │
│                         (is_system_owner = true)                             │
└─────────────────────────────────────────────────────────────────────────────┘
                                     │
                                     │ owns/manages
                                     ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                                  USER                                        │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │ id, email, first_name, last_name, is_active, is_system_owner        │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────────┘
           │                           │                          │
           │ owns                      │ member of                │ granted
           ▼                           ▼                          ▼
┌──────────────────┐      ┌──────────────────────┐     ┌──────────────────┐
│      TEAM        │      │    TEAM_MEMBER       │     │  USER_WORKSPACE  │
│ ┌──────────────┐ │      │ ┌──────────────────┐ │     │ ┌──────────────┐ │
│ │ id           │ │      │ │ team_id          │ │     │ │ user_id      │ │
│ │ name         │ │      │ │ user_id          │ │     │ │ workspace_id │ │
│ │ slug         │ │      │ │ role_id (null)   │ │     │ │ team_id      │ │
│ │ owner_id     │ │      │ └──────────────────┘ │     │ └──────────────┘ │
│ │ parent_id    │◄┼──┐   └──────────────────────┘     └──────────────────┘
│ └──────────────┘ │  │              │                          │
└──────────────────┘  │              │ has role                 │
         │            │              ▼                          │
         │ sub-team   │   ┌──────────────────┐                  │
         └────────────┘   │      ROLE        │                  │
                          │ ┌──────────────┐ │                  │
         ┌────────────────┤ │ id           │ │                  │
         │                │ │ name         │ │                  │
         │                │ │ slug         │ │                  │
         │                │ │ team_id      │ │                  │
         │                │ │ is_admin     │ │                  │
         │                │ │ priority     │ │                  │
         │                │ └──────────────┘ │                  │
         │                └──────────────────┘                  │
         │                         │                            │
         │                         │ has                        │
         │                         ▼                            │
         │                ┌──────────────────┐                  │
         │                │ ROLE_PERMISSION  │                  │
         │                │ ┌──────────────┐ │                  │
         │                │ │ role_id      │ │                  │
         │                │ │ permission_id│ │                  │
         │                │ └──────────────┘ │                  │
         │                └──────────────────┘                  │
         │                         │                            │
         │                         ▼                            │
         │                ┌──────────────────┐                  │
         │                │   PERMISSION     │                  │
         │                │ ┌──────────────┐ │                  │
         │                │ │ id           │ │                  │
         │                │ │ name         │ │                  │
         │                │ │ slug         │ │                  │
         │                │ │ team_id(null)│ │ ◄── Global if null
         │                │ └──────────────┘ │
         │                └──────────────────┘
         │                         ▲
         │                         │
         │                ┌──────────────────┐
         │                │ TEAM_PERMISSION  │
         │                │ ┌──────────────┐ │
         │                │ │ team_id      │ │
         │                │ │ permission_id│ │
         │                │ └──────────────┘ │
         │                └──────────────────┘
         │                         ▲
         │                         │
         │    ┌────────────────────┴────────────────────┐
         │    │                                         │
         ▼    │                                         ▼
┌──────────────────┐                          ┌──────────────────┐
│ TEAM_WORKSPACE   │                          │    WORKSPACE     │
│ ┌──────────────┐ │                          │ ┌──────────────┐ │
│ │ team_id      │ │                          │ │ id           │ │
│ │ workspace_id │ │─────────────────────────►│ │ name         │ │
│ └──────────────┘ │                          │ │ slug         │ │
└──────────────────┘                          │ │ owner_id     │ │
                                              │ └──────────────┘ │
                                              └──────────────────┘
```

---

## Team Hierarchy

```
                    ┌─────────────────┐
                    │   Root Team     │ ◄── สร้างได้โดย System Owner เท่านั้น
                    │  (parent=null)  │
                    └────────┬────────┘
                             │
              ┌──────────────┼──────────────┐
              ▼              ▼              ▼
        ┌──────────┐   ┌──────────┐   ┌──────────┐
        │ Sub-Team │   │ Sub-Team │   │ Sub-Team │ ◄── สร้างได้โดย System Owner
        │    A     │   │    B     │   │    C     │     หรือ Team Admin ของ Parent
        └────┬─────┘   └──────────┘   └──────────┘
             │
        ┌────┴────┐
        ▼         ▼
   ┌────────┐ ┌────────┐
   │Sub-Sub │ │Sub-Sub │ ◄── สามารถซ้อนได้หลายระดับ
   │ Team 1 │ │ Team 2 │
   └────────┘ └────────┘
```

---

## Role Priority System

```
Priority: 100  ┌─────────────────┐
               │   CEO           │  ◄── สูงสุด
               └─────────────────┘
                       │
Priority: 80   ┌─────────────────┐
               │   Manager       │
               └─────────────────┘
                       │
Priority: 50   ┌─────────────────┐
               │   Team Lead     │
               └─────────────────┘
                       │
Priority: 20   ┌─────────────────┐
               │   Developer     │
               └─────────────────┘
                       │
Priority: 0    ┌─────────────────┐
               │   Intern        │  ◄── ต่ำสุด (default)
               └─────────────────┘

* ค่า Priority สูงกว่า = ตำแหน่งสำคัญกว่า
* การเปลี่ยน Priority ได้เมื่อไม่มีสมาชิกใช้ Role นั้น
```

---

## User Roles & Permissions Matrix

### 1. User Types

| Type | Description | Identifier |
|------|-------------|------------|
| **System Owner** | ผู้ดูแลระบบสูงสุด มีสิทธิ์ทุกอย่าง | `user.is_system_owner = true` |
| **Team Owner** | เจ้าของทีม | `team.owner_id = user.id` |
| **Team Admin** | ผู้ดูแลทีม (มี Role ที่ `is_admin = true`) | `member.role.is_admin = true` |
| **Team Member** | สมาชิกทีมทั่วไป | มี record ใน `team_members` |
| **Regular User** | ผู้ใช้ทั่วไป | ไม่มีสิทธิ์พิเศษ |

---

## Permission Matrix by Resource

### TEAM Operations

| Operation | System Owner | Team Owner | Team Admin | Parent Team Admin | Member |
|-----------|:------------:|:----------:|:----------:|:-----------------:|:------:|
| **Create Root Team** | ✅ | ❌ | ❌ | ❌ | ❌ |
| **Create Sub-Team** | ✅ | ❌ | ✅ | ❌ | ❌ |
| **View Team** | ✅ | ✅ | ✅ | ❌ | ✅ |
| **Update Team** | ✅ | ✅ | ✅ | ❌ | ❌ |
| **Delete Team** | ✅ | ✅ | ❌ | ❌ | ❌ |

#### Delete Team Conditions:
```
❌ Cannot delete if:
   - Has sub-teams → "Delete sub-teams first"
   - Has members (except owner) → "Remove members first"
   - Has roles → "Delete roles first"
```

---

### ROLE Operations

| Operation | System Owner | Team Owner | Team Admin | Member |
|-----------|:------------:|:----------:|:----------:|:------:|
| **Create Role** | ✅ | ❌ | ✅ | ❌ |
| **View Role** | ✅ (all) | ❌ | ✅ (team) | ✅ (team) |
| **Update Role** | ✅ | ❌ | ✅ | ❌ |
| **Update Priority** | ✅* | ❌ | ✅* | ❌ |
| **Delete Role** | ✅* | ❌ | ✅* | ❌ |
| **Assign Permissions** | ✅ | ❌ | ✅ | ❌ |

#### Role Restrictions:
```
* Update Priority:
  ❌ Cannot change if members are using this role

* Delete Role:
  ❌ Cannot delete if members are using this role
```

---

### WORKSPACE Operations

| Operation | System Owner | Team Owner | Team Admin | Parent Team Admin | Member |
|-----------|:------------:|:----------:|:----------:|:-----------------:|:------:|
| **Create Workspace** | ✅ | ❌ | ❌ | ❌ | ❌ |
| **View Workspaces** | ✅ (all) | ❌ | ❌ | ❌ | ❌ |
| **Update Workspace** | ✅ | ❌ | ❌ | ❌ | ❌ |
| **Delete Workspace** | ✅* | ❌ | ❌ | ❌ | ❌ |
| **Grant to Root Team** | ✅ | ❌ | ❌ | ❌ | ❌ |
| **Grant to Sub-Team** | ✅ | ❌ | ❌ | ✅ | ❌ |
| **Revoke from Root Team** | ✅ | ❌ | ❌ | ❌ | ❌ |
| **Revoke from Sub-Team** | ✅ | ❌ | ❌ | ✅ | ❌ |

#### Delete Workspace Conditions:
```
* Delete Workspace:
  ❌ Cannot delete if:
     - Granted to any teams → "Revoke team access first"
     - Granted to any users → "Revoke user access first"
```

---

### PERMISSION Operations

| Operation | System Owner | Team Owner | Team Admin | Parent Team Admin | Member |
|-----------|:------------:|:----------:|:----------:|:-----------------:|:------:|
| **Create Global Permission** | ✅ | ❌ | ❌ | ❌ | ❌ |
| **Create Team Permission** | ✅ | ❌ | ✅ | ❌ | ❌ |
| **View Permissions** | ✅ (all) | ❌ | ✅ (team) | ❌ | ❌ |
| **Update Global Permission** | ✅ | ❌ | ❌ | ❌ | ❌ |
| **Update Team Permission** | ✅ | ❌ | ✅ | ❌ | ❌ |
| **Delete Global Permission** | ✅* | ❌ | ❌ | ❌ | ❌ |
| **Delete Team Permission** | ✅* | ❌ | ✅* | ❌ | ❌ |
| **Grant to Root Team** | ✅ | ❌ | ❌ | ❌ | ❌ |
| **Grant to Sub-Team** | ✅ | ❌ | ❌ | ✅ | ❌ |
| **Revoke from Root Team** | ✅ | ❌ | ❌ | ❌ | ❌ |
| **Revoke from Sub-Team** | ✅ | ❌ | ❌ | ✅ | ❌ |

#### Delete Permission Conditions:
```
* Delete Permission:
  ❌ Cannot delete if:
     - Assigned to any roles → "Remove from roles first"
     - Granted to any teams → "Revoke team access first"
```

---

### TEAM MEMBER Operations

| Operation | System Owner | Team Owner | Team Admin | Member |
|-----------|:------------:|:----------:|:----------:|:------:|
| **Add Member** | ✅ | ✅ | ✅ | ❌ |
| **View Members** | ✅ | ✅ | ✅ | ✅ |
| **Update Member Role** | ✅ | ✅ | ✅ | ❌ |
| **Remove Member** | ✅ | ✅ | ✅ | ❌ |
| **Remove Owner** | ❌ | ❌ | ❌ | ❌ |

#### Member Restrictions:
```
❌ Cannot remove Team Owner from their own team
```

---

### INVITATION Operations

| Operation | System Owner | Team Owner | Team Admin | Member |
|-----------|:------------:|:----------:|:----------:|:------:|
| **Create System Invite** | ✅ | ❌ | ❌ | ❌ |
| **Create Team Invite** | ✅ | ✅ | ✅ | ❌ |
| **View Invitations** | ✅ | ✅ | ✅ | ❌ |

---

## Data Flow Diagrams

### User Access to Workspace

```
User ──► TeamMember ──► Team ──► TeamWorkspace ──► Workspace
              │
              └──► Role ──► RolePermission ──► Permission
```

### Permission Inheritance

```
┌─────────────────────────────────────────────────────────────┐
│                    GLOBAL PERMISSIONS                        │
│              (permission.team_id = NULL)                     │
│         สร้างโดย System Owner, ใช้ได้ทุก Team                 │
└─────────────────────────────────────────────────────────────┘
                            │
                            │ can be granted to
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                         TEAM                                 │
│                   via TEAM_PERMISSION                        │
└─────────────────────────────────────────────────────────────┘
                            │
                            │ can be assigned to
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                         ROLE                                 │
│                   via ROLE_PERMISSION                        │
└─────────────────────────────────────────────────────────────┘
                            │
                            │ assigned to
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                      TEAM_MEMBER                             │
│                    (user in team)                            │
└─────────────────────────────────────────────────────────────┘
```

---

## Cascade Delete Behavior

### When Deleting TEAM:
```
TEAM (deleted)
  ├── Sub-Teams ──────────► CASCADE DELETE
  ├── TeamMembers ─────────► CASCADE DELETE
  ├── Roles ───────────────► CASCADE DELETE
  │     └── RolePermissions ► CASCADE DELETE
  ├── TeamWorkspaces ──────► CASCADE DELETE
  ├── TeamPermissions ─────► CASCADE DELETE
  └── Invitations ─────────► CASCADE DELETE
```

### When Deleting ROLE:
```
ROLE (deleted)
  ├── RolePermissions ─────► CASCADE DELETE
  └── TeamMembers.role_id ─► SET NULL (members keep membership)
```

### When Deleting WORKSPACE:
```
WORKSPACE (deleted)
  ├── TeamWorkspaces ──────► CASCADE DELETE
  └── UserWorkspaces ──────► CASCADE DELETE
```

### When Deleting PERMISSION:
```
PERMISSION (deleted)
  ├── RolePermissions ─────► CASCADE DELETE
  └── TeamPermissions ─────► CASCADE DELETE
```

---

## API Endpoints Summary

### Authentication
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/auth/login` | Login |
| POST | `/api/v1/auth/logout` | Logout |
| POST | `/api/v1/auth/refresh` | Refresh token |
| GET | `/api/v1/auth/me` | Get current session |

### Teams
| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| GET | `/api/v1/teams` | List teams | System Owner |
| POST | `/api/v1/teams` | Create team | System Owner / Team Admin (sub) |
| GET | `/api/v1/teams/{slug}` | Get team | Team Member |
| PATCH | `/api/v1/teams/{slug}` | Update team | Team Admin |
| DELETE | `/api/v1/teams/{slug}` | Delete team | Team Owner / System Owner |

### Roles
| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| GET | `/api/v1/roles` | List accessible roles | Authenticated |
| GET | `/api/v1/roles/teams/{slug}/roles` | List team roles | Team Admin |
| POST | `/api/v1/roles/teams/{slug}/roles` | Create role | Team Admin |
| GET | `/api/v1/roles/{slug}` | Get role | Team Member |
| PATCH | `/api/v1/roles/{slug}` | Update role | Team Admin |
| DELETE | `/api/v1/roles/{slug}` | Delete role | Team Admin |
| POST | `/api/v1/roles/{slug}/permissions` | Assign permissions | Team Admin |

### Workspaces
| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| GET | `/api/v1/workspaces` | List workspaces | System Owner |
| POST | `/api/v1/workspaces` | Create workspace | System Owner |
| PATCH | `/api/v1/workspaces/{slug}` | Update workspace | System Owner |
| DELETE | `/api/v1/workspaces/{slug}` | Delete workspace | System Owner |

### Permissions
| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| GET | `/api/v1/permissions` | List permissions | Authenticated |
| POST | `/api/v1/permissions` | Create permission | System Owner / Team Admin |
| PATCH | `/api/v1/permissions/{slug}` | Update permission | System Owner / Team Admin |
| DELETE | `/api/v1/permissions/{slug}` | Delete permission | System Owner / Team Admin |

---

## Notes

1. **System Owner** คือผู้ใช้คนแรกที่สร้างผ่าน bootstrap process
2. **Role Priority** ใช้เพื่อจัดลำดับความสำคัญของตำแหน่ง (ค่าสูง = สำคัญกว่า)
3. **Global Permission** คือ permission ที่ไม่ผูกกับ team ใด (`team_id = null`)
4. **Team Permission** คือ permission ที่สร้างโดย team (`team_id != null`)
5. การลบข้อมูลจะต้องไม่มีข้อมูลที่เกี่ยวข้องอยู่ (ยกเว้นตัวเอง)
