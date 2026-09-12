import {
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";

import {
  addInvoiceLine,
  createInvoice,
  getInvoice,
  getInvoiceLines,
  getInvoices,
  issueInvoice,
  removeInvoiceLine,
  voidInvoice,
} from "@/features/billing/api";
import type {
  AddInvoiceLineInput,
  CreateInvoiceInput,
  InvoiceLine,
} from "@/features/billing/types";
import { useActiveTenantId } from "@/features/tenants/active-hooks";
import {
  canRunTenantScopedQuery,
  getResolvedActiveTenantId,
  requireActiveTenantId,
} from "@/features/tenants/query-state";

export function useInvoices() {
  const activeTenantIdQuery = useActiveTenantId();
  const activeTenantId = getResolvedActiveTenantId(
    activeTenantIdQuery,
  );

  return useQuery({
    queryKey: ["invoices", activeTenantId],
    queryFn: () => {
      requireActiveTenantId(activeTenantIdQuery);
      return getInvoices();
    },
    enabled: canRunTenantScopedQuery(activeTenantIdQuery),
  });
}

export function useInvoice(invoiceId: string) {
  const activeTenantIdQuery = useActiveTenantId();
  const activeTenantId = getResolvedActiveTenantId(
    activeTenantIdQuery,
  );

  return useQuery({
    queryKey: ["invoice", activeTenantId, invoiceId],
    queryFn: () => {
      requireActiveTenantId(activeTenantIdQuery);
      return getInvoice(invoiceId);
    },
    enabled:
      Boolean(invoiceId) &&
      canRunTenantScopedQuery(activeTenantIdQuery),
  });
}

export function useInvoiceLines(invoiceId: string) {
  const activeTenantIdQuery = useActiveTenantId();
  const activeTenantId = getResolvedActiveTenantId(
    activeTenantIdQuery,
  );

  return useQuery({
    queryKey: [
      "invoice-lines",
      activeTenantId,
      invoiceId,
    ],
    queryFn: () => {
      requireActiveTenantId(activeTenantIdQuery);
      return getInvoiceLines(invoiceId);
    },
    enabled:
      Boolean(invoiceId) &&
      canRunTenantScopedQuery(activeTenantIdQuery),
  });
}

export function useCreateInvoice() {
  const queryClient = useQueryClient();
  const activeTenantIdQuery = useActiveTenantId();

  return useMutation({
    mutationFn: (input: CreateInvoiceInput) =>
      createInvoice(input),
    onSuccess: async () => {
      await queryClient.invalidateQueries({
        queryKey: [
          "invoices",
          activeTenantIdQuery.data,
        ],
      });
    },
  });
}

export function useAddInvoiceLine(
  invoiceId: string,
) {
  const queryClient = useQueryClient();
  const activeTenantIdQuery = useActiveTenantId();

  return useMutation({
    mutationFn: (input: AddInvoiceLineInput) =>
      addInvoiceLine(invoiceId, input),
    onSuccess: async (newInvoiceLine) => {
      const tenantId = activeTenantIdQuery.data;

      queryClient.setQueryData<InvoiceLine[]>(
        ["invoice-lines", tenantId, invoiceId],
        (currentLines) =>
          currentLines
            ? [...currentLines, newInvoiceLine]
            : [newInvoiceLine],
      );

      await queryClient.invalidateQueries({
        queryKey: ["invoices", tenantId],
        refetchType: "none",
      });

      await queryClient.refetchQueries({
        queryKey: ["invoice", tenantId, invoiceId],
        exact: true,
      });
    },
  });
}

export function useRemoveInvoiceLine(
  invoiceId: string,
) {
  const queryClient = useQueryClient();
  const activeTenantIdQuery = useActiveTenantId();

  return useMutation({
    mutationFn: (invoiceLineId: string) =>
      removeInvoiceLine(invoiceId, invoiceLineId),
    onSuccess: async (_data, invoiceLineId) => {
      const tenantId = activeTenantIdQuery.data;

      queryClient.setQueryData<InvoiceLine[]>(
        ["invoice-lines", tenantId, invoiceId],
        (currentLines) =>
          currentLines?.filter(
            (line) => line.id !== invoiceLineId,
          ),
      );

      await queryClient.invalidateQueries({
        queryKey: ["invoices", tenantId],
        refetchType: "none",
      });

      await queryClient.refetchQueries({
        queryKey: ["invoice", tenantId, invoiceId],
        exact: true,
      });
    },
  });
}

export function useIssueInvoice(
  invoiceId: string,
) {
  const queryClient = useQueryClient();
  const activeTenantIdQuery = useActiveTenantId();

  return useMutation({
    mutationFn: () => issueInvoice(invoiceId),
    onSuccess: async (invoice) => {
      const tenantId = activeTenantIdQuery.data;

      queryClient.setQueryData(
        ["invoice", tenantId, invoiceId],
        invoice,
      );

      await queryClient.invalidateQueries({
        queryKey: ["invoices", tenantId],
        refetchType: "none",
      });
    },
  });
}

export function useVoidInvoice(
  invoiceId: string,
) {
  const queryClient = useQueryClient();
  const activeTenantIdQuery = useActiveTenantId();

  return useMutation({
    mutationFn: () => voidInvoice(invoiceId),
    onSuccess: async (invoice) => {
      const tenantId = activeTenantIdQuery.data;

      queryClient.setQueryData(
        ["invoice", tenantId, invoiceId],
        invoice,
      );

      await queryClient.invalidateQueries({
        queryKey: ["invoices", tenantId],
        refetchType: "none",
      });
    },
  });
}
