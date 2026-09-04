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

export function useInvoices() {
  const activeTenantId = useActiveTenantId();

  return useQuery({
    queryKey: [
      "invoices",
      activeTenantId,
    ],
    queryFn: getInvoices,
    enabled: Boolean(activeTenantId),
  });
}

export function useInvoice(
  invoiceId: string,
) {
  const activeTenantId = useActiveTenantId();

  return useQuery({
    queryKey: [
      "invoice",
      activeTenantId,
      invoiceId,
    ],
    queryFn: () =>
      getInvoice(invoiceId),
    enabled:
      Boolean(activeTenantId) &&
      Boolean(invoiceId),
  });
}

export function useInvoiceLines(
  invoiceId: string,
) {
  const activeTenantId = useActiveTenantId();

  return useQuery({
    queryKey: [
      "invoice-lines",
      activeTenantId,
      invoiceId,
    ],
    queryFn: () =>
      getInvoiceLines(invoiceId),
    enabled:
      Boolean(activeTenantId) &&
      Boolean(invoiceId),
  });
}

export function useCreateInvoice() {
  const queryClient = useQueryClient();
  const activeTenantId = useActiveTenantId();

  return useMutation({
    mutationFn: (
      input: CreateInvoiceInput,
    ) => createInvoice(input),

    onSuccess: async () => {
      await queryClient.invalidateQueries({
        queryKey: [
          "invoices",
          activeTenantId,
        ],
      });
    },
  });
}

export function useAddInvoiceLine(
  invoiceId: string,
) {
  const queryClient = useQueryClient();
  const activeTenantId = useActiveTenantId();

  return useMutation({
    mutationFn: (
      input: AddInvoiceLineInput,
    ) =>
      addInvoiceLine(
        invoiceId,
        input,
      ),

    onSuccess: async (
      newInvoiceLine,
    ) => {
      queryClient.setQueryData<InvoiceLine[]>(
        [
          "invoice-lines",
          activeTenantId,
          invoiceId,
        ],
        (currentLines) => {
          if (!currentLines) {
            return [
              newInvoiceLine,
            ];
          }

          return [
            ...currentLines,
            newInvoiceLine,
          ];
        },
      );

      await queryClient.invalidateQueries({
        queryKey: [
          "invoices",
          activeTenantId,
        ],
        refetchType: "none",
      });

      await queryClient.refetchQueries({
        queryKey: [
          "invoice",
          activeTenantId,
          invoiceId,
        ],
        exact: true,
      });
    },
  });
}

export function useRemoveInvoiceLine(
  invoiceId: string,
) {
  const queryClient = useQueryClient();
  const activeTenantId = useActiveTenantId();

  return useMutation({
    mutationFn: (
      invoiceLineId: string,
    ) =>
      removeInvoiceLine(
        invoiceId,
        invoiceLineId,
      ),

    onSuccess: async (
      _data,
      invoiceLineId,
    ) => {
      queryClient.setQueryData<InvoiceLine[]>(
        [
          "invoice-lines",
          activeTenantId,
          invoiceId,
        ],
        (currentLines) => {
          if (!currentLines) {
            return currentLines;
          }

          return currentLines.filter(
            (line) =>
              line.id !== invoiceLineId,
          );
        },
      );

      await queryClient.invalidateQueries({
        queryKey: [
          "invoices",
          activeTenantId,
        ],
        refetchType: "none",
      });

      await queryClient.refetchQueries({
        queryKey: [
          "invoice",
          activeTenantId,
          invoiceId,
        ],
        exact: true,
      });
    },
  });
}

export function useIssueInvoice(
  invoiceId: string,
) {
  const queryClient = useQueryClient();
  const activeTenantId = useActiveTenantId();

  return useMutation({
    mutationFn: () =>
      issueInvoice(invoiceId),

    onSuccess: async (invoice) => {
      queryClient.setQueryData(
        [
          "invoice",
          activeTenantId,
          invoiceId,
        ],
        invoice,
      );

      await queryClient.invalidateQueries({
        queryKey: [
          "invoices",
          activeTenantId,
        ],
        refetchType: "none",
      });
    },
  });
}

export function useVoidInvoice(
  invoiceId: string,
) {
  const queryClient = useQueryClient();
  const activeTenantId = useActiveTenantId();

  return useMutation({
    mutationFn: () =>
      voidInvoice(invoiceId),

    onSuccess: async (invoice) => {
      queryClient.setQueryData(
        [
          "invoice",
          activeTenantId,
          invoiceId,
        ],
        invoice,
      );

      await queryClient.invalidateQueries({
        queryKey: [
          "invoices",
          activeTenantId,
        ],
        refetchType: "none",
      });
    },
  });
}