"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Checkbox } from "@/components/ui/checkbox";
import { useToast } from "@/components/ui/use-toast";
import { Plus, AppWindow, Copy, Check } from "lucide-react";

interface OAuthClient {
  id: string;
  client_id: string;
  name: string;
  description?: string;
  client_type: string;
  redirect_uris: string[];
  allowed_scopes: string[];
  is_active: boolean;
}

const AVAILABLE_SCOPES = [
  { value: "openid", label: "OpenID (required for OIDC)" },
  { value: "profile", label: "Profile (name and avatar)" },
  { value: "email", label: "Email address" },
  { value: "teams", label: "Team memberships" },
  { value: "roles", label: "Role information" },
  { value: "workspaces", label: "Workspace access" },
  { value: "permissions", label: "Permission list" },
];

export default function ApplicationsPage() {
  const { toast } = useToast();
  const [clients, setClients] = useState<OAuthClient[]>([]);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [creating, setCreating] = useState(false);
  const [newClientSecret, setNewClientSecret] = useState<string | null>(null);
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const [formData, setFormData] = useState({
    name: "",
    description: "",
    client_type: "confidential",
    redirect_uris: "",
    allowed_scopes: ["openid"] as string[],
  });

  useEffect(() => {
    loadClients();
  }, []);

  const loadClients = async () => {
    try {
      const data = await api.getOAuthClients();
      setClients(data);
    } catch (error) {
      toast({
        variant: "destructive",
        title: "Error",
        description: "Failed to load OAuth clients",
      });
    } finally {
      setLoading(false);
    }
  };

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    setCreating(true);

    try {
      const redirectUris = formData.redirect_uris
        .split("\n")
        .map((uri) => uri.trim())
        .filter((uri) => uri);

      const result = await api.createOAuthClient({
        name: formData.name,
        description: formData.description || undefined,
        client_type: formData.client_type,
        redirect_uris: redirectUris,
        allowed_scopes: formData.allowed_scopes,
      });

      setNewClientSecret(result.client_secret);
      toast({
        title: "Application Created",
        description: "Your OAuth application has been created. Save the client secret now!",
      });
      loadClients();
    } catch (error) {
      toast({
        variant: "destructive",
        title: "Error",
        description: error instanceof Error ? error.message : "Failed to create application",
      });
    } finally {
      setCreating(false);
    }
  };

  const handleScopeToggle = (scope: string) => {
    if (scope === "openid") return; // Always required
    setFormData((prev) => ({
      ...prev,
      allowed_scopes: prev.allowed_scopes.includes(scope)
        ? prev.allowed_scopes.filter((s) => s !== scope)
        : [...prev.allowed_scopes, scope],
    }));
  };

  const copyToClipboard = async (text: string, id: string) => {
    await navigator.clipboard.writeText(text);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  const resetForm = () => {
    setShowCreate(false);
    setNewClientSecret(null);
    setFormData({
      name: "",
      description: "",
      client_type: "confidential",
      redirect_uris: "",
      allowed_scopes: ["openid"],
    });
  };

  if (loading) {
    return <div>Loading...</div>;
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Applications</h1>
          <p className="text-muted-foreground">
            Manage OAuth applications that can use Login with Telechubbiies
          </p>
        </div>
        <Button onClick={() => setShowCreate(true)} className="gap-2">
          <Plus className="h-4 w-4" />
          Create Application
        </Button>
      </div>

      {/* Create Application Form */}
      {showCreate && (
        <Card>
          <CardHeader>
            <CardTitle>
              {newClientSecret ? "Application Created" : "Create New Application"}
            </CardTitle>
            <CardDescription>
              {newClientSecret
                ? "Save the client secret now. You won't be able to see it again!"
                : "Create a new OAuth client application."}
            </CardDescription>
          </CardHeader>
          <CardContent>
            {newClientSecret ? (
              <div className="space-y-4">
                <div className="p-4 bg-yellow-50 border border-yellow-200 rounded-md">
                  <p className="text-sm text-yellow-800 font-medium mb-2">
                    Important: Save your client secret now!
                  </p>
                  <p className="text-sm text-yellow-700">
                    This is the only time you'll see the client secret. Copy it and store it securely.
                  </p>
                </div>
                <div className="space-y-2">
                  <Label>Client Secret</Label>
                  <div className="flex gap-2">
                    <Input
                      value={newClientSecret}
                      readOnly
                      className="font-mono text-sm"
                    />
                    <Button
                      variant="outline"
                      size="icon"
                      onClick={() => copyToClipboard(newClientSecret, "secret")}
                    >
                      {copiedId === "secret" ? (
                        <Check className="h-4 w-4" />
                      ) : (
                        <Copy className="h-4 w-4" />
                      )}
                    </Button>
                  </div>
                </div>
                <Button onClick={resetForm}>Done</Button>
              </div>
            ) : (
              <form onSubmit={handleCreate} className="space-y-4">
                <div className="grid gap-4 md:grid-cols-2">
                  <div className="space-y-2">
                    <Label htmlFor="name">Application Name</Label>
                    <Input
                      id="name"
                      value={formData.name}
                      onChange={(e) =>
                        setFormData({ ...formData, name: e.target.value })
                      }
                      placeholder="My Application"
                      required
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="client_type">Client Type</Label>
                    <Select
                      value={formData.client_type}
                      onValueChange={(value) =>
                        setFormData({ ...formData, client_type: value })
                      }
                    >
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="confidential">
                          Confidential (Server-side app)
                        </SelectItem>
                        <SelectItem value="public">
                          Public (SPA/Mobile app with PKCE)
                        </SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                </div>
                <div className="space-y-2">
                  <Label htmlFor="description">Description (optional)</Label>
                  <Input
                    id="description"
                    value={formData.description}
                    onChange={(e) =>
                      setFormData({ ...formData, description: e.target.value })
                    }
                    placeholder="Application description..."
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="redirect_uris">Redirect URIs (one per line)</Label>
                  <textarea
                    id="redirect_uris"
                    value={formData.redirect_uris}
                    onChange={(e) =>
                      setFormData({ ...formData, redirect_uris: e.target.value })
                    }
                    placeholder="https://myapp.com/callback&#10;https://localhost:3000/callback"
                    className="w-full min-h-[100px] rounded-md border border-input bg-background px-3 py-2 text-sm"
                    required
                  />
                </div>
                <div className="space-y-2">
                  <Label>Allowed Scopes</Label>
                  <div className="grid gap-2 md:grid-cols-2">
                    {AVAILABLE_SCOPES.map((scope) => (
                      <div key={scope.value} className="flex items-center space-x-2">
                        <Checkbox
                          id={scope.value}
                          checked={formData.allowed_scopes.includes(scope.value)}
                          onCheckedChange={() => handleScopeToggle(scope.value)}
                          disabled={scope.value === "openid"}
                        />
                        <label
                          htmlFor={scope.value}
                          className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70"
                        >
                          {scope.label}
                        </label>
                      </div>
                    ))}
                  </div>
                </div>
                <div className="flex gap-2">
                  <Button type="submit" disabled={creating}>
                    {creating ? "Creating..." : "Create Application"}
                  </Button>
                  <Button type="button" variant="outline" onClick={resetForm}>
                    Cancel
                  </Button>
                </div>
              </form>
            )}
          </CardContent>
        </Card>
      )}

      {/* OAuth Clients List */}
      {clients.length === 0 ? (
        <Card>
          <CardContent className="py-12 text-center">
            <AppWindow className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
            <h3 className="text-lg font-medium mb-2">No applications yet</h3>
            <p className="text-muted-foreground mb-4">
              Create your first OAuth application to enable SSO.
            </p>
            <Button onClick={() => setShowCreate(true)} className="gap-2">
              <Plus className="h-4 w-4" />
              Create Application
            </Button>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-4">
          {clients.map((client) => (
            <Card key={client.id}>
              <CardHeader>
                <div className="flex items-start justify-between">
                  <div>
                    <CardTitle className="flex items-center gap-2">
                      <AppWindow className="h-5 w-5" />
                      {client.name}
                    </CardTitle>
                    <CardDescription>{client.description}</CardDescription>
                  </div>
                  <div className="flex gap-2">
                    <Badge
                      variant={client.client_type === "public" ? "outline" : "secondary"}
                    >
                      {client.client_type}
                    </Badge>
                    <Badge variant={client.is_active ? "default" : "destructive"}>
                      {client.is_active ? "Active" : "Inactive"}
                    </Badge>
                  </div>
                </div>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="space-y-2">
                  <Label>Client ID</Label>
                  <div className="flex gap-2">
                    <Input
                      value={client.client_id}
                      readOnly
                      className="font-mono text-sm"
                    />
                    <Button
                      variant="outline"
                      size="icon"
                      onClick={() => copyToClipboard(client.client_id, client.id)}
                    >
                      {copiedId === client.id ? (
                        <Check className="h-4 w-4" />
                      ) : (
                        <Copy className="h-4 w-4" />
                      )}
                    </Button>
                  </div>
                </div>
                <div className="grid gap-4 md:grid-cols-2">
                  <div>
                    <Label className="text-muted-foreground">Redirect URIs</Label>
                    <ul className="mt-1 text-sm space-y-1">
                      {client.redirect_uris.map((uri, i) => (
                        <li key={i} className="font-mono text-xs truncate">
                          {uri}
                        </li>
                      ))}
                    </ul>
                  </div>
                  <div>
                    <Label className="text-muted-foreground">Allowed Scopes</Label>
                    <div className="mt-1 flex flex-wrap gap-1">
                      {client.allowed_scopes.map((scope) => (
                        <Badge key={scope} variant="outline" className="text-xs">
                          {scope}
                        </Badge>
                      ))}
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
