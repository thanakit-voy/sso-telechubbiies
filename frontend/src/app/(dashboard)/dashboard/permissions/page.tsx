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
import { useToast } from "@/components/ui/use-toast";
import { Plus, Shield, Globe, Users } from "lucide-react";

interface Permission {
  id: string;
  name: string;
  slug: string;
  description?: string;
  is_global: boolean;
}

export default function PermissionsPage() {
  const { toast } = useToast();
  const [permissions, setPermissions] = useState<Permission[]>([]);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [creating, setCreating] = useState(false);
  const [formData, setFormData] = useState({
    name: "",
    slug: "",
    description: "",
  });

  useEffect(() => {
    loadPermissions();
  }, []);

  const loadPermissions = async () => {
    try {
      const data = await api.getPermissions();
      setPermissions(data);
    } catch (error) {
      toast({
        variant: "destructive",
        title: "Error",
        description: "Failed to load permissions",
      });
    } finally {
      setLoading(false);
    }
  };

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    setCreating(true);

    try {
      await api.createPermission(formData);
      toast({
        title: "Permission Created",
        description: "Your permission has been created successfully.",
      });
      setShowCreate(false);
      setFormData({ name: "", slug: "", description: "" });
      loadPermissions();
    } catch (error) {
      toast({
        variant: "destructive",
        title: "Error",
        description: error instanceof Error ? error.message : "Failed to create permission",
      });
    } finally {
      setCreating(false);
    }
  };

  const generateSlug = (name: string) => {
    return name
      .toLowerCase()
      .replace(/[^a-z0-9_]/g, "_")
      .replace(/_+/g, "_")
      .replace(/^_|_$/g, "");
  };

  if (loading) {
    return <div>Loading...</div>;
  }

  const globalPermissions = permissions.filter((p) => p.is_global);
  const teamPermissions = permissions.filter((p) => !p.is_global);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Permissions</h1>
          <p className="text-muted-foreground">
            Manage permissions and access controls
          </p>
        </div>
        <Button onClick={() => setShowCreate(true)} className="gap-2">
          <Plus className="h-4 w-4" />
          Create Permission
        </Button>
      </div>

      {/* Create Permission Form */}
      {showCreate && (
        <Card>
          <CardHeader>
            <CardTitle>Create New Permission</CardTitle>
            <CardDescription>
              Create a new global permission. Team-specific permissions can be created from the team page.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleCreate} className="space-y-4">
              <div className="grid gap-4 md:grid-cols-2">
                <div className="space-y-2">
                  <Label htmlFor="name">Permission Name</Label>
                  <Input
                    id="name"
                    value={formData.name}
                    onChange={(e) => {
                      setFormData({
                        ...formData,
                        name: e.target.value,
                        slug: generateSlug(e.target.value),
                      });
                    }}
                    placeholder="Read Reports"
                    required
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="slug">Slug</Label>
                  <Input
                    id="slug"
                    value={formData.slug}
                    onChange={(e) =>
                      setFormData({ ...formData, slug: e.target.value })
                    }
                    placeholder="read_reports"
                    pattern="^[a-zA-Z0-9_]+$"
                    required
                  />
                  <p className="text-xs text-muted-foreground">
                    Only letters, numbers, and underscores
                  </p>
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
                  placeholder="Permission description..."
                />
              </div>
              <div className="flex gap-2">
                <Button type="submit" disabled={creating}>
                  {creating ? "Creating..." : "Create Permission"}
                </Button>
                <Button
                  type="button"
                  variant="outline"
                  onClick={() => setShowCreate(false)}
                >
                  Cancel
                </Button>
              </div>
            </form>
          </CardContent>
        </Card>
      )}

      {/* Global Permissions */}
      <div className="space-y-4">
        <div className="flex items-center gap-2">
          <Globe className="h-5 w-5" />
          <h2 className="text-xl font-semibold">Global Permissions</h2>
        </div>
        {globalPermissions.length === 0 ? (
          <Card>
            <CardContent className="py-8 text-center">
              <Shield className="h-10 w-10 mx-auto text-muted-foreground mb-3" />
              <p className="text-muted-foreground">
                No global permissions defined yet.
              </p>
            </CardContent>
          </Card>
        ) : (
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            {globalPermissions.map((permission) => (
              <Card key={permission.id}>
                <CardHeader className="pb-2">
                  <div className="flex items-start justify-between">
                    <CardTitle className="text-base">{permission.name}</CardTitle>
                    <Badge variant="secondary">Global</Badge>
                  </div>
                  <CardDescription className="font-mono text-xs">
                    @{permission.slug}
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  {permission.description && (
                    <p className="text-sm text-muted-foreground">
                      {permission.description}
                    </p>
                  )}
                </CardContent>
              </Card>
            ))}
          </div>
        )}
      </div>

      {/* Team Permissions */}
      <div className="space-y-4">
        <div className="flex items-center gap-2">
          <Users className="h-5 w-5" />
          <h2 className="text-xl font-semibold">Team-Specific Permissions</h2>
        </div>
        {teamPermissions.length === 0 ? (
          <Card>
            <CardContent className="py-8 text-center">
              <Shield className="h-10 w-10 mx-auto text-muted-foreground mb-3" />
              <p className="text-muted-foreground">
                No team-specific permissions defined yet.
              </p>
            </CardContent>
          </Card>
        ) : (
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            {teamPermissions.map((permission) => (
              <Card key={permission.id}>
                <CardHeader className="pb-2">
                  <div className="flex items-start justify-between">
                    <CardTitle className="text-base">{permission.name}</CardTitle>
                    <Badge>Team</Badge>
                  </div>
                  <CardDescription className="font-mono text-xs">
                    @{permission.slug}
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  {permission.description && (
                    <p className="text-sm text-muted-foreground">
                      {permission.description}
                    </p>
                  )}
                </CardContent>
              </Card>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
