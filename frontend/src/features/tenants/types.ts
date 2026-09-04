export type UserTenant = {
  id: string;
  name: string;
  slug: string;
  membership_id: string;
  role_id: string;
};

export type CreateTenantInput = {
  name: string;
  slug: string;
};

export type CreateTenantResponse = {
  id: string;
  membership_id: string;
  name: string;
  slug: string;
};