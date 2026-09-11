import { redirect } from "next/navigation";

import { LoginForm } from "@/components/login-form";
import { isAuthenticated } from "@/features/auth/server";

type LoginPageProps = {
  searchParams: Promise<{
    registered?: string;
  }>;
};

export default async function LoginPage({
  searchParams,
}: LoginPageProps) {
  const authenticated = await isAuthenticated();

  if (authenticated) {
    redirect("/");
  }

  const { registered } = await searchParams;

  return (
    <LoginForm
      showRegistrationSuccess={registered === "1"}
    />
  );
}
