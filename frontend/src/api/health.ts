export type HealthResponse = {
  status: string;
};

export async function getHealth(): Promise<HealthResponse> {
  const response = await fetch("/api/health", {
    method: "GET",
    cache: "no-store",
  });

  const data = (await response.json()) as HealthResponse;

  if (!response.ok) {
    throw new Error("Backend health check failed");
  }

  return data;
}