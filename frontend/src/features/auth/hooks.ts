"use client";

import {
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";

import {
  getCurrentUser,
  login,
  logout,
  registerCompany,
} from "@/features/auth/api";

export function useLogin() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: login,
    onSuccess: async () => {
      await resetSessionQueries(queryClient);
    },
  });
}

export function useRegisterCompany() {
  return useMutation({
    mutationFn: registerCompany,
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
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: logout,
    onSuccess: async () => {
      await resetSessionQueries(queryClient);
    },
  });
}

async function resetSessionQueries(
  queryClient: ReturnType<typeof useQueryClient>,
): Promise<void> {
  await queryClient.cancelQueries();
  queryClient.removeQueries();
}
