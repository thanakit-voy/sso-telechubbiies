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
import { Separator } from "@/components/ui/separator";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
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
import {
  ArrowLeft,
  Users,
  Settings,
  UserPlus,
  UserMinus,
  Shield,
  Mail,
  Copy,
  Check,
  Trash2,
  Save,
  Crown,
} from "lucide-react";

interface Team {
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
}

interface Role {
  id: string;
  name: string;
  slug: string;
  is_admin: boolean;
  priority: number;
}

export default function TeamDetailPage() {
  const router = useRouter();
  const params = useParams();
  const slug = params.slug as string;
  const { toast } = useToast();

  const [team, setTeam] = useState<Team | null>(null);
  const [roles, setRoles] = useState<Role[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [deleting, setDeleting] = useState(false);

  // Edit form
  const [editName, setEditName] = useState("");
  const [editDescription, setEditDescription] = useState("");
  const [hasChanges, setHasChanges] = useState(false);

  // Invite form
  const [showInvite, setShowInvite] = useState(false);
  const [inviteEmail, setInviteEmail] = useState("");
  const [inviteRoleId, setInviteRoleId] = useState<string>("");
  const [inviting, setInviting] = useState(false);
  const [inviteLink, setInviteLink] = useState("");
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    loadData();
  }, [slug]);

  useEffect(() => {
    if (team) {
      const nameChanged = editName !== team.name;
      const descChanged = editDescription !== (team.description || "");
      setHasChanges(nameChanged || descChanged);
    }
  }, [editName, editDescription, team]);

  const loadData = async () => {
    try {
      const [teamData, rolesData] = await Promise.all([
        api.getTeam(slug),
        api.getTeamRoles(slug).catch(() => []),
      ]);

      setTeam(teamData);
      setRoles(rolesData);
      setEditName(teamData.name);
      setEditDescription(teamData.description || "");
    } catch (error) {
      toast({
        variant: "destructive",
        title: "Error",
        description:
          error instanceof Error ? error.message : "Failed to load team",
      });
      router.push("/dashboard/teams");
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async () => {
    if (!team) return;

    setSaving(true);

    try {
      await api.updateTeam(slug, {
        name: editName,
        description: editDescription || undefined,
      });

      toast({
        title: "Team Updated",
        description: "Team settings have been saved.",
      });

      await loadData();
    } catch (error) {
      toast({
        variant: "destructive",
        title: "Error",
        description:
          error instanceof Error ? error.message : "Failed to update team",
      });
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async () => {
    if (!team) return;

    setDeleting(true);

    try {
      await api.deleteTeam(slug);
      toast({
        title: "Team Deleted",
        description: "The team has been deleted successfully.",
      });
      router.push("/dashboard/teams");
    } catch (error) {
      toast({
        variant: "destructive",
        title: "Error",
        description:
          error instanceof Error ? error.message : "Failed to delete team",
      });
      setDeleting(false);
    }
  };

  const handleInvite = async (e: React.FormEvent) => {
    e.preventDefault();
    setInviting(true);

    try {
      const result = await api.createTeamInvitation(slug, {
        email: inviteEmail,
        role_id: inviteRoleId || undefined,
      });

      setInviteLink(result.link);
      toast({
        title: "Invitation Created",
        description: "Share the invitation link with the user.",
      });
    } catch (error) {
      toast({
        variant: "destructive",
        title: "Error",
        description:
          error instanceof Error ? error.message : "Failed to create invitation",
      });
    } finally {
      setInviting(false);
    }
  };

  const handleCopyLink = async () => {
    await navigator.clipboard.writeText(inviteLink);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleRemoveMember = async (userId: string, userName: string) => {
    try {
      await api.removeTeamMember(slug, userId);
      toast({
        title: "Member Removed",
        description: `${userName} has been removed from the team.`,
      });
      await loadData();
    } catch (error) {
      toast({
        variant: "destructive",
        title: "Error",
        description:
          error instanceof Error ? error.message : "Failed to remove member",
      });
    }
  };

  const handleUpdateRole = async (userId: string, roleId: string | null) => {
    try {
      await api.updateMemberRole(slug, userId, roleId);
      toast({
        title: "Role Updated",
        description: "Member role has been updated.",
      });
      await loadData();
    } catch (error) {
      toast({
        variant: "destructive",
        title: "Error",
        description:
          error instanceof Error ? error.message : "Failed to update role",
      });
    }
  };

  const getInitials = (firstName: string, lastName: string) => {
    return `${firstName[0]}${lastName[0]}`.toUpperCase();
  };

  if (loading) {
    return <div>Loading...</div>;
  }

  if (!team) {
    return <div>Team not found</div>;
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Link href="/dashboard/teams">
            <Button variant="ghost" size="icon">
              <ArrowLeft className="h-5 w-5" />
            </Button>
          </Link>
          <div>
            <h1 className="text-3xl font-bold">{team.name}</h1>
            <p className="text-muted-foreground font-mono text-sm">
              @{team.slug}
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
                <AlertDialogTitle>Delete Team</AlertDialogTitle>
                <AlertDialogDescription>
                  Are you sure you want to delete the team "{team.name}"? This
                  action cannot be undone. The team must have no sub-teams, no
                  members (except owner), and no roles.
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

      {/* Team Settings */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Settings className="h-5 w-5" />
            Team Settings
          </CardTitle>
          <CardDescription>
            Configure the basic settings for this team
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid gap-4 md:grid-cols-2">
            <div className="space-y-2">
              <Label htmlFor="name">Team Name</Label>
              <Input
                id="name"
                value={editName}
                onChange={(e) => setEditName(e.target.value)}
                placeholder="Engineering"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="description">Description</Label>
              <Input
                id="description"
                value={editDescription}
                onChange={(e) => setEditDescription(e.target.value)}
                placeholder="Team description..."
              />
            </div>
          </div>
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <Crown className="h-4 w-4" />
            Owner: {team.owner.first_name} {team.owner.last_name} ({team.owner.email})
          </div>
        </CardContent>
      </Card>

      {/* Members */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="flex items-center gap-2">
                <Users className="h-5 w-5" />
                Members ({team.member_count})
              </CardTitle>
              <CardDescription>
                Manage team members and their roles
              </CardDescription>
            </div>
            <Button onClick={() => setShowInvite(true)} className="gap-2">
              <UserPlus className="h-4 w-4" />
              Invite Member
            </Button>
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          {/* Invite Form */}
          {showInvite && (
            <div className="p-4 border rounded-lg bg-muted/50 space-y-4">
              <h4 className="font-medium">Invite New Member</h4>
              <form onSubmit={handleInvite} className="space-y-4">
                <div className="grid gap-4 md:grid-cols-2">
                  <div className="space-y-2">
                    <Label htmlFor="email">Email Address</Label>
                    <Input
                      id="email"
                      type="email"
                      value={inviteEmail}
                      onChange={(e) => setInviteEmail(e.target.value)}
                      placeholder="user@example.com"
                      required
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="role">Role (optional)</Label>
                    <Select
                      value={inviteRoleId || "none"}
                      onValueChange={(value) => setInviteRoleId(value === "none" ? "" : value)}
                    >
                      <SelectTrigger>
                        <SelectValue placeholder="Select a role" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="none">No role</SelectItem>
                        {roles.map((role) => (
                          <SelectItem key={role.id} value={role.id}>
                            {role.name}
                            {role.is_admin && " (Admin)"}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                </div>

                {inviteLink && (
                  <div className="space-y-2">
                    <Label>Invitation Link</Label>
                    <div className="flex gap-2">
                      <Input value={inviteLink} readOnly className="font-mono text-sm" />
                      <Button
                        type="button"
                        variant="outline"
                        size="icon"
                        onClick={handleCopyLink}
                      >
                        {copied ? (
                          <Check className="h-4 w-4 text-green-500" />
                        ) : (
                          <Copy className="h-4 w-4" />
                        )}
                      </Button>
                    </div>
                    <p className="text-xs text-muted-foreground">
                      Share this link with the user to invite them to the team.
                    </p>
                  </div>
                )}

                <div className="flex gap-2">
                  <Button type="submit" disabled={inviting} className="gap-2">
                    <Mail className="h-4 w-4" />
                    {inviting ? "Creating..." : "Create Invitation"}
                  </Button>
                  <Button
                    type="button"
                    variant="outline"
                    onClick={() => {
                      setShowInvite(false);
                      setInviteEmail("");
                      setInviteRoleId("");
                      setInviteLink("");
                    }}
                  >
                    Cancel
                  </Button>
                </div>
              </form>
            </div>
          )}

          <Separator />

          {/* Members List */}
          <div className="space-y-3">
            {team.members.map((member) => (
              <div
                key={member.id}
                className="flex items-center justify-between p-3 border rounded-lg"
              >
                <div className="flex items-center gap-3">
                  <Avatar>
                    <AvatarImage
                      src={member.user.avatar_url}
                      alt={member.user.first_name}
                    />
                    <AvatarFallback>
                      {getInitials(member.user.first_name, member.user.last_name)}
                    </AvatarFallback>
                  </Avatar>
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="font-medium">
                        {member.user.first_name} {member.user.last_name}
                      </span>
                      {member.user.id === team.owner_id && (
                        <Badge variant="outline" className="gap-1">
                          <Crown className="h-3 w-3" />
                          Owner
                        </Badge>
                      )}
                      {member.is_admin && member.user.id !== team.owner_id && (
                        <Badge variant="secondary">Admin</Badge>
                      )}
                    </div>
                    <p className="text-sm text-muted-foreground">
                      {member.user.email}
                    </p>
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  {/* Role Selector */}
                  <Select
                    value={member.role?.id || "none"}
                    onValueChange={(value) =>
                      handleUpdateRole(member.user.id, value === "none" ? null : value)
                    }
                    disabled={member.user.id === team.owner_id}
                  >
                    <SelectTrigger className="w-[180px]">
                      <SelectValue placeholder="No role" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="none">No role</SelectItem>
                      {roles.map((role) => (
                        <SelectItem key={role.id} value={role.id}>
                          <div className="flex items-center gap-2">
                            {role.is_admin && <Shield className="h-3 w-3" />}
                            {role.name}
                          </div>
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>

                  {/* Remove Button */}
                  {member.user.id !== team.owner_id && (
                    <AlertDialog>
                      <AlertDialogTrigger asChild>
                        <Button variant="ghost" size="icon">
                          <UserMinus className="h-4 w-4 text-destructive" />
                        </Button>
                      </AlertDialogTrigger>
                      <AlertDialogContent>
                        <AlertDialogHeader>
                          <AlertDialogTitle>Remove Member</AlertDialogTitle>
                          <AlertDialogDescription>
                            Are you sure you want to remove {member.user.first_name}{" "}
                            {member.user.last_name} from the team?
                          </AlertDialogDescription>
                        </AlertDialogHeader>
                        <AlertDialogFooter>
                          <AlertDialogCancel>Cancel</AlertDialogCancel>
                          <AlertDialogAction
                            onClick={() =>
                              handleRemoveMember(
                                member.user.id,
                                `${member.user.first_name} ${member.user.last_name}`
                              )
                            }
                            className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
                          >
                            Remove
                          </AlertDialogAction>
                        </AlertDialogFooter>
                      </AlertDialogContent>
                    </AlertDialog>
                  )}
                </div>
              </div>
            ))}

            {team.members.length === 0 && (
              <div className="text-center py-8">
                <Users className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
                <h3 className="text-lg font-medium mb-2">No members yet</h3>
                <p className="text-muted-foreground">
                  Invite members to join this team.
                </p>
              </div>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Team Roles */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="flex items-center gap-2">
                <Shield className="h-5 w-5" />
                Team Roles ({roles.length})
              </CardTitle>
              <CardDescription>
                Roles define permissions for team members
              </CardDescription>
            </div>
            <Link href="/dashboard/roles">
              <Button variant="outline">Manage Roles</Button>
            </Link>
          </div>
        </CardHeader>
        <CardContent>
          {roles.length > 0 ? (
            <div className="grid gap-3 md:grid-cols-2 lg:grid-cols-3">
              {roles.map((role) => (
                <Link key={role.id} href={`/dashboard/roles/${role.slug}`}>
                  <div className="p-3 border rounded-lg hover:bg-muted/50 transition-colors cursor-pointer">
                    <div className="flex items-center justify-between">
                      <span className="font-medium">{role.name}</span>
                      {role.is_admin && (
                        <Badge variant="destructive" className="text-xs">
                          Admin
                        </Badge>
                      )}
                    </div>
                    <p className="text-xs text-muted-foreground font-mono">
                      @{role.slug}
                    </p>
                  </div>
                </Link>
              ))}
            </div>
          ) : (
            <div className="text-center py-6">
              <Shield className="h-10 w-10 mx-auto text-muted-foreground mb-3" />
              <p className="text-muted-foreground">
                No roles created for this team yet.
              </p>
              <Link href="/dashboard/roles">
                <Button variant="outline" className="mt-3">
                  Create Role
                </Button>
              </Link>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
