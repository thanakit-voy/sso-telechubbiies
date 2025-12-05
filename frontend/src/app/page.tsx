"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
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

export default function HomePage() {
  const router = useRouter();
  const { toast } = useToast();
  const [loading, setLoading] = useState(true);
  const [initialized, setInitialized] = useState(false);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [bootstrapEmail, setBootstrapEmail] = useState("");
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    checkSystemStatus();
  }, []);

  const checkSystemStatus = async () => {
    try {
      const status = await api.getSystemStatus();
      setInitialized(status.initialized);

      if (status.initialized) {
        // Try to get current session
        try {
          const session = await api.getCurrentSession();
          if (session.user) {
            router.push("/dashboard");
            return;
          }
        } catch {
          // Not logged in
        }
      }
    } catch (error) {
      toast({
        variant: "destructive",
        title: "Error",
        description: "Failed to connect to server",
      });
    } finally {
      setLoading(false);
    }
  };

  const handleBootstrap = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);

    try {
      const result = await api.bootstrap(bootstrapEmail);
      toast({
        title: "Invitation Sent",
        description: result.message,
      });

      if (result.invitation_token) {
        // In development mode, redirect directly
        router.push(`/invite/accept?token=${result.invitation_token}`);
      }
    } catch (error) {
      toast({
        variant: "destructive",
        title: "Error",
        description: error instanceof Error ? error.message : "Failed to send invitation",
      });
    } finally {
      setSubmitting(false);
    }
  };

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);

    try {
      await api.login(email, password);
      router.push("/dashboard");
    } catch (error) {
      toast({
        variant: "destructive",
        title: "Login Failed",
        description: error instanceof Error ? error.message : "Invalid credentials",
      });
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-violet-500 to-purple-600">
        <div className="text-white text-xl">Loading...</div>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-violet-500 to-purple-600 p-4">
      <Card className="w-full max-w-md">
        <CardHeader className="text-center">
          <CardTitle className="text-2xl font-bold">
            Portal Telechubbiies
          </CardTitle>
          <CardDescription>
            {initialized
              ? "Sign in to your account"
              : "Initialize your SSO portal"}
          </CardDescription>
        </CardHeader>
        <CardContent>
          {initialized ? (
            <form onSubmit={handleLogin} className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="email">Email</Label>
                <Input
                  id="email"
                  type="email"
                  placeholder="you@example.com"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="password">Password</Label>
                <Input
                  id="password"
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                />
              </div>
              <Button type="submit" className="w-full" disabled={submitting}>
                {submitting ? "Signing in..." : "Sign In"}
              </Button>
            </form>
          ) : (
            <form onSubmit={handleBootstrap} className="space-y-4">
              <div className="p-4 bg-muted rounded-lg mb-4">
                <p className="text-sm text-muted-foreground">
                  Welcome! This portal needs to be initialized. Enter your email
                  to create the system owner account.
                </p>
              </div>
              <div className="space-y-2">
                <Label htmlFor="bootstrap-email">System Owner Email</Label>
                <Input
                  id="bootstrap-email"
                  type="email"
                  placeholder="admin@example.com"
                  value={bootstrapEmail}
                  onChange={(e) => setBootstrapEmail(e.target.value)}
                  required
                />
              </div>
              <Button type="submit" className="w-full" disabled={submitting}>
                {submitting ? "Sending..." : "Initialize Portal"}
              </Button>
            </form>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
