import { redirect } from "next/navigation";

import { SignupForm } from "@/components/signup-form";
import { isAuthenticated } from "@/features/auth/server";

export default async function SignupPage() {
  const authenticated = await isAuthenticated();

  if (authenticated) {
    redirect("/dashboard");
  }

  return <SignupForm />;
}
