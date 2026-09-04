import type {
  CreateLocationInput,
  Location,
} from "@/features/locations/types";

export async function getLocations(): Promise<
  Location[]
> {
  const response = await fetch(
    "/api/locations",
    {
      method: "GET",
      cache: "no-store",
    },
  );

  const data = await response.json();

  if (!response.ok) {
    throw new Error(
      data?.detail ??
        "Unable to load locations",
    );
  }

  return data as Location[];
}

export async function createLocation(
  input: CreateLocationInput,
): Promise<Location> {
  const response = await fetch(
    "/api/locations",
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(input),
    },
  );

  const data = await response.json();

  if (!response.ok) {
    throw new Error(
      data?.detail ??
        "Unable to create location",
    );
  }

  return data as Location;
}