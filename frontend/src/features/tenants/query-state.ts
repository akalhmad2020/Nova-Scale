type ActiveTenantQueryState = {
  data: string | null | undefined;
  error: unknown;
  isError: boolean;
  isPending: boolean;
  isSuccess: boolean;
};

export function getResolvedActiveTenantId(
  query: ActiveTenantQueryState,
): string | null {
  if (!query.isSuccess || !query.data) {
    return null;
  }

  return query.data;
}

export function canRunTenantScopedQuery(
  query: ActiveTenantQueryState,
): boolean {
  return !query.isPending;
}

export function requireActiveTenantId(
  query: ActiveTenantQueryState,
): string {
  if (query.isError) {
    if (query.error instanceof Error) {
      throw query.error;
    }

    throw new Error(
      "Unable to resolve the active workspace",
    );
  }

  if (!query.data) {
    throw new Error(
      "No active workspace is available",
    );
  }

  return query.data;
}
