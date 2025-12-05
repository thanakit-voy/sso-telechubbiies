"use client";

import { useEffect, useState, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
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
import { useToast } from "@/components/ui/use-toast";

function AcceptInvitationContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { toast } = useToast();
  const token = searchParams.get("token");

  const [loading, setLoading] = useState(true);
  const [invitation, setInvitation] = useState<{
    valid: boolean;
    email: string;
    invitation_type: string;
    team_name?: string;
    role_name?: string;
    expires_at: string;
    message?: string;
  } | null>(null);

  const [formData, setFormData] = useState({
    first_name: "",
    last_name: "",
    password: "",
    confirm_password: "",
    avatar_url: "",
  });
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (token) {
      validateInvitation();
    } else {
      setLoading(false);
    }
  }, [token]);

  const validateInvitation = async () => {
    try {
      const result = await api.validateInvitation(token!);
      setInvitation(result);
    } catch (error) {
      toast({
        variant: "destructive",
        title: "Invalid Invitation",
        description: error instanceof Error ? error.message : "Invitation not found",
      });
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (formData.password !== formData.confirm_password) {
      toast({
        variant: "destructive",
        title: "Error",
        description: "Passwords do not match",
      });
      return;
    }

    if (formData.password.length < 8) {
      toast({
        variant: "destructive",
        title: "Error",
        description: "Password must be at least 8 characters",
      });
      return;
    }

    setSubmitting(true);

    try {
      await api.acceptInvitation(token!, {
        first_name: formData.first_name,
        last_name: formData.last_name,
        password: formData.password,
        avatar_url: formData.avatar_url || undefined,
      });

      toast({
        title: "Account Created",
        description: "Your account has been created. Please sign in.",
      });

      router.push("/");
    } catch (error) {
      toast({
        variant: "destructive",
        title: "Registration Failed",
        description: error instanceof Error ? error.message : "Failed to create account",
      });
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-violet-500 to-purple-600">
        <div className="text-white text-xl">Validating invitation...</div>
      </div>
    );
  }

  if (!token) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-violet-500 to-purple-600 p-4">
        <Card className="w-full max-w-md">
          <CardHeader className="text-center">
            <CardTitle className="text-2xl font-bold text-destructive">
              Invalid Link
            </CardTitle>
            <CardDescription>
              No invitation token provided. Please use the link from your
              invitation email.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Button onClick={() => router.push("/")} className="w-full">
              Go to Login
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  if (!invitation?.valid) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-violet-500 to-purple-600 p-4">
        <Card className="w-full max-w-md">
          <CardHeader className="text-center">
            <CardTitle className="text-2xl font-bold text-destructive">
              Invalid Invitation
            </CardTitle>
            <CardDescription>
              {invitation?.message || "This invitation is no longer valid."}
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Button onClick={() => router.push("/")} className="w-full">
              Go to Login
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-violet-500 to-purple-600 p-4">
      <Card className="w-full max-w-md">
        <CardHeader className="text-center">
          <CardTitle className="text-2xl font-bold">Complete Registration</CardTitle>
          <CardDescription>
            {invitation.team_name ? (
              <>
                You&apos;ve been invited to join{" "}
                <strong>{invitation.team_name}</strong>
                {invitation.role_name && (
                  <> as <strong>{invitation.role_name}</strong></>
                )}
              </>
            ) : (
              "Create your system owner account"
            )}
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="p-3 bg-muted rounded-lg text-sm">
              <strong>Email:</strong> {invitation.email}
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="first_name">First Name</Label>
                <Input
                  id="first_name"
                  value={formData.first_name}
                  onChange={(e) =>
                    setFormData({ ...formData, first_name: e.target.value })
                  }
                  required
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="last_name">Last Name</Label>
                <Input
                  id="last_name"
                  value={formData.last_name}
                  onChange={(e) =>
                    setFormData({ ...formData, last_name: e.target.value })
                  }
                  required
                />
              </div>
            </div>

            <div className="space-y-2">
              <Label htmlFor="password">Password</Label>
              <Input
                id="password"
                type="password"
                value={formData.password}
                onChange={(e) =>
                  setFormData({ ...formData, password: e.target.value })
                }
                required
                minLength={8}
              />
              <p className="text-xs text-muted-foreground">
                Min 8 characters with uppercase, lowercase, and number
              </p>
            </div>

            <div className="space-y-2">
              <Label htmlFor="confirm_password">Confirm Password</Label>
              <Input
                id="confirm_password"
                type="password"
                value={formData.confirm_password}
                onChange={(e) =>
                  setFormData({ ...formData, confirm_password: e.target.value })
                }
                required
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="avatar_url">Avatar URL (optional)</Label>
              <Input
                id="avatar_url"
                type="url"
                placeholder="https://..."
                value={formData.avatar_url}
                onChange={(e) =>
                  setFormData({ ...formData, avatar_url: e.target.value })
                }
              />
            </div>

            <Button type="submit" className="w-full" disabled={submitting}>
              {submitting ? "Creating Account..." : "Create Account"}
            </Button>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}

export default function AcceptInvitationPage() {
  return (
    <Suspense fallback={
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-violet-500 to-purple-600">
        <div className="text-white text-xl">Loading...</div>
      </div>
    }>
      <AcceptInvitationContent />
    </Suspense>
  );
}
