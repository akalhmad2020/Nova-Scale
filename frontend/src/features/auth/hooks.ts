"use client";

import {
  useMutation,
  useQuery,
} from "@tanstack/react-query";

import {
  getCurrentUser,
  login,
  logout,
} from "@/features/auth/api";

export function useLogin() {
  return useMutation({
    mutationFn: login,
  });
}

export function useCurrentUser() {
  return useQuery({
    queryKey: ["auth", "me"],
    queryFn: getCurrentUser,
    retry: false,
  });
}

export function useLogout() {
  return useMutation({
    mutationFn: logout,
  });
}