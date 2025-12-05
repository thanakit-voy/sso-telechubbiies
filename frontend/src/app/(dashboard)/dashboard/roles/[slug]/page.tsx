"use client";

import { useEffect, useState } from "react";
import { useRouter, useParams } from "next/navigation";
import Link from "next/link";
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
import { Checkbox } from "@/components/ui/checkbox";
import { Separator } from "@/components/ui/separator";
import { useToast } from "@/components/ui/use-toast";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
import { ArrowLeft, Shield, Key, Save, Trash2 } from "lucide-react";

interface Role {
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
}

interface Permission {
  id: string;
  name: string;
  slug: string;
  description?: string;
  is_global: boolean;
}

export default function RoleDetailPage() {
  const router = useRouter();
  const params = useParams();
  const slug = params.slug as string;
  const { toast } = useToast();

  const [role, setRole] = useState<Role | null>(null);
  const [allPermissions, setAllPermissions] = useState<Permission[]>([]);
  const [selectedPermissions, setSelectedPermissions] = useState<Set<string>>(
    new Set()
  );
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [deleting, setDeleting] = useState(false);

  // Edit form
  const [editName, setEditName] = useState("");
  const [editDescription, setEditDescription] = useState("");
  const [hasChanges, setHasChanges] = useState(false);

  useEffect(() => {
    loadData();
  }, [slug]);

  useEffect(() => {
    if (role) {
      const nameChanged = editName !== role.name;
      const descChanged = editDescription !== (role.description || "");
      const currentPermIds = new Set(role.permissions.map((p) => p.id));
      const permsChanged =
        selectedPermissions.size !== currentPermIds.size ||
        Array.from(selectedPermissions).some((id) => !currentPermIds.has(id));

      setHasChanges(nameChanged || descChanged || permsChanged);
    }
  }, [editName, editDescription, selectedPermissions, role]);

  const loadData = async () => {
    try {
      const [roleData, permissionsData] = await Promise.all([
        api.getRole(slug),
        api.getPermissions(),
      ]);

      setRole(roleData);
      setAllPermissions(permissionsData);
      setEditName(roleData.name);
      setEditDescription(roleData.description || "");
      setSelectedPermissions(new Set(roleData.permissions.map((p) => p.id)));
    } catch (error) {
      toast({
        variant: "destructive",
        title: "Error",
        description:
          error instanceof Error ? error.message : "Failed to load role",
      });
      router.push("/dashboard/roles");
    } finally {
      setLoading(false);
    }
  };

  const handleTogglePermission = (permissionId: string) => {
    setSelectedPermissions((prev) => {
      const next = new Set(prev);
      if (next.has(permissionId)) {
        next.delete(permissionId);
      } else {
        next.add(permissionId);
      }
      return next;
    });
  };

  const handleSave = async () => {
    if (!role) return;

    setSaving(true);

    try {
      // Update role details if changed
      const nameChanged = editName !== role.name;
      const descChanged = editDescription !== (role.description || "");

      if (nameChanged || descChanged) {
        await api.updateRole(slug, {
          name: editName,
          description: editDescription || undefined,
        });
      }

      // Update permissions
      await api.assignRolePermissions(slug, Array.from(selectedPermissions));

      toast({
        title: "Role Updated",
        description: "Role settings and permissions have been saved.",
      });

      // Reload data
      await loadData();
    } catch (error) {
      toast({
        variant: "destructive",
        title: "Error",
        description:
          error instanceof Error ? error.message : "Failed to update role",
      });
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async () => {
    if (!role) return;

    setDeleting(true);

    try {
      await api.deleteRole(slug);
      toast({
        title: "Role Deleted",
        description: "The role has been deleted successfully.",
      });
      router.push("/dashboard/roles");
    } catch (error) {
      toast({
        variant: "destructive",
        title: "Error",
        description:
          error instanceof Error ? error.message : "Failed to delete role",
      });
      setDeleting(false);
    }
  };

  if (loading) {
    return <div>Loading...</div>;
  }

  if (!role) {
    return <div>Role not found</div>;
  }

  // Group permissions by global/specific
  const globalPermissions = allPermissions.filter((p) => p.is_global);
  const specificPermissions = allPermissions.filter((p) => !p.is_global);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Link href="/dashboard/roles">
            <Button variant="ghost" size="icon">
              <ArrowLeft className="h-5 w-5" />
            </Button>
          </Link>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-3xl font-bold">{role.name}</h1>
              {role.is_admin && <Badge variant="destructive">Admin</Badge>}
            </div>
            <p className="text-muted-foreground font-mono text-sm">
              @{role.slug}
            </p>
          </div>
        </div>
        <div className="flex gap-2">
          <Button
            onClick={handleSave}
            disabled={saving || !hasChanges}
            className="gap-2"
          >
            <Save className="h-4 w-4" />
            {saving ? "Saving..." : "Save Changes"}
          </Button>
          <AlertDialog>
            <AlertDialogTrigger asChild>
              <Button variant="destructive" disabled={deleting} className="gap-2">
                <Trash2 className="h-4 w-4" />
                Delete
              </Button>
            </AlertDialogTrigger>
            <AlertDialogContent>
              <AlertDialogHeader>
                <AlertDialogTitle>Delete Role</AlertDialogTitle>
                <AlertDialogDescription>
                  Are you sure you want to delete the role "{role.name}"? This
                  action cannot be undone. The role must not be assigned to any
                  team members.
                </AlertDialogDescription>
              </AlertDialogHeader>
              <AlertDialogFooter>
                <AlertDialogCancel>Cancel</AlertDialogCancel>
                <AlertDialogAction
                  onClick={handleDelete}
                  className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
                >
                  {deleting ? "Deleting..." : "Delete"}
                </AlertDialogAction>
              </AlertDialogFooter>
            </AlertDialogContent>
          </AlertDialog>
        </div>
      </div>

      {/* Role Settings */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Shield className="h-5 w-5" />
            Role Settings
          </CardTitle>
          <CardDescription>
            Configure the basic settings for this role
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid gap-4 md:grid-cols-2">
            <div className="space-y-2">
              <Label htmlFor="name">Role Name</Label>
              <Input
                id="name"
                value={editName}
                onChange={(e) => setEditName(e.target.value)}
                placeholder="Developer"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="description">Description</Label>
              <Input
                id="description"
                value={editDescription}
                onChange={(e) => setEditDescription(e.target.value)}
                placeholder="Role description..."
              />
            </div>
          </div>
          {role.is_admin && (
            <div className="flex items-center gap-2 p-3 bg-amber-50 border border-amber-200 rounded-lg text-sm">
              <Shield className="h-4 w-4 text-amber-600" />
              <p className="text-amber-700">
                This is the Admin role for this team. Admin status cannot be changed.
              </p>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Permissions */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Key className="h-5 w-5" />
            Permissions
          </CardTitle>
          <CardDescription>
            Select the permissions to assign to this role. Members with this
            role will have these permissions.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          {/* Global Permissions */}
          {globalPermissions.length > 0 && (
            <div className="space-y-4">
              <div>
                <h3 className="font-medium">Global Permissions</h3>
                <p className="text-sm text-muted-foreground">
                  System-wide permissions available to all teams
                </p>
              </div>
              <div className="grid gap-3 md:grid-cols-2 lg:grid-cols-3">
                {globalPermissions.map((permission) => (
                  <div
                    key={permission.id}
                    className={`flex items-start space-x-3 p-3 rounded-lg border transition-colors cursor-pointer ${
                      selectedPermissions.has(permission.id)
                        ? "border-primary bg-primary/5"
                        : "border-border hover:border-muted-foreground/50"
                    }`}
                    onClick={() => handleTogglePermission(permission.id)}
                  >
                    <Checkbox
                      id={`perm-${permission.id}`}
                      checked={selectedPermissions.has(permission.id)}
                      onCheckedChange={() =>
                        handleTogglePermission(permission.id)
                      }
                      className="mt-0.5"
                    />
                    <div className="flex-1 min-w-0">
                      <Label
                        htmlFor={`perm-${permission.id}`}
                        className="cursor-pointer font-medium"
                      >
                        {permission.name}
                      </Label>
                      <p className="text-xs text-muted-foreground font-mono">
                        {permission.slug}
                      </p>
                      {permission.description && (
                        <p className="text-xs text-muted-foreground mt-1">
                          {permission.description}
                        </p>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {globalPermissions.length > 0 && specificPermissions.length > 0 && (
            <Separator />
          )}

          {/* Team-specific Permissions */}
          {specificPermissions.length > 0 && (
            <div className="space-y-4">
              <div>
                <h3 className="font-medium">Team Permissions</h3>
                <p className="text-sm text-muted-foreground">
                  Permissions specific to teams or created by teams
                </p>
              </div>
              <div className="grid gap-3 md:grid-cols-2 lg:grid-cols-3">
                {specificPermissions.map((permission) => (
                  <div
                    key={permission.id}
                    className={`flex items-start space-x-3 p-3 rounded-lg border transition-colors cursor-pointer ${
                      selectedPermissions.has(permission.id)
                        ? "border-primary bg-primary/5"
                        : "border-border hover:border-muted-foreground/50"
                    }`}
                    onClick={() => handleTogglePermission(permission.id)}
                  >
                    <Checkbox
                      id={`perm-${permission.id}`}
                      checked={selectedPermissions.has(permission.id)}
                      onCheckedChange={() =>
                        handleTogglePermission(permission.id)
                      }
                      className="mt-0.5"
                    />
                    <div className="flex-1 min-w-0">
                      <Label
                        htmlFor={`perm-${permission.id}`}
                        className="cursor-pointer font-medium"
                      >
                        {permission.name}
                      </Label>
                      <p className="text-xs text-muted-foreground font-mono">
                        {permission.slug}
                      </p>
                      {permission.description && (
                        <p className="text-xs text-muted-foreground mt-1">
                          {permission.description}
                        </p>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {allPermissions.length === 0 && (
            <div className="text-center py-8">
              <Key className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
              <h3 className="text-lg font-medium mb-2">No permissions available</h3>
              <p className="text-muted-foreground">
                Create permissions first to assign them to this role.
              </p>
              <Link href="/dashboard/permissions">
                <Button variant="outline" className="mt-4">
                  Manage Permissions
                </Button>
              </Link>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Current Permissions Summary */}
      {role.permissions.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">
              Currently Assigned ({role.permissions.length})
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex flex-wrap gap-2">
              {role.permissions.map((permission) => (
                <Badge key={permission.id} variant="secondary">
                  {permission.name}
                </Badge>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
