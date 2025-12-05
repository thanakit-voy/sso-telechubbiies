/**
 * API client for communicating with the backend.
 */

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

// Storage key for access token
const ACCESS_TOKEN_KEY = "access_token";

interface ApiError {
  detail: string;
  code?: string;
}

class ApiClient {
  private baseUrl: string;
  private accessToken: string | null = null;
  private isRefreshing = false;
  private refreshPromise: Promise<boolean> | null = null;

  constructor(baseUrl: string) {
    this.baseUrl = baseUrl;
    // Load token from localStorage on init (browser only)
    if (typeof window !== "undefined") {
      this.accessToken = localStorage.getItem(ACCESS_TOKEN_KEY);
    }
  }

  setAccessToken(token: string | null) {
    this.accessToken = token;
    if (typeof window !== "undefined") {
      if (token) {
        localStorage.setItem(ACCESS_TOKEN_KEY, token);
      } else {
        localStorage.removeItem(ACCESS_TOKEN_KEY);
      }
    }
  }

  getAccessToken(): string | null {
    return this.accessToken;
  }

  clearAuth() {
    this.setAccessToken(null);
  }

  private async request<T>(
    endpoint: string,
    options: RequestInit = {},
    skipAuth = false,
    retryCount = 0
  ): Promise<T> {
    const url = `${this.baseUrl}${endpoint}`;

    const headers: HeadersInit = {
      "Content-Type": "application/json",
      ...options.headers,
    };

    // Add Authorization header if we have a token
    if (!skipAuth && this.accessToken) {
      (headers as Record<string, string>)["Authorization"] = `Bearer ${this.accessToken}`;
    }

    const response = await fetch(url, {
      ...options,
      headers,
      credentials: "include", // Include cookies for refresh token
    });

    // Handle 401 - try to refresh token
    if (response.status === 401 && !skipAuth && retryCount === 0) {
      const refreshed = await this.tryRefreshToken();
      if (refreshed) {
        // Retry the original request with new token
        return this.request<T>(endpoint, options, skipAuth, retryCount + 1);
      }
      // Refresh failed, clear auth and throw
      this.clearAuth();
    }

    if (!response.ok) {
      let error: ApiError;
      try {
        error = await response.json();
      } catch {
        error = { detail: "An unexpected error occurred" };
      }
      throw new Error(error.detail);
    }

    // Handle empty responses
    const text = await response.text();
    if (!text) {
      return {} as T;
    }

    return JSON.parse(text);
  }

  private async tryRefreshToken(): Promise<boolean> {
    // Prevent multiple refresh calls
    if (this.isRefreshing) {
      return this.refreshPromise || Promise.resolve(false);
    }

    this.isRefreshing = true;
    this.refreshPromise = (async () => {
      try {
        const response = await fetch(`${this.baseUrl}/api/v1/auth/refresh`, {
          method: "POST",
          credentials: "include",
        });

        if (response.ok) {
          const data = await response.json();
          this.setAccessToken(data.access_token);
          return true;
        }
        return false;
      } catch {
        return false;
      } finally {
        this.isRefreshing = false;
        this.refreshPromise = null;
      }
    })();

    return this.refreshPromise;
  }

  // Auth endpoints
  async getSystemStatus() {
    return this.request<{
      initialized: boolean;
      user_count: number;
      message: string;
    }>("/api/v1/system/status");
  }

  async bootstrap(email: string) {
    return this.request<{
      message: string;
      invitation_token?: string;
    }>("/api/v1/system/bootstrap", {
      method: "POST",
      body: JSON.stringify({ email }),
    });
  }

  async validateInvitation(token: string) {
    return this.request<{
      valid: boolean;
      email: string;
      invitation_type: string;
      team_name?: string;
      role_name?: string;
      expires_at: string;
      message?: string;
    }>(`/api/v1/invitations/${token}`);
  }

  async acceptInvitation(
    token: string,
    data: {
      first_name: string;
      last_name: string;
      password: string;
      avatar_url?: string;
    }
  ) {
    return this.request<{
      id: string;
      email: string;
      first_name: string;
      last_name: string;
    }>(`/api/v1/invitations/${token}/accept`, {
      method: "POST",
      body: JSON.stringify(data),
    });
  }

  async login(email: string, password: string) {
    const response = await this.request<{
      user: {
        id: string;
        email: string;
        first_name: string;
        last_name: string;
        is_system_owner: boolean;
      };
      access_token: string;
      token_type: string;
      expires_in: number;
    }>("/api/v1/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    }, true); // skipAuth=true for login

    // Store the access token
    this.setAccessToken(response.access_token);

    return response;
  }

  async logout() {
    const response = await this.request<{ message: string }>("/api/v1/auth/logout", {
      method: "POST",
    });
    // Clear stored token
    this.clearAuth();
    return response;
  }

  async refreshToken() {
    return this.request<{
      access_token: string;
      token_type: string;
      expires_in: number;
    }>("/api/v1/auth/refresh", {
      method: "POST",
    });
  }

  async getCurrentSession() {
    return this.request<{
      user: {
        id: string;
        email: string;
        first_name: string;
        last_name: string;
        is_system_owner: boolean;
        avatar_url?: string;
      };
      is_system_owner: boolean;
      teams: Array<{
        id: string;
        name: string;
        slug: string;
        role_name?: string;
        role_slug?: string;
        is_admin: boolean;
      }>;
      permissions: string[];
    }>("/api/v1/auth/me");
  }

  // Profile
  async updateProfile(data: {
    first_name?: string;
    last_name?: string;
    avatar_url?: string;
  }) {
    return this.request<{
      id: string;
      email: string;
      first_name: string;
      last_name: string;
      avatar_url?: string;
      is_system_owner: boolean;
      is_active: boolean;
    }>("/api/v1/auth/profile", {
      method: "PATCH",
      body: JSON.stringify(data),
    });
  }

  async changePassword(data: {
    current_password: string;
    new_password: string;
  }) {
    return this.request<{ message: string }>("/api/v1/auth/change-password", {
      method: "POST",
      body: JSON.stringify(data),
    });
  }

  // Teams
  async getTeams() {
    return this.request<
      Array<{
        id: string;
        name: string;
        slug: string;
        description?: string;
        parent_team_id?: string;
        owner_id: string;
      }>
    >("/api/v1/teams");
  }

  async createTeam(data: {
    name: string;
    slug: string;
    description?: string;
    parent_team_id?: string;
  }) {
    return this.request<{
      id: string;
      name: string;
      slug: string;
    }>("/api/v1/teams", {
      method: "POST",
      body: JSON.stringify(data),
    });
  }

  async getTeam(slug: string) {
    return this.request<{
      id: string;
      name: string;
      slug: string;
      description?: string;
      owner_id: string;
      owner: {
        id: string;
        email: string;
        first_name: string;
        last_name: string;
      };
      members: Array<{
        id: string;
        user: {
          id: string;
          email: string;
          first_name: string;
          last_name: string;
          avatar_url?: string;
        };
        role?: {
          id: string;
          name: string;
          slug: string;
          is_admin: boolean;
        };
        is_admin: boolean;
        joined_at: string;
      }>;
      member_count: number;
    }>(`/api/v1/teams/${slug}`);
  }

  async updateTeam(
    slug: string,
    data: {
      name?: string;
      description?: string;
    }
  ) {
    return this.request<{
      id: string;
      name: string;
      slug: string;
      description?: string;
    }>(`/api/v1/teams/${slug}`, {
      method: "PATCH",
      body: JSON.stringify(data),
    });
  }

  async deleteTeam(slug: string) {
    return this.request<{ message: string }>(`/api/v1/teams/${slug}`, {
      method: "DELETE",
    });
  }

  async removeTeamMember(teamSlug: string, userId: string) {
    return this.request<{ message: string }>(
      `/api/v1/teams/${teamSlug}/members/${userId}`,
      { method: "DELETE" }
    );
  }

  async updateMemberRole(teamSlug: string, userId: string, roleId: string | null) {
    const params = roleId ? `?role_id=${roleId}` : "";
    return this.request<{ message: string }>(
      `/api/v1/teams/${teamSlug}/members/${userId}/role${params}`,
      { method: "PATCH" }
    );
  }

  // Invitations
  async createTeamInvitation(
    teamSlug: string,
    data: {
      email: string;
      role_id?: string;
      send_email?: boolean;
    }
  ) {
    return this.request<{
      invitation_id: string;
      link: string;
      expires_at: string;
    }>(`/api/v1/invitations/team/${teamSlug}`, {
      method: "POST",
      body: JSON.stringify(data),
    });
  }

  // Roles
  async getRoles() {
    return this.request<
      Array<{
        id: string;
        name: string;
        slug: string;
        description?: string;
        team_id: string;
        team_name?: string;
        team_slug?: string;
        is_admin: boolean;
        priority: number;
      }>
    >("/api/v1/roles");
  }

  async getTeamRoles(teamSlug: string) {
    return this.request<
      Array<{
        id: string;
        name: string;
        slug: string;
        description?: string;
        is_admin: boolean;
        priority: number;
      }>
    >(`/api/v1/roles/teams/${teamSlug}/roles`);
  }

  async getTeamRolesWithMembers(teamSlug: string) {
    return this.request<
      Array<{
        id: string;
        name: string;
        slug: string;
        description?: string;
        team_id: string;
        team_name?: string;
        team_slug?: string;
        is_admin: boolean;
        priority: number;
        member_count: number;
      }>
    >(`/api/v1/roles/teams/${teamSlug}/roles/with-members`);
  }

  async reorderRoles(teamSlug: string, roleIds: string[]) {
    return this.request<
      Array<{
        id: string;
        name: string;
        slug: string;
        priority: number;
      }>
    >(`/api/v1/roles/teams/${teamSlug}/roles/reorder`, {
      method: "POST",
      body: JSON.stringify({ role_ids: roleIds }),
    });
  }

  async createRole(
    teamSlug: string,
    data: {
      name: string;
      slug: string;
      description?: string;
      is_admin?: boolean;
      priority?: number;
    }
  ) {
    return this.request<{
      id: string;
      name: string;
      slug: string;
      priority: number;
    }>(`/api/v1/roles/teams/${teamSlug}/roles`, {
      method: "POST",
      body: JSON.stringify(data),
    });
  }

  async getRole(slug: string) {
    return this.request<{
      id: string;
      name: string;
      slug: string;
      description?: string;
      team_id: string;
      is_admin: boolean;
      created_at: string;
      updated_at: string;
      permissions: Array<{
        id: string;
        name: string;
        slug: string;
      }>;
    }>(`/api/v1/roles/${slug}`);
  }

  async updateRole(
    slug: string,
    data: {
      name?: string;
      description?: string;
      is_admin?: boolean;
      priority?: number;
    }
  ) {
    return this.request<{
      id: string;
      name: string;
      slug: string;
      description?: string;
      is_admin: boolean;
      priority: number;
    }>(`/api/v1/roles/${slug}`, {
      method: "PATCH",
      body: JSON.stringify(data),
    });
  }

  async deleteRole(slug: string) {
    return this.request<{ message: string }>(`/api/v1/roles/${slug}`, {
      method: "DELETE",
    });
  }

  async assignRolePermissions(slug: string, permissionIds: string[]) {
    return this.request<{
      id: string;
      name: string;
      slug: string;
      permissions: Array<{
        id: string;
        name: string;
        slug: string;
      }>;
    }>(`/api/v1/roles/${slug}/permissions`, {
      method: "POST",
      body: JSON.stringify({ permission_ids: permissionIds }),
    });
  }

  // Workspaces
  async getWorkspaces() {
    return this.request<
      Array<{
        id: string;
        name: string;
        slug: string;
        description?: string;
      }>
    >("/api/v1/workspaces");
  }

  async createWorkspace(data: {
    name: string;
    slug: string;
    description?: string;
  }) {
    return this.request<{
      id: string;
      name: string;
      slug: string;
    }>("/api/v1/workspaces", {
      method: "POST",
      body: JSON.stringify(data),
    });
  }

  // Permissions
  async getPermissions() {
    return this.request<
      Array<{
        id: string;
        name: string;
        slug: string;
        description?: string;
        is_global: boolean;
      }>
    >("/api/v1/permissions");
  }

  async createPermission(data: {
    name: string;
    slug: string;
    description?: string;
    team_id?: string;
  }) {
    return this.request<{
      id: string;
      name: string;
      slug: string;
    }>("/api/v1/permissions", {
      method: "POST",
      body: JSON.stringify(data),
    });
  }

  // OAuth Clients
  async getOAuthClients() {
    return this.request<
      Array<{
        id: string;
        client_id: string;
        name: string;
        description?: string;
        client_type: string;
        redirect_uris: string[];
        allowed_scopes: string[];
        is_active: boolean;
      }>
    >("/api/v1/oauth/clients");
  }

  async createOAuthClient(data: {
    name: string;
    description?: string;
    client_type: string;
    redirect_uris: string[];
    allowed_scopes: string[];
  }) {
    return this.request<{
      id: string;
      client_id: string;
      client_secret: string;
      name: string;
    }>("/api/v1/oauth/clients", {
      method: "POST",
      body: JSON.stringify(data),
    });
  }

  // Activity Logs
  async getActivityLogs(params?: {
    action?: string;
    oauth_client_id?: string;
    login_method?: string;
    skip?: number;
    limit?: number;
  }) {
    const searchParams = new URLSearchParams();
    if (params?.action) searchParams.set("action", params.action);
    if (params?.oauth_client_id) searchParams.set("oauth_client_id", params.oauth_client_id);
    if (params?.login_method) searchParams.set("login_method", params.login_method);
    if (params?.skip) searchParams.set("skip", params.skip.toString());
    if (params?.limit) searchParams.set("limit", params.limit.toString());

    const query = searchParams.toString();
    return this.request<{
      items: Array<{
        id: string;
        actor: {
          id: string;
          email: string;
          first_name: string;
          last_name: string;
        };
        action: string;
        resource_type: string;
        resource_id?: string;
        extra_data?: Record<string, any>;
        ip_address?: string;
        created_at: string;
      }>;
      total: number;
      skip: number;
      limit: number;
    }>(`/api/v1/activity${query ? `?${query}` : ""}`);
  }
}

export const api = new ApiClient(API_URL);
