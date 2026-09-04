export type User = {
  id: string;
  email: string;
  first_name: string;
  last_name: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
};

export type LoginCredentials = {
  email: string;
  password: string;
};

export type TokenResponse = {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
};

export type RegisterUserInput = {
  email: string;
  password: string;
  first_name: string;
  last_name: string;
};