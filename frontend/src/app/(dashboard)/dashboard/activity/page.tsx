"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { useToast } from "@/components/ui/use-toast";
import { Activity, ChevronLeft, ChevronRight, User, Globe, Monitor } from "lucide-react";

interface ActivityLog {
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
}

interface ActivityResponse {
  items: ActivityLog[];
  total: number;
  skip: number;
  limit: number;
}

interface OAuthClient {
  id: string;
  client_id: string;
  name: string;
}

const ACTION_FILTERS = [
  { value: "all", label: "All Actions" },
  { value: "login", label: "Login" },
  { value: "logout", label: "Logout" },
  { value: "create", label: "Create" },
  { value: "update", label: "Update" },
  { value: "delete", label: "Delete" },
  { value: "invite", label: "Invite" },
  { value: "grant", label: "Grant" },
  { value: "revoke", label: "Revoke" },
];

const LOGIN_METHOD_FILTERS = [
  { value: "all", label: "All Methods" },
  { value: "direct", label: "Direct Login" },
  { value: "oauth", label: "OAuth App" },
];

const getActionColor = (action: string): string => {
  if (action.includes("delete") || action.includes("revoke")) return "destructive";
  if (action.includes("create") || action.includes("grant")) return "default";
  if (action.includes("login")) return "secondary";
  return "outline";
};

const formatDate = (dateString: string): string => {
  const date = new Date(dateString);
  return new Intl.DateTimeFormat("en-US", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(date);
};

export default function ActivityPage() {
  const { toast } = useToast();
  const [data, setData] = useState<ActivityResponse | null>(null);
  const [oauthClients, setOauthClients] = useState<OAuthClient[]>([]);
  const [loading, setLoading] = useState(true);
  const [actionFilter, setActionFilter] = useState("all");
  const [loginMethodFilter, setLoginMethodFilter] = useState("all");
  const [oauthClientFilter, setOauthClientFilter] = useState("all");
  const [page, setPage] = useState(0);
  const limit = 20;

  useEffect(() => {
    loadOAuthClients();
  }, []);

  useEffect(() => {
    loadActivity();
  }, [actionFilter, loginMethodFilter, oauthClientFilter, page]);

  const loadOAuthClients = async () => {
    try {
      const clients = await api.getOAuthClients();
      setOauthClients(clients);
    } catch {
      // User might not have permission to view OAuth clients
    }
  };

  const loadActivity = async () => {
    setLoading(true);
    try {
      const result = await api.getActivityLogs({
        action: actionFilter === "all" ? undefined : actionFilter,
        login_method: loginMethodFilter === "all" ? undefined : loginMethodFilter,
        oauth_client_id: oauthClientFilter === "all" ? undefined : oauthClientFilter,
        skip: page * limit,
        limit,
      });
      setData(result);
    } catch (error) {
      toast({
        variant: "destructive",
        title: "Error",
        description: "Failed to load activity logs",
      });
    } finally {
      setLoading(false);
    }
  };

  const totalPages = data ? Math.ceil(data.total / limit) : 0;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Activity Log</h1>
          <p className="text-muted-foreground">
            Track user actions and system events
          </p>
        </div>
        <div className="flex gap-2">
          <Select
            value={actionFilter}
            onValueChange={(value) => {
              setActionFilter(value);
              setPage(0);
            }}
          >
            <SelectTrigger className="w-[150px]">
              <SelectValue placeholder="Action" />
            </SelectTrigger>
            <SelectContent>
              {ACTION_FILTERS.map((filter) => (
                <SelectItem key={filter.value} value={filter.value}>
                  {filter.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>

          <Select
            value={loginMethodFilter}
            onValueChange={(value) => {
              setLoginMethodFilter(value);
              setPage(0);
            }}
          >
            <SelectTrigger className="w-[150px]">
              <SelectValue placeholder="Login Method" />
            </SelectTrigger>
            <SelectContent>
              {LOGIN_METHOD_FILTERS.map((filter) => (
                <SelectItem key={filter.value} value={filter.value}>
                  {filter.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>

          {oauthClients.length > 0 && (
            <Select
              value={oauthClientFilter}
              onValueChange={(value) => {
                setOauthClientFilter(value);
                setPage(0);
              }}
            >
              <SelectTrigger className="w-[180px]">
                <SelectValue placeholder="Application" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Applications</SelectItem>
                {oauthClients.map((client) => (
                  <SelectItem key={client.id} value={client.id}>
                    {client.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          )}
        </div>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Activity className="h-5 w-5" />
            Recent Activity
          </CardTitle>
          <CardDescription>
            {data ? `${data.total} total events` : "Loading..."}
          </CardDescription>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className="py-8 text-center text-muted-foreground">
              Loading activity logs...
            </div>
          ) : !data || data.items.length === 0 ? (
            <div className="py-8 text-center">
              <Activity className="h-10 w-10 mx-auto text-muted-foreground mb-3" />
              <p className="text-muted-foreground">No activity logs found.</p>
            </div>
          ) : (
            <div className="space-y-4">
              {data.items.map((log) => {
                const isOAuthLogin = log.extra_data?.login_method === "oauth";
                const oauthClientName = log.extra_data?.oauth_client_name;
                const loginMethod = log.extra_data?.login_method || log.extra_data?.logout_method;

                return (
                  <div
                    key={log.id}
                    className="flex items-start gap-4 p-4 rounded-lg border bg-card"
                  >
                    <div className="rounded-full bg-muted p-2">
                      {isOAuthLogin ? (
                        <Globe className="h-4 w-4" />
                      ) : (
                        <User className="h-4 w-4" />
                      )}
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-1 flex-wrap">
                        <span className="font-medium">
                          {log.actor.first_name} {log.actor.last_name}
                        </span>
                        <Badge variant={getActionColor(log.action) as any}>
                          {log.action}
                        </Badge>
                        {oauthClientName && (
                          <Badge variant="outline" className="gap-1">
                            <Globe className="h-3 w-3" />
                            {oauthClientName}
                          </Badge>
                        )}
                        {loginMethod === "direct" && (log.action === "login" || log.action === "logout") && (
                          <Badge variant="outline" className="gap-1">
                            <Monitor className="h-3 w-3" />
                            Direct
                          </Badge>
                        )}
                      </div>
                      <p className="text-sm text-muted-foreground">
                        {log.resource_type}
                        {log.resource_id && (
                          <span className="font-mono text-xs ml-1">
                            ({log.resource_id.slice(0, 8)}...)
                          </span>
                        )}
                        {log.ip_address && (
                          <span className="ml-2 text-xs">
                            from {log.ip_address}
                          </span>
                        )}
                      </p>
                      {log.extra_data && Object.keys(log.extra_data).filter(k => !["login_method", "logout_method", "oauth_client_id", "oauth_client_name"].includes(k)).length > 0 && (
                        <div className="mt-2 text-xs bg-muted rounded p-2 font-mono">
                          {Object.entries(log.extra_data)
                            .filter(([key]) => !["login_method", "logout_method", "oauth_client_id", "oauth_client_name"].includes(key))
                            .map(([key, value]) => (
                              <div key={key}>
                                <span className="text-muted-foreground">{key}:</span>{" "}
                                {typeof value === "object"
                                  ? JSON.stringify(value)
                                  : String(value)}
                              </div>
                            ))}
                        </div>
                      )}
                    </div>
                    <div className="text-sm text-muted-foreground whitespace-nowrap">
                      {formatDate(log.created_at)}
                    </div>
                  </div>
                );
              })}

              {/* Pagination */}
              {totalPages > 1 && (
                <div className="flex items-center justify-between pt-4">
                  <p className="text-sm text-muted-foreground">
                    Page {page + 1} of {totalPages}
                  </p>
                  <div className="flex gap-2">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => setPage((p) => Math.max(0, p - 1))}
                      disabled={page === 0}
                    >
                      <ChevronLeft className="h-4 w-4" />
                      Previous
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => setPage((p) => Math.min(totalPages - 1, p + 1))}
                      disabled={page >= totalPages - 1}
                    >
                      Next
                      <ChevronRight className="h-4 w-4" />
                    </Button>
                  </div>
                </div>
              )}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
