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
import { Users, Briefcase, Key, Activity, Plus } from "lucide-react";

export default function DashboardPage() {
  const [session, setSession] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      const data = await api.getCurrentSession();
      setSession(data);
    } catch (error) {
      console.error("Failed to load session", error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return <div>Loading...</div>;
  }

  return (
    <div className="space-y-8">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold">
          Welcome, {session?.user?.first_name}!
        </h1>
        <p className="text-muted-foreground mt-1">
          Manage your teams, permissions, and OAuth applications.
        </p>
      </div>

      {/* Quick Stats */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium">Teams</CardTitle>
            <Users className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {session?.teams?.length || 0}
            </div>
            <p className="text-xs text-muted-foreground">
              Teams you belong to
            </p>
          </CardContent>
        </Card>

        {session?.is_system_owner && (
          <>
            <Card>
              <CardHeader className="flex flex-row items-center justify-between pb-2">
                <CardTitle className="text-sm font-medium">Workspaces</CardTitle>
                <Briefcase className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">-</div>
                <p className="text-xs text-muted-foreground">
                  Total workspaces
                </p>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="flex flex-row items-center justify-between pb-2">
                <CardTitle className="text-sm font-medium">Permissions</CardTitle>
                <Key className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">
                  {session?.permissions?.length || 0}
                </div>
                <p className="text-xs text-muted-foreground">
                  Your permissions
                </p>
              </CardContent>
            </Card>
          </>
        )}

        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium">Activity</CardTitle>
            <Activity className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">-</div>
            <p className="text-xs text-muted-foreground">Recent actions</p>
          </CardContent>
        </Card>
      </div>

      {/* Quick Actions */}
      <div>
        <h2 className="text-xl font-semibold mb-4">Quick Actions</h2>
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {session?.teams?.length === 0 && (
            <Card>
              <CardHeader>
                <CardTitle className="text-lg">Create Your First Team</CardTitle>
                <CardDescription>
                  Get started by creating a team to organize your users.
                </CardDescription>
              </CardHeader>
              <CardContent>
                <Link href="/dashboard/teams">
                  <Button className="gap-2">
                    <Plus className="h-4 w-4" />
                    Create Team
                  </Button>
                </Link>
              </CardContent>
            </Card>
          )}

          {session?.is_system_owner && (
            <>
              <Card>
                <CardHeader>
                  <CardTitle className="text-lg">Create Workspace</CardTitle>
                  <CardDescription>
                    Create a new workspace for your organization.
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <Link href="/dashboard/workspaces">
                    <Button variant="outline" className="gap-2">
                      <Plus className="h-4 w-4" />
                      New Workspace
                    </Button>
                  </Link>
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle className="text-lg">OAuth Application</CardTitle>
                  <CardDescription>
                    Register an application to use SSO.
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <Link href="/dashboard/applications">
                    <Button variant="outline" className="gap-2">
                      <Plus className="h-4 w-4" />
                      New Application
                    </Button>
                  </Link>
                </CardContent>
              </Card>
            </>
          )}
        </div>
      </div>

      {/* Teams List */}
      {session?.teams && session.teams.length > 0 && (
        <div>
          <h2 className="text-xl font-semibold mb-4">Your Teams</h2>
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            {session.teams.map((team: any) => (
              <Card key={team.id}>
                <CardHeader>
                  <CardTitle className="text-lg">{team.name}</CardTitle>
                  <CardDescription>
                    {team.role_name || "Member"}
                    {team.is_admin && " (Admin)"}
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <Link href={`/dashboard/teams/${team.slug}`}>
                    <Button variant="outline" size="sm">
                      View Team
                    </Button>
                  </Link>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
