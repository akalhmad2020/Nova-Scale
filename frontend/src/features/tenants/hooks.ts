"use client";

import { useQuery } from "@tanstack/react-query";

import { getMyTenants } from "@/features/tenants/api";

export function useMyTenants() {
  return useQuery({
    queryKey: ["tenants", "mine"],
    queryFn: getMyTenants,
    retry: false,
  });
}