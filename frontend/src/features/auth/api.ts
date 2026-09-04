import type {
  LoginCredentials,
  User,
} from "@/features/auth/types";

type LoginResponse = {
  authenticated: boolean;
};

export async function login(
  credentials: LoginCredentials,
): Promise<LoginResponse> {
  const response = await fetch("/api/auth/login", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(credentials),
  });

  const data = await response.json();

  if (!response.ok) {
    throw new Error(
      data?.detail ?? "Login failed",
    );
  }

  return data as LoginResponse;
}

export async function getCurrentUser(): Promise<User> {
  const response = await fetch("/api/auth/me", {
    method: "GET",
    cache: "no-store",
  });

  const data = await response.json();

  if (!response.ok) {
    throw new Error(
      data?.detail ?? "Unable to load current user",
    );
  }

  return data as User;
}

export async function logout(): Promise<void> {
  const response = await fetch("/api/auth/logout", {
    method: "POST",
  });

  if (!response.ok) {
    throw new Error("Logout failed");
  }
}