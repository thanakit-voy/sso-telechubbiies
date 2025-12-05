"use client";

import { useEffect, useState } from "react";
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
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { useToast } from "@/components/ui/use-toast";
import {
  Plus,
  Shield,
  Users,
  ArrowUpDown,
  Lock,
  AlertCircle,
  ChevronUp,
  ChevronDown,
} from "lucide-react";

interface Role {
  id: string;
  name: string;
  slug: string;
  description?: string;
  team_id: string;
  team_name?: string;
  team_slug?: string;
  is_admin: boolean;
  priority: number;
  member_count?: number;
}

interface Team {
  id: string;
  name: string;
  slug: string;
}

export default function RolesPage() {
  const { toast } = useToast();
  const [roles, setRoles] = useState<Role[]>([]);
  const [teams, setTeams] = useState<Team[]>([]);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [creating, setCreating] = useState(false);
  const [formData, setFormData] = useState({
    name: "",
    slug: "",
    description: "",
    team_slug: "",
  });

  // Reorder state
  const [reorderTeamSlug, setReorderTeamSlug] = useState<string | null>(null);
  const [reorderRoles, setReorderRoles] = useState<Role[]>([]);
  const [reordering, setReordering] = useState(false);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      const [rolesData, teamsData] = await Promise.all([
        api.getRoles(),
        api.getTeams(),
      ]);
      setRoles(rolesData);
      setTeams(teamsData);
    } catch (error) {
      toast({
        variant: "destructive",
        title: "Error",
        description: "Failed to load roles",
      });
    } finally {
      setLoading(false);
    }
  };

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!formData.team_slug) {
      toast({
        variant: "destructive",
        title: "Error",
        description: "Please select a team",
      });
      return;
    }

    setCreating(true);

    try {
      await api.createRole(formData.team_slug, {
        name: formData.name,
        slug: formData.slug,
        description: formData.description || undefined,
      });
      toast({
        title: "Role Created",
        description: "Your role has been created successfully.",
      });
      setShowCreate(false);
      setFormData({
        name: "",
        slug: "",
        description: "",
        team_slug: "",
      });
      loadData();
    } catch (error) {
      toast({
        variant: "destructive",
        title: "Error",
        description:
          error instanceof Error ? error.message : "Failed to create role",
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

  // Check if team has any roles
  const getTeamRoleCount = (teamSlug: string) => {
    return roles.filter((r) => r.team_slug === teamSlug).length;
  };

  // Reorder functions
  const openReorderDialog = async (teamSlug: string) => {
    try {
      const rolesWithMembers = await api.getTeamRolesWithMembers(teamSlug);
      setReorderRoles(rolesWithMembers);
      setReorderTeamSlug(teamSlug);
    } catch (error) {
      toast({
        variant: "destructive",
        title: "Error",
        description: "Failed to load roles for reordering",
      });
    }
  };

  const isRoleLocked = (role: Role) => {
    return role.is_admin || (role.member_count && role.member_count > 0);
  };

  const canMoveUp = (index: number) => {
    if (index === 0) return false;
    const currentRole = reorderRoles[index];
    const prevRole = reorderRoles[index - 1];
    // Can move up if current role is not locked AND previous role is not locked
    return !isRoleLocked(currentRole) && !isRoleLocked(prevRole);
  };

  const canMoveDown = (index: number) => {
    if (index === reorderRoles.length - 1) return false;
    const currentRole = reorderRoles[index];
    const nextRole = reorderRoles[index + 1];
    // Can move down if current role is not locked AND next role is not locked
    return !isRoleLocked(currentRole) && !isRoleLocked(nextRole);
  };

  const handleMoveUp = (index: number) => {
    if (!canMoveUp(index)) return;
    const newRoles = [...reorderRoles];
    [newRoles[index - 1], newRoles[index]] = [newRoles[index], newRoles[index - 1]];
    setReorderRoles(newRoles);
  };

  const handleMoveDown = (index: number) => {
    if (!canMoveDown(index)) return;
    const newRoles = [...reorderRoles];
    [newRoles[index], newRoles[index + 1]] = [newRoles[index + 1], newRoles[index]];
    setReorderRoles(newRoles);
  };

  const handleReorderSave = async () => {
    if (!reorderTeamSlug) return;

    setReordering(true);
    try {
      // Only send non-admin role IDs that have no members
      const roleIds = reorderRoles
        .filter((r) => !r.is_admin && (!r.member_count || r.member_count === 0))
        .map((r) => r.id);

      await api.reorderRoles(reorderTeamSlug, roleIds);
      toast({
        title: "Roles Reordered",
        description: "Role priorities have been updated.",
      });
      setReorderTeamSlug(null);
      loadData();
    } catch (error) {
      toast({
        variant: "destructive",
        title: "Error",
        description:
          error instanceof Error ? error.message : "Failed to reorder roles",
      });
    } finally {
      setReordering(false);
    }
  };

  // Group roles by team
  const rolesByTeam = roles.reduce(
    (acc, role) => {
      const teamKey = role.team_slug || "unknown";
      if (!acc[teamKey]) {
        acc[teamKey] = {
          team_name: role.team_name || "Unknown Team",
          team_slug: role.team_slug || "unknown",
          roles: [],
        };
      }
      acc[teamKey].roles.push(role);
      return acc;
    },
    {} as Record<string, { team_name: string; team_slug: string; roles: Role[] }>
  );

  if (loading) {
    return <div>Loading...</div>;
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Roles</h1>
          <p className="text-muted-foreground">
            Manage roles and permissions across teams
          </p>
        </div>
        <Button onClick={() => setShowCreate(true)} className="gap-2">
          <Plus className="h-4 w-4" />
          Create Role
        </Button>
      </div>

      {/* Create Role Form */}
      {showCreate && (
        <Card>
          <CardHeader>
            <CardTitle>Create New Role</CardTitle>
            <CardDescription>
              Create a new role for a team. Roles define permissions for team
              members.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleCreate} className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="team">Team</Label>
                <Select
                  value={formData.team_slug}
                  onValueChange={(value) =>
                    setFormData({ ...formData, team_slug: value })
                  }
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Select a team" />
                  </SelectTrigger>
                  <SelectContent>
                    {teams.map((team) => (
                      <SelectItem key={team.id} value={team.slug}>
                        {team.name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              {/* Info message for first role */}
              {formData.team_slug && getTeamRoleCount(formData.team_slug) === 0 && (
                <div className="flex items-start gap-2 p-3 bg-blue-50 border border-blue-200 rounded-lg text-sm">
                  <AlertCircle className="h-4 w-4 text-blue-500 mt-0.5 shrink-0" />
                  <div>
                    <p className="font-medium text-blue-700">
                      This will be the first role for this team
                    </p>
                    <p className="text-blue-600">
                      The first role is automatically set as the Admin role with the
                      highest priority (100). This role will have admin privileges
                      to manage team settings and members.
                    </p>
                  </div>
                </div>
              )}

              <div className="grid gap-4 md:grid-cols-2">
                <div className="space-y-2">
                  <Label htmlFor="name">Role Name</Label>
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
                    placeholder="Developer"
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
                    placeholder="developer"
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
                  placeholder="Role description..."
                />
              </div>
              <div className="flex gap-2">
                <Button type="submit" disabled={creating}>
                  {creating ? "Creating..." : "Create Role"}
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

      {/* Roles List by Team */}
      {Object.keys(rolesByTeam).length === 0 ? (
        <Card>
          <CardContent className="py-12 text-center">
            <Shield className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
            <h3 className="text-lg font-medium mb-2">No roles yet</h3>
            <p className="text-muted-foreground mb-4">
              Create your first role to define permissions for team members.
            </p>
            <Button onClick={() => setShowCreate(true)} className="gap-2">
              <Plus className="h-4 w-4" />
              Create Role
            </Button>
          </CardContent>
        </Card>
      ) : (
        Object.entries(rolesByTeam).map(([teamSlug, teamData]) => (
          <div key={teamSlug} className="space-y-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Users className="h-5 w-5" />
                <h2 className="text-xl font-semibold">{teamData.team_name}</h2>
                <Link href={`/dashboard/teams/${teamData.team_slug}`}>
                  <Badge variant="outline" className="cursor-pointer">
                    @{teamData.team_slug}
                  </Badge>
                </Link>
              </div>
              {teamData.roles.length > 1 && (
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => openReorderDialog(teamData.team_slug)}
                  className="gap-2"
                >
                  <ArrowUpDown className="h-4 w-4" />
                  Reorder Priorities
                </Button>
              )}
            </div>
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
              {teamData.roles.map((role) => (
                <Card key={role.id}>
                  <CardHeader className="pb-2">
                    <div className="flex items-start justify-between">
                      <CardTitle className="text-base">{role.name}</CardTitle>
                      <div className="flex gap-2">
                        <Badge variant="secondary">#{role.priority}</Badge>
                        {role.is_admin && (
                          <Badge variant="destructive">Admin</Badge>
                        )}
                      </div>
                    </div>
                    <CardDescription className="font-mono text-xs">
                      @{role.slug}
                    </CardDescription>
                  </CardHeader>
                  <CardContent>
                    {role.description && (
                      <p className="text-sm text-muted-foreground mb-4">
                        {role.description}
                      </p>
                    )}
                    <Link href={`/dashboard/roles/${role.slug}`}>
                      <Button variant="outline" size="sm" className="w-full">
                        Manage Permissions
                      </Button>
                    </Link>
                  </CardContent>
                </Card>
              ))}
            </div>
          </div>
        ))
      )}

      {/* Reorder Dialog */}
      <AlertDialog
        open={reorderTeamSlug !== null}
        onOpenChange={(open) => !open && setReorderTeamSlug(null)}
      >
        <AlertDialogContent className="max-w-md">
          <AlertDialogHeader>
            <AlertDialogTitle>Reorder Role Priorities</AlertDialogTitle>
            <AlertDialogDescription>
              Use the arrow buttons to reorder roles. Higher positions have higher priority.
              Roles with members or admin roles cannot be moved.
            </AlertDialogDescription>
          </AlertDialogHeader>

          <div className="space-y-2 my-4">
            {reorderRoles.map((role, index) => {
              const locked = isRoleLocked(role);
              return (
                <div
                  key={role.id}
                  className={`flex items-center gap-3 p-3 border rounded-lg ${
                    locked ? "bg-muted/50" : "bg-background"
                  }`}
                >
                  {/* Move buttons */}
                  <div className="flex flex-col gap-0.5 w-6">
                    {canMoveUp(index) ? (
                      <Button
                        variant="ghost"
                        size="icon"
                        className="h-6 w-6"
                        onClick={() => handleMoveUp(index)}
                      >
                        <ChevronUp className="h-4 w-4" />
                      </Button>
                    ) : (
                      <div className="h-6 w-6" />
                    )}
                    {canMoveDown(index) ? (
                      <Button
                        variant="ghost"
                        size="icon"
                        className="h-6 w-6"
                        onClick={() => handleMoveDown(index)}
                      >
                        <ChevronDown className="h-4 w-4" />
                      </Button>
                    ) : (
                      <div className="h-6 w-6" />
                    )}
                  </div>

                  {locked && <Lock className="h-4 w-4 text-muted-foreground" />}

                  <div className="flex-1">
                    <div className="flex items-center gap-2">
                      <span className="font-medium">{role.name}</span>
                      {role.is_admin && (
                        <Badge variant="destructive" className="text-xs">
                          Admin
                        </Badge>
                      )}
                    </div>
                  </div>
                  <Badge variant="outline">#{role.priority}</Badge>
                </div>
              );
            })}
          </div>

          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction onClick={handleReorderSave} disabled={reordering}>
              {reordering ? "Saving..." : "Save Order"}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
